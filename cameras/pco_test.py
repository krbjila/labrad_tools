import labrad
import time
import numpy as np

path = "C:\\Users\\Ye Lab\\Desktop\\labrad_tools\\cameras\\test.npz"

cxn = labrad.connect()
server = cxn.krbg2_pco

cam = server.get_interface_list()[0]
server.select_interface(cam)

server.stop_record()
# print(server.available_images())
server.set_interframing_enabled(True)
server.set_trigger_mode('auto sequence')
server.start_record(2)

time.sleep(2)
print(server.available_images())
server.save_images(path, 2)
print(server.available_images())

data = np.load(path, allow_pickle=True)
print(data['data'])
print(data['meta'].item())