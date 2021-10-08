import sys
sys.path.append('../')

from twisted.internet.defer import inlineCallbacks, Deferred
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
            self.database = yield self.cxn.polarkrb_database
            self.conductor = yield self.cxn.conductor
            self.logging = yield self.cxn.imaging_logging
            yield self.database.connect(database="data", collection="shots")
        except Exception as e:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("Could not connect to database server: {}".format(e))


    @inlineCallbacks
    def update(self):
        try:
            parameters = loads(self.conductor.get_parameter_values())
            shot = self.logging.get_shot()
            now = datetime.now()
            shot_id = now.strftime("%Y_%m_%d_{}").format(shot)
            update = {
                "$set": {
                    "parameters": parameters,
                    "time": now
                }
            }
            self.database.update_one({'_id': shot_id}, update, upsert=True)
        except Exception as e:
            print("Could not save parameters to database: {}".format(e))

    @inlineCallbacks
    def stop(self):
        try:
            self.database.close()
        except Exception as e:
            print("Could not close database connection: {}".format(e))

