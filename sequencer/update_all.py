""" Update all sequences after config.json has been modified. """

import json
import glob

dates_path = '/home/bialkali/data/'
sequences_path = dates_path + '{}/sequences/'

all_dates = glob.glob(dates_path + '*')

dates = []
for k in range(len(all_dates)):
    dates.append(all_dates[k].split('/')[-1])

with open('./config.json', 'r') as infile:
    current_parameters = json.load(infile)

for folder in dates:
    path = sequences_path.format(folder)
    sequences = glob.glob(path + '*')
    sequences = ['/home/bialkali/data/20170818/sequences/bad_default']
    for k in sequences:
        with open(k, 'r') as infile:
            c = json.load(infile)
        for val in c:
            address = val.split('@')[-1]
            print(address)
            pass

x = current_parameters['devices']['ABCD']['channels'][5]
print(x)
