import labrad

cxn = labrad.connect()
valon = cxn.randomlaptop_valon5009
devs = valon.get_devices()
valon.select_device(devs[0])

valon.set_channel(1)
valon.set_attenuation(10)
valon.set_freq(200)
valon.set_enable(True)
valon.save()

print(valon.get_freq())
