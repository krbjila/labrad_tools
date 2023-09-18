import influxdb_client
from json import load
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from pymongo import MongoClient

with open("C:\\Users\\krbji\\Desktop\\labrad_tools\\log\\secrets.json", 'r') as f:
    config= load(f)
    TEMPSTICK_KEY = config['TEMPSTICK_KEY']
    URI = config['MONGO_URI']
    INFLUXDB_TOKEN = config['INFLUXDB_TOKEN']
    INFLUXDB_URL = config['INFLUXDB_URL']


org = "krb"
influx_client = influxdb_client.InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=org)
bucket="log"
influx_api = influx_client.write_api(write_options=SYNCHRONOUS)

mongo_client = MongoClient(URI)
db = mongo_client.data.log

# load each document from the mongo database and write it to influxdb.
# example doc is:
"""
{"_id":"2023_09_11_261","time":{"$date":"2023-09-11T11:02:27.350Z"},"shot":261,"RbMOT":-0.004435493610799313,"KMOT":0.01007910631597042,"waterPressure_PSI":47.67891526222229,"wavemeter":{"Up Leg":{"freq":309.60315543944773,"unit":"THz"},"D1":{"freq":389.286952639064,"unit":"THz"},"K Repump":{"freq":391.01806446347155,"unit":"THz"},"Down Leg":{"freq":434.9231593643252,"unit":"THz"},"Rb Trap":{"freq":-99930.81933333333,"unit":"THz"},"Rb Repump":{"freq":384.2347710642697,"unit":"THz"},"K Trap":{"freq":1227.93,"unit":"MHz"}},"tempstick":{"x1B20 Room":{"temp":21.46,"humidity":44.27,"last_checkin":"2023-09-11 10:46:23"},"Optical Table":{"temp":20.59,"humidity":44.61,"last_checkin":"2023-09-11 11:01:18"}}}
"""

# InfluxDB schema:
# measurement: wavemeter
#   tags: unit
#   fields: Up Leg, D1, K Repump, Down Leg, Rb Trap, Rb Repump, K Trap
# measurement: temperature
#   tags: X1B20 Room, Optical Table
#   fields: temp, humidity
# measurement: labjack
#   tags: channel, unit
# measurement: shot
#   tags: none
#   fields: shot

i = 0
for doc in db.find():
    time = doc.get('time', None)
    shot = doc.get('shot', None)
    RbMOT = doc.get('RbMOT', None)
    KMOT = doc.get('KMOT', None)
    waterPressure_PSI = doc.get('waterPressure_PSI', None)
    wavemeter = doc.get('wavemeter', None)
    tempstick = doc.get('tempstick', None)

    # write shot data
    p = Point("shot").field("shot", shot).time(time, WritePrecision.S)
    influx_api.write(bucket, org, p)

    # write temperature data
    if tempstick is not None:
        for sensor in tempstick:
            temp = float(tempstick[sensor]['temp'])
            humidity = float(tempstick[sensor]['humidity'])
            p = Point("temperature").tag("sensor", sensor).field("temp", temp).field("humidity", humidity).time(time, WritePrecision.S)
            influx_api.write(bucket, org, p)

    # write labjack data
    if RbMOT is not None:
        p = Point("labjack").tag("channel", "RbMOT").tag("unit", "V").field("value", RbMOT).time(time, WritePrecision.S)
        influx_api.write(bucket, org, p)
    
    if KMOT is not None:
        p = Point("labjack").tag("channel", "KMOT").tag("unit", "V").field("value", KMOT).time(time, WritePrecision.S)
        influx_api.write(bucket, org, p)
    
    if waterPressure_PSI is not None:
        p = Point("labjack").tag("channel", "waterPressure").tag("unit", "PSI").field("value", waterPressure_PSI).time(time, WritePrecision.S)
        influx_api.write(bucket, org, p)

    # write wavemeter data
    if wavemeter is not None:
        for laser in wavemeter:
            freq = wavemeter[laser]['freq']
            unit = wavemeter[laser]['unit']
            p = Point("wavemeter").tag("laser", laser).tag("unit", unit).field("freq", freq).time(time, WritePrecision.S)
            influx_api.write(bucket, org, p)
