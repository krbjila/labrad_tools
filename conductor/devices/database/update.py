import sys
sys.path.append('../')

from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from labrad.wrappers import connectAsync
from conductor_device.conductor_parameter import ConductorParameter

from bson.json_util import loads, dumps
from datetime import datetime
import pytz
import json

class Update(ConductorParameter):
    """
    Update(ConductorParameter)

    Conductor parameter for saving the list of conductor parameters in MongoDB each shot
    """

    priority = 5

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        try:
            self.database = yield self.cxn.database
            self.conductor = yield self.cxn.conductor
            self.logging = yield self.cxn.imaging_logging
            yield self.database.connect()
            yield self.database.set_database("data")
            yield self.database.set_collection("shots")
        except Exception as e:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("Could not connect to database server: {}".format(e))


    @inlineCallbacks
    def update(self):
        try:
            parameters = yield self.conductor.get_parameter_values()
            parameters_dict = loads(parameters)
            db_param = parameters_dict.pop('database', None)
            synth_param = parameters_dict.pop("synthesizer", None)
            shot = yield self.logging.get_shot()
            if shot != None and shot != -1:
                now = datetime.now(pytz.timezone('US/Mountain'))
                shot_id = now.strftime("%Y_%m_%d_{}").format(shot)
                db_entry = {
                    "parameters": parameters_dict,
                    "time": now
                }
                if db_param != None:
                    db_entry.update(db_param)
                if synth_param != None and "waveform" in synth_param:
                    synth_param["waveform"] = json.loads(synth_param["waveform"])
                    parameters_dict.update(synth_param)
                update = {
                    "$set": db_entry
                }
                yield self.database.update_one(dumps({'_id': shot_id}), dumps(update))
                print("Saved parameters to database with shot ID {}".format(shot_id))
        except Exception as e:
            print("Could not save parameters to database: {}".format(e))

    @inlineCallbacks
    def stop(self):
        try:
            self.database.close()
        except Exception as e:
            print("Could not close database connection: {}".format(e))

