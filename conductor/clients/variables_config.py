variables_dict = [
    # Detunings and probe intensities
    ['*RbDet', 1.16],
    ['*RbHFBlast', -8.715],
    ['*KDet', 7.83],
    ['*RbProbeI', -7.5],
    ['*KProbeI', -3.5],
    ['*KHFBlast', 0.58],
    ['*KMOT', 4],
    ['*RbMOT', 9.8],
    ['*RbHFOP', 4.7], 
    # QUAD shims
    ['*NWhigh', 4.42],
    ['*NWlow', 4.43], # 4.44
    ['*SWhigh', 4.775],
    ['*SWlow',4.62], # 4.645
   # Plug PZTs
    ['*PLUGV', 0],
   # Plug Power
    ['*PLUGP', 1.9],
    # B fields
    ['*QUADV', -3.8], # was -3.6
    ['*QTRAP', 7.5],
    ['*QuadI2', 4.5], # was 3.8, was 4.0, was 5
    ['*QuadV2', -2.45], # was -2.5 on 9/17/2020
    ['*QuadI3', 0.],
    ['*QuadV3', -0.],
    ['*BIASI', 0.042], # was .04, 0.044
    ['*BIASV', 0.248],
    ['*LowField', 0.457], # was 0.465
    ['*LowFieldV', -.085],
    ['*HighField', 8.45],
    ['*HighFieldV', -3.9], # was -3.6 before moving stuff to back corridor
    ['*BiasSub', -2.65],
    ['*StableBias', -0.1], # was 0.45
    ['*FeshBias', -5.43],
    ['*ToeBias', -5.01],
    #Micellaneous
    ['*time', 0.1],
    ['*RFpulse', 0.001],
    ['*X', 0.005],
    ['*Tau', -3],
    ['*FillTime', 5.0], 
    # Lattice 
    ['*VOTLoad', 0],
    ['*VOTBottom', 0],
    ['*VOTFull', 0],
    ['*VOTFinal', 0],
    ['*VLattPhase', 0],
    ['*VLattPhaseFinal', 0],
    ['*VLattInitialPhase', 0],
    # Optical traps
    ['*HOTLoad', 4], # was 3.6 (9/23/20); was 3.77 (11/27/19); was 5.2 before calibration changed
    ['*HOTMid', 0.8], # was 0.9 (11/27/19); was 1.6 (7/11/19); was 1.8 before calibration changed
    ['*HOTFinal', 0.5], # was 0.9 before calibration changed
    ['*HOTBottom', 0.4],
    ['*HOTRecom', 0.42],
    ['*HOTFilter', 0.4],
    ['*MARIALoad', 5], # was 4.5 (9/23/20); was 2.34 (11/27/19); was 2.6
    ['*MARIAMid', 0.9], # was 0.7 (11/27/19);  was 1.0 (7/11/19); was 1
    ['*MARIAFinal', 0.7], # was 0.5
    ['*MARIABottom', 0.344],
    ['*MARIARecom', 0.4],
    ['*MARIAFilter', 0.4],
    ['*Latt1Load', 0],
    ['*LSLLoad', 0],
    ['*LSLFilter', 0],
    ['*LSLFinal', 0.03],
    # Electric Fields
    ['*LowerPlate', 0.0],
    ['*UpperPlate', 0.0],
    ['*LowerWestRod', 0.0],
    ['*LowerEastRod', 0.0],
    ['*UpperWestRod', 0.0],
    ['*UpperEastRod', 0.0],
    ['*LowerPlateZero', -0.458/2.0016e3],
    ['*UpperPlateZero', 1.003/2.00172e3],
    ['*LWRodZero', 2.848/2.00192e3],
    ['*LERodZero', -6.029/2.0014e3],
    ['*UWRodZero', -2.496/2.00005e3],
    ['*UERodZero', 0.15/2.0017e3],
    ['*LPGrad', 0],
    ['*UPGrad', 0],
    ['*LWGrad', 0],
    ['*LEGrad', 0],
    ['*UWGrad', 0],
    ['*UEGrad', 0],
    ['*LPEvap', 0],
    ['*UPEvap', 0],
    ['*LWEvap', 0],
    ['*LEEvap', 0],
    ['*UWEvap', 0],
    ['*UEEvap', 0],
    # Utility variables
#    ['*HRecompress', 0], # Evap recompression midpoint
#    ['*MRecompress', 0], # Evap recompression midpoint
]
