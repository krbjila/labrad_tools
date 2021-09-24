variables_dict = [
    # Detunings and probe intensities
    ['*RbDet', -8.64],
    ['*RbHFBlast', -8.55],
    ['*KDet', 0.375],
    ['*RbProbeI', -4.4],
    ['*KProbeI', -4.4],
    ['*KHFBlast', 0.385],
    ['*KMOT', 6.0], # was 5.1
    ['*RbMOT', 5.1], # was 3.5
    ['*RbHFOP', 5.2], 
    # QUAD shims
    ['*NWhigh', 4.4],
    ['*NWlow', 4.35], # 4.44
    ['*SWhigh', 4.84],
    ['*SWlow',4.66], # 4.645
    # Evaporation
    ['*MagEvapTime', 12.9],
    # Plug PZTs
    ['*PLUGV', 0],
    # Plug Power
    ['*PLUGP', 1.9],
    # B fields
    ['*QuadV0', -1.0],
    ['*QUADV', -4.0], # was -3.6
    ['*QTRAP', 7.5],
    ['*QuadI2', 4.5], # was 3.8, was 4.0, was 5
    ['*QuadV2', -2.4], # was -2.5 on 9/17/2020
    ['*QuadI3', 0.],
    ['*QuadV3', -0.],
    ['*BIASI', 0.044], # was .04, 0.044
    ['*BIASV', -0.37],
    ['*LowField', 0.457], # was 0.465
    ['*LowFieldV', -0.675],
    ['*HighField', 8.45],
    ['*HighFieldV', -4.65], # was -4.65 (5/18); was -4.725, was -3.6 before moving stuff to back corridor
    ['*BiasSub', -8.45],
    ['*StableBias', -0.1], # was 0.45
    ['*FeshBias', -5.245],
    ['*ToeBias', -5.01],
    # RF
    ['*RFpulse', 0.001],
    ['*RFpulse2', 0.001],
    ['*RFpulse20', 0.001],
    # Lattice 
    ['*VOTLoad', 0],
    ['*VOTBottom', 0],
    ['*VOTFull', 0],
    ['*VOTFinal', 0],
    ['*VOTHold', 0],
    ['*VLattPhase', 0],
    ['*VLattPhase2', 0],
    ['*VLattPhaseFinal', 0],
    ['*VLattInitialPhase', 0],
    # Optical traps
    ['*HOTLoad', 2.322], # was 3.6 (9/23/20); was 3.77 (11/27/19); was 5.2 before calibration changed
    ['*HOTMid', 0.9675], # was 0.8 (10/09/20); was 0.9 (11/27/19); was 1.6 (7/11/19); was 1.8 before calibration changed
    ['*HOTFinal', 0.5], # was 0.9 before calibration changed
    ['*HOTFinal2', 0.5],
    ['*HOTBottom', 0.4],
    ['*HOTRecom', 0.42],
    ['*HOTFilter', 0.4],
    ['*HOTQuad', 0.5],
    ['*MARIALoad', -8.37], # was 5 (10/09/20); was 4.5 (9/23/20); was 2.34 (11/27/19); was 2.6
    ['*MARIAMid', -3.4875], # was 0.9 (10/21/20); was 0.7 (11/27/19);  was 1.0 (7/11/19); was 1
    ['*MARIAFinal', -0.9765], # was 0.5
    ['*MARIAFinal2', -0.9765],
    ['*MARIABottom', 0.344],
    ['*MARIARecom', 0.4],
    ['*MARIAFilter', 0.4],
    ['*MARIAQuad', 0.7],
    ['*Latt1Load', 0],
    ['*LSLLoad', 0],
    ['*LSLFilter', 0],
    ['*LSLFinal', 0.03],
      # Micellaneous
    ['*time', 0.1],
    ['*X', 0.005],
    ['*Tau', -3],
    ['*FillTime', 5.0],
    ['*TOF', 1e-3],
    # Digital variables
    ['*?HOT', 1],
    ['*?MARIA', 1],
    ['*?VLATT', 1],
    ['*?LSL', 1],
    ['*?Blackman', 0],
    ['*?RFpulse', 0],
    ['*?stirap', 1],
    ['*?Blast', 0],
    ['*?Pulse1', 0],
    ['*?Pulse2', 0],
    ['*?Pulse3', 0],
    ['*?Sandwich', 0],
    ['*?BigFlip',0],
    ['*?Axial', 0],
    ['*?Side', 1],
    # Utility variables
    ['*poo', 0],
    ['*LowerPlateZero', 0],
    ['*UpperPlateZero', 0],
    ['*LWRodZero', 0],
    ['*LERodZero', 0],
    ['*UWRodZero', 0],
    ['*UERodZero', 0],
#    ['*HRecompress', 0], # Evap recompression midpoint
#    ['*MRecompress', 0], # Evap recompression midpoint
]
