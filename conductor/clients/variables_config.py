variables_dict = [
    # Detunings and probe intensities
    ['*RbDet', -8.64],
    ['*RbHFBlast', -8.55],
    ['*KDet', 0.375],
    ['*RbProbeI', -4.4],
    ['*KProbeI', -4.4],
    ['*KHFBlast', 0.385],
    ['*KMOT', 3.6], # was 5.1
    ['*RbMOT', 1.3], # was 3.5
    ['*RbHFOP', 5.2], 
    # QUAD shims
    ['*NWhigh', 4.27],# 03/14/2023 was 4.51 was 4.55, changed 05/14/2021
    ['*NWlow', 3.8], # 03/14/23 was 4.12 was 4.32 09/29/22, 4.14 11/28/2022
    ['*SWhigh', 4.74], # 03/14/23 was 4.73 was 4.7, changed 05/14/2021, 4.72 11/23/2022
    ['*SWlow', 4.59], # 03/14/23 was 4.55 was 4.6 09/29/22, 4.55 11/28/2022
    # Evaporation
    ['*MagEvapTime', 12.9],
    # Plug PZTs
    ['*PLUGV', 0],
    # Plug Power
    ['*PLUGP', 1.9],
    # B fields
    ['*QuadV0', -1.15],
    ['*QUADV', -3.75], # was -3.6
    ['*QTRAP', 7.5],
    ['*QuadI2', 4.5], # was 3.8, was 4.0, was 5
    ['*QuadV2', -2.4], # was -2.5 on 9/17/2020
    ['*QuadI3', 0.],
    ['*QuadV3', -0.],
    ['*QuadVcmot', -1],
    ['*BIASI', 0.0464], # was 0.0491 11/30/22
    ['*BIASV', -0.385],
    ['*LowField', 0.461], # was 0.457 (11/2/21)
    ['*LowFieldV', -0.675],
    ['*HighField', 8.45],
    ['*HighFieldV', -4.8], # was -4.64 (11/30/22) before changing DACs; was -4.725, was -3.6 before moving stuff to back corridor
    ['*BiasSub', -8.45],
    ['*StableBias', -0.1], # was 0.45
    ['*FeshBias', -5.3],
    ['*ToeBias', -5.01],
    # RF
    ['*RFpulse', 0.001],
    ['*RFpulse2', 0.001],
    ['*RFpulse20', 0.001],
    ['*RecoveryPulse', 0.001],
    ['*RFlayer', 0.001],
    ['*RFpi', 4.8],
    ['*Echo10', 0.001],
    ['*Echo1m1', 0.001],
    ['*FlipTime', 0.001],
    ['*RF1', 0.001],
    ['*RF2', 0.001],
    ['*RF3', 0.001],
    ['*RF4', 0.001],
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
    ['*LattLoad', -10], #for HLatt alignment
    ['*LattFinal', -0.4],
    ['*MARIAMid', -3.4875], # was 0.9 (10/21/20); was 0.7 (11/27/19);  was 1.0 (7/11/19); was 1
    ['*MARIAFinal', -0.9765], # was 0.5
    ['*MARIAFinal2', -0.9765],
    ['*MARIABottom', 0.344],
    ['*MARIARecom', 0.4],
    ['*MARIAFilter', 0.4],
    ['*MARIAQuad', 0.7],
    ['*MARIACDT', 0.7],
    ['*Latt1Load', 0],
    ['*LSLLoad', 0],
    ['*LSLFilter', 0],
    ['*LSLFinal', 0.03],
      # Micellaneous
    ['*time', 0.1],
    ['*time2', 0.2],
    ['*phase', 0],
    ['*X', 0.005],
    ['*Tau', -3],
    ['*FillTime', 5.0],
    ['*BlastTime', 20e-6],
    ['*end1', 1e-06],
    ['*mid1', 1e-06],
    ['*end2', 1e-06],
    ['*mid2', 1e-06],
    ['*tpi1', 1e-06],
    ['*tpi2', 1e-06],
    ['*TOF', 1e-03],
    ['*RFShelve', 1e-06],
    ['*SwapTime', 1e-06],
    ['*NoRFTime', 1e-06],
    # Digital variables
    ['*?HOT', 1],
    ['*?MARIA', 1],
    ['*?VLATT', 1],
    ['*?LSL', 1],
    ['*?Latt1', 1],
    ['*?Blackman', 0],
    ['*?RFpulse', 0],
    ['*?stirap', 1],
    ['*?layerBlast', 0],
    ['*?Blast', 0],
    ['*?Pulse1', 0],
    ['*?Pulse2', 0],
    ['*?Pulse3', 0],
    ['*?layerPulse1', 0],
    ['*?layerPulse2', 0],
    ['*?layerPulse3', 0],
    ['*?Sandwich', 0],
    ['*?BigFlip',0],
    ['*?BigARP',0],
    ['*?Side', 0],
    ['*?Axial', 0],
    ['*?Image00', 1],
    ['*?poo', 0],
    ['*?!poo', 1],
    ['*?20Pulse', 0],
    ['*?!20Pulse', 1],
    ['*?Shelve', 0],
    ['*?ExtraTip', 0],

    # Utility variables
    ['*poo', 0],
    ['*howdy', 100],
    ['*LowerPlateZero', 0],
    ['*UpperPlateZero', 0],
    ['*LWRodZero', 0],
    ['*LERodZero', 0],
    ['*UWRodZero', 0],
    ['*UERodZero', 0],
#    ['*HRecompress', 0], # Evap recompression midpoint
#    ['*MRecompress', 0], # Evap recompression midpoint
]
