""" Update all sequences after config.json has been modified. """
from __future__ import print_function

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

def getname(c, address):
	#Address should be a string like "B13" or "H07"
	reg = address[0]
	add = address[1:]
	if ord(reg) <= 68:
		row = ord(reg) - 65
		index = row*16 + int(add)
		return c['devices']['ABCD']['channels'][index]['name'] 
	elif ord(reg) > 68 and ord(reg) < 73:
		row = ord(reg) - 69
		index = row*16 + int(add)
		return c['devices']['EFGH']['channels'][index]['name']
	else:
		index = int(add)
		return c['devices'][reg]['channels'][index]['name']
			

for folder in dates:
    path = sequences_path.format(folder)
    sequences = glob.glob(path + '*')
    #sequences = ['/home/bialkali/data/20171030/sequences/testingmodule_donotopen']
    for k in sequences:
        with open(k, 'r') as infile:
            c = json.load(infile)
            if "sequence" in c:
                d = c["sequence"]
            else:
                d = c
#            print(c)
	FileUpdate = False
        for val in d:
            (old_name, address) = val.split('@')
	    channel_name = getname(current_parameters, address)
	
            if not channel_name == old_name:
		print("Discrepancy found in {0} at address {1}.".format(k.split('/')[-1], address))
                print("Changing {0} to {1}.".format(old_name, channel_name))
		d[channel_name + '@' +  address] = d.pop(old_name + '@' + address) #Replace entry in dictionary
		FileUpdate = True
	
        if FileUpdate:
            # Due to aliasing -- c has the changes to d
	    with open(k, 'w') as outfile:
	        json.dump(c, outfile)
	    print("{} successfully updated".format(k))
