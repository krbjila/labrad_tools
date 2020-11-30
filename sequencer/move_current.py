""" Moves all of the current sequences to today's date """ 
from __future__ import print_function

import glob, datetime
import os
from shutil import copyfile

dates_path = '/home/bialkali/data/'
sequences_path = dates_path + '{}/sequences/'
all_dates = glob.glob(dates_path + '*')


dates = []
for k in range(len(all_dates)):
    dates.append(all_dates[k].split('/')[-1])

""" Make today's directory if it doesn't exist """
todays_path = sequences_path.format(datetime.date.today().strftime('%Y%m%d'))
if not os.path.exists(todays_path):
    os.makedirs(todays_path)

dates.sort(reverse=True)
all_sequences = []
for k in range(1, len(dates)):
    current_path = sequences_path.format(dates[k])
    current_sequences = glob.glob(current_path+'*')
    for kk in current_sequences:
        x = kk.split('/')[-1]
        if x in all_sequences:
            pass
        else:
            copyfile(kk, todays_path + x)
            all_sequences.append(x)
            if os.path.exists(todays_path + x):
                print("{} successfully copied.".format(todays_path + x))
print("{} successfully copied.".format(len(all_sequences)))
