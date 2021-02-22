"""
A script which starts the LabRAD servers listed in :mod:`nodecontrol.nodecontrol_config` in the order that they appear in the file.
"""

import labrad 
import numpy as np
import time
from nodecontrol_config import node_dicts


if __name__ == "__main__":
    cxn = labrad.connect()
    for node_dict in node_dicts:
        for node in node_dict.keys():
            if node in cxn.servers: 
                print('{}:'.format(node))
                cxn.servers[node].refresh_servers()
                running_servers = np.array(cxn.servers[node].running_servers())
                for server in node_dict[node]:
                    if server in running_servers: 
                        print('{} is running'.format(server))
                    else:
                        print('starting ' + server)
                        try:
                            cxn.servers[node].start(server)
                            if server == 'rf':
                                cxn = labrad.connect()
                                cxn.servers[node].restart(server)
                        except Exception as e:
                            print('error with ' + server)
                            print(e)
            else:
                print('{} is not running'.format(node))

    print('done!')
