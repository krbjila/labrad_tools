node_dicts = [
    {
        'node wavemeterlaptop' : [
            'wavemeter'
        ]
    },
    {
        'node imaging' : [
            'ad9910',
            'okfpga',
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
        ]
    },
]
