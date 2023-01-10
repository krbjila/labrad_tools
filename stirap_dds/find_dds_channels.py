import pyvisa

#USE ON POLARKRB ONLY

#USE FOR FINDING STIRAP DDS SERIAL PORTS
rm = pyvisa.ResourceManager()
print(rm.list_resources())

#IF THE ASRL NUMBERS ARE DIFFERENT THAN THE ONES USED IN config.json in 
# Desktop\labrad_tools\ad9910 on imaging computer, then the STIRAP DDS serial
# ports have changed and the config file needs to be updated. Update this file on 
# imaging computer, then run restart_server.py
