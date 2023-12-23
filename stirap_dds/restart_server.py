import labrad

##USE FOR RESTARTING STIRAP DDS IF ALREADY STARTED WITH NODE CONTROL
cxn = labrad.connect()
# if serial was started on polarkrb and NOT with node control, change the line below
# to be cxn.node_polarkrb.restart('serial')
cxn.node_polarkrb.restart("polarkrb_serial")
cxn.node_imaging.restart("imaging_serial")
cxn.node_imaging.start("ad9910")
cxn.node_polarkrb.restart("stirap")

# Hopefully the DDSs will work after this. If not then
# 1) If there are errors about not being able to find stirap devices when restarting
# 	ad9910 or stirap, then it is likely the serial ports changed.
# 	Run find_dds_channels.py on polarkrb and follow instructions to change the
# 	ad9910 config.json file on imaging
# 2) If there are other errors, try restarting the node. Hopefully this will fix it
