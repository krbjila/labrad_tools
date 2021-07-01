from sequencer import SequencerServer
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(SequencerServer('./test_config.json'))
