import labrad
from time import sleep
from json import loads, load
import datetime, pytz
from pymongo import MongoClient
import requests


cxn = labrad.connect()
labjack = cxn.polarkrb_labjack
wavemeter = cxn.wavemeterlaptop_wavemeter
logging = cxn.imaging_logging

with open('C:\\Users\\krbji\\Desktop\\labrad_tools\\log\\logging_config.json', 'r') as f:
    lasers = load(f)['wavemeter']['channels']

with open("C:\\Users\\krbji\\Desktop\\labrad_tools\\log\\secrets.json", 'r') as f:
    config= load(f)
    TEMPSTICK_KEY = config['TEMPSTICK_KEY']
    URI = config['MONGO_URI']

def get_tempstick():
    try:
        url = "https://tempstickapi.com/api/v1/sensors/all"
        headers = {
            "X-API-KEY": TEMPSTICK_KEY # replace YOUR_API_KEY with the key from the Developer tab
        }
        sensors = requests.get(url, headers=headers).json()['data']['items']
        data = {}
        for s in sensors:
            # print(s['sensor_name'], s['last_temp'], s['last_humidity'])
            data[s['sensor_name']] = {'temp': s['last_temp'], 'humidity': s['last_humidity'], 'last_checkin': s['last_checkin']}
        return data
    except Exception as e:
        return {'error': e}

client = MongoClient(URI)
db = client.data.log

last_shot = logging.get_shot()
last_shot_time = datetime.datetime.now(pytz.timezone('US/Mountain'))
while True:
    try:
        shot = logging.get_shot()
        if shot != last_shot or (shot == -1 and (datetime.datetime.now(pytz.timezone('US/Mountain')) - last_shot_time).total_seconds() > 60):
            sleep(10)
            last_shot = shot
            try:
                RbMOT = labjack.read_name('AIN0')
            except Exception as e:
                RbMOT = {'error': e}
            try:
                KMOT = labjack.read_name('AIN1')
            except Exception as e:
                KMOT = {'error': e}
            try:
                waterPressure = labjack.read_name('AIN2')*15.0 #15 PSI/V
            except Exception as e:
                waterPressure = {'error': e}
            wavelens = loads(loads(wavemeter.get_wavelengths()))
            try:
                freqs = {}
                for (i, l) in enumerate(lasers):
                    if l['i'] < 8:
                        wl = 299792.458/wavelens["wavelengths"][l['i']]
                        freqs[l['label']] = {'freq': wl, 'unit': 'THz'}
                    else:
                        wl = wavelens["freq"]
                        freqs[l['label']] = {'freq': wl, 'unit': 'MHz'}
            except Exception as e:
                freqs = {'error': e}
            tempstick = get_tempstick()

            now = datetime.datetime.now(pytz.timezone('US/Mountain'))
            update ={
                'time': now,
                'shot': shot if shot != 0 else None,
                # ID of the corresponding database shot: YYYY_MM_DD_shot
                '_id': now.strftime('%Y_%m_%d_') + str(shot) if shot > 0 else now.strftime('%Y_%m_%d_%H_%M_%S'),
                'RbMOT': RbMOT,
                'KMOT': KMOT,
                'waterPressure_PSI': waterPressure,
                'wavemeter': freqs,
                'tempstick': tempstick
            }
            db.insert_one(update)
            last_shot_time = now
            print(update)
    except Exception as e:
        print(e)
    sleep(1)
