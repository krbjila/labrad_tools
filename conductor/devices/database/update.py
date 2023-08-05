import sys
sys.path.append('../')

from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from labrad.wrappers import connectAsync
from conductor_device.conductor_parameter import ConductorParameter

from bson.json_util import loads, dumps
from datetime import datetime

class Update(ConductorParameter):
    """
    Update(ConductorParameter)

    Conductor parameter for saving the list of conductor parameters in MongoDB each shot
    """

    priority = 1

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
            shot = yield self.logging.get_shot()
            if shot != None and shot != -1:
                now = datetime.now()
                shot_id = now.strftime("%Y_%m_%d_{}").format(shot)
                update = {
                    "$set": {
                        "parameters": loads(parameters),
                        "time": now
                    }
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

