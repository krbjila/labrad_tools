from __future__ import print_function
import labrad
from nodecontrol_config import node_dicts
#connect to LabRAD

try:
    cxn = labrad.connect()
except:
    print('Please start LabRAD Manager')

for node_dict in node_dicts:
    for node in node_dict.keys():
        if not node in cxn.servers:
            '{} is not running'.format(node)
        else:
            print('\nWorking on {} \n '.format(node))
            cxn.servers[node].refresh_servers()
            running_servers = cxn.servers[node].running_servers()
            for name, fullname in running_servers:
                print('stopping {}'.format(fullname))
                cxn.servers[node].stop(fullname)
print('DONE')
