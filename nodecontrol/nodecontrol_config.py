node_dicts = [
#    {
#        'node wavemeterlaptop' : [
#            'wavemeter'
#        ]
#    },
    {
        'node imaging' : [
            'wavemeter',
            'ad9910',
            'okfpga',
            'usb',
            'dg800',
            'logging'
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
            # start device servers next
            'sequencer',
            # start conductor last
            'conductor', 
        ],
        'node polarkrb': [
            # start hardware interfaces first
            'usb', 
            # start multimeter monitoring
            'multimeter', 
        ]
    },
]
