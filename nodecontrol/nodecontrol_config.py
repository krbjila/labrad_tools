"""
A list of LabRAD servers, by node, which are started and stopped by the :mod:`nodecontrol.nodecontrol_start` and :mod:`nodecontrol.nodecontrol_stop` scripts. They are started and stopped in the order that they appear in the file.
"""

node_dicts = [
    {
        'node polarkrb': [
                # start hardware interfaces first
                'synthesizer',
                'usb',
                'serial',
                'labjack',
                # 'pco',
                'database',
                'picomotor',
            ]
    },
    {
        'node wavemeterlaptop': [
                'wavemeter'
            ]
    },
    {
        'node imaging' : [
            # 'okfpga',
            'usb',
            'serial',
            'kinesis',
            # 'dg800',
            'elliptec',
            'ad9910', # needs serial server
            'andor',
            'logging'
        ],
        # 'node krbg2': [
        #     'okfpga',
        #     'dds'
        # ]
    },
    {
        'node polarkrb' : [
            'stirap',
            'dg4000'
        ]
    },
    {
        'node krbjila': [
            # start hardware interfaces first
            'gpib', 
            'okfpga',
            'arduino',
#            # electrode gui
            'electrode',
#            # start device servers next
            'sequencer',
            # start conductor last
            'conductor', 
        ],
        'node polarkrb': [
            # start multimeter monitoring
            # 'ag34410a',
            'alerter'
        ]
    },
]
