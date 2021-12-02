import json
from twisted.internet.defer import inlineCallbacks, returnValue
import sys

sys.path.append('../../')
from server_tools.device_server import DeviceWrapper

from time import sleep

class Arduino(DeviceWrapper):
    def __init__(self, config):
        """ defaults """
        self.program = []
        self.profiles = []
        self.echo = ""

        """ non-defaults"""
        for key, value in config.items():
            setattr(self, key, value)
        super(Arduino, self).__init__({})


    @inlineCallbacks
    def initialize(self):
        pass

    @inlineCallbacks
    def write_data(self, program, profiles):
        """
        write_data(self, program, profiles)

        Writes data to the Arduino. See ``ad9910_server.py`` for definitions of ``ProgramLine`` and ``Profile``.

        Args:
            program (list(ProgramLine)): list of ``ProgramLine``s
            profiles (list(Profile)): list of ``Profile``s
        """
        self.program = program
        self.profiles = profiles

        program_string = compile_program_strings(program)
        profile_string = compile_profile_strings(profiles)

        yield self.connection.flush_input()
        yield self.connection.flush_output()

        yield self.connection.write(program_string)
        yield self.connection.write(profile_string)
        yield self.connection.write("Done\n")
        yield self.connection.flush_output()

        self.echo = yield self.read_echo(self.program)

    
    @inlineCallbacks
    def force_trigger(self):
        """
        force_trigger(self)

        Issues trigger to device instead of external trigger
        """
        yield self.connection.force_trigger()
  
        

    


    
