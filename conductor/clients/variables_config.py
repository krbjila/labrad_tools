variables_dict = [
    # Detunings and probe intensities
    ['*RbDet', 1.16],
    ['*RbHFBlast', -8.715],
    ['*KDet', 7.83],
    ['*RbProbeI', -8.1],
    ['*KProbeI', -4.1],
    ['*KHFBlast', 0.58],
    # MOT shims
    ['*MOTUD', 1.9],
    ['*MOTSE', -1.0],
    ['*MOTSW', 1.4],
   # Plug PZTs
    ['*PLUGV', 0],
   # Plug Power
    ['*PLUGP', 1.9],
    # B fields
    ['*QUADV', -3.6],
    ['*QTRAP', 7.5],
    ['*QuadI2', 4.5], # was 3.8, was 4.0, was 5
    ['*QuadV2', -2.2], # was -2.2, was -1.9, was -2.4
    ['*QuadI3', 0.],
    ['*QuadV3', -0.],
    ['*BIASI', 0.048], # was 0.044
    ['*LowField', 0.457], # was 0.465
    ['*HighField', 8.45],
    ['*HighFieldV', -4.1], # was -3.6 before moving stuff to back corridor
    ['*BiasSub', -2.65],
    #Micellaneous
    ['*Tau', -3],
    ['*VOTLoad', 1.0],
    ['*VOTBottom', 1.0],
    ['*VOTFull',0.3],
    ['*VOTFinal', 1.0],
    ['*FillTime', 1.0], 
    # Optical traps
    ['*HOTLoad', 3.77], # was 5.2 before calibration changed
    ['*HOTMid', 1.8], # was 1.8 before calibration changed
    ['*HOTFinal', 1.8], # was 0.9 before calibration changed
    ['*HOTBottom', 0.54],
    ['*MARIALoad', 1.95], # was 2.6
    ['*MARIAMid', 0.8], # was 1
    ['*MARIAFinal', 0.9], # was 0.5
    ['*MARIABottom', 0.27],
    ['*StableBias', 0.05], # was 0.45
    ['*FeshBias', -5.31],
    ['*X', 0.56],
    # Electric Fields
    ['*LowerPlate', 0.0],
    ['*UpperPlate', 0.0],
    ['*LowerRods', 0.0],
    ['*UpperRods', 0.0]
]
