#TODO: Finish and test this!

import serial
import io

ser1 = serial.Serial('/dev/ttyUSB1', baudrate=9600, timeout=3)
sio1 = io.TextIOWrapper(io.BufferedRWPair(ser1, ser1), newline='\r')
cmd = unicode('~ 05 0B ')
checksum = -ord(unicode('~'))
for c in cmd:
    checksum += ord(c)
print(cmd)
cmd = cmd + unicode(hex(checksum % 256)[2:] + '\r')
print(cmd)
sio1.write(cmd)
sio1.flush()
print sio1.readline()