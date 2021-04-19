import serial
import datetime

ser = serial.Serial("COM3", 9600, timeout=1)

ser.setRTS(False)
ser.setDTR(True)
ser.write("D0\r".encode())
#ser.write("\r".encode())
print(datetime.datetime.now())
print(ser.readline())

ser.close()
