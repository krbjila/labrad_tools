# INTENDED AS A DEMONSTRATION OF M-LOOP
# DO NOT USE FOR ALIGNMENT
# USE motion\scripts\align_local_opt.py INSTEAD

#Imports for M-LOOP
import mloop.interfaces as mli
import mloop.controllers as mlc
import mloop.visualizations as mlv

#Other imports
import labrad
import numpy as np
from matplotlib import pyplot as plt
import time
from calibrated_picomotor import CalibratedPicomotor

#Declare your custom class that inherits from the Interface class
class CustomInterface(mli.Interface):
    
    #Initialization of the interface, including this method is optional
    def __init__(self):
        #You must include the super command to call the parent class, Interface, constructor 
        super(CustomInterface,self).__init__()

        cxn = labrad.connect()
        picomotor = cxn.polarkrb_picomotor
        self.labjack = cxn.polarkrb_labjack

        picomotor.select_device(picomotor.get_device_list()[0])
        
        calibration = {
            1: 1.2430034558945282,
            2: 1.2012205752414258,
            3: 1.0936954742350635,
            4: 1.1944678217819649
        }

        self.cpm = CalibratedPicomotor(picomotor, signal_source=self.get_voltage, calibration=calibration)
        for axis in [1, 2, 3, 4]:
            self.cpm.positions[axis] = 0
        #Attributes of the interface can be added here
        #If you want to precalculate any variables etc. this is the place to do it
        #In this example we will just define the location of the minimum
        # self.minimum_params = np.array([0,0,0,0])

    def get_voltage(self):
        return self.labjack.read_name('AIN0')
        
    #You must include the get_next_cost_dict method in your class
    #this method is called whenever M-LOOP wants to run an experiment
    def get_next_cost_dict(self,params_dict):
        
        #Get parameters from the provided dictionary
        params = params_dict['params']
        self.cpm.move_abs(1, int(params[0]))
        self.cpm.move_abs(2, int(params[1]))
        self.cpm.move_abs(3, int(params[2]))
        self.cpm.move_abs(4, int(params[3]))
        # time.sleep(0.2)
        # while not self.picomotor.motion_done(1):
        #     time.sleep(0.2)
        cost =  - self.get_voltage()
        # time.sleep(0.001)
        # cost = np.linalg.norm([(params)])

        #Here you can include the code to run your experiment given a particular set of parameters
        #In this example we will just evaluate a sum of sinc functions
        # cost = np.linalg.norm([(params)])
        #There is no uncertainty in our result
        # uncer = 0
        #The evaluation will always be a success
        bad = False
        #Add a small time delay to mimic a real experiment
        # time.sleep(0.01)
        
        #The cost, uncertainty and bad boolean must all be returned as a dictionary
        #You can include other variables you want to record as well if you want
        # cost_dict = {'cost':cost, 'uncer':uncer, 'bad':bad}
        cost_dict = {'cost':cost, 'bad':bad}
        return cost_dict
    
def main():
    #M-LOOP can be run with three commands
    
    #First create your interface
    interface = CustomInterface()
    #Next create the controller. Provide it with your interface and any options you want to set
    range = 2000
    controller = mlc.create_controller(interface, 
                                       max_num_runs = 50,
                                       target_cost = -3,
                                       num_params = 4, 
                                       min_boundary = [-range]*4,
                                       max_boundary = [range]*4)
    #To run M-LOOP and find the optimal parameters just use the controller method optimize
    controller.optimize()
    
    #The results of the optimization will be saved to files and can also be accessed as attributes of the controller.
    print('Best parameters found:')
    print(controller.best_params)
    interface.cpm.move_abs(1, int(controller.best_params[0]))
    interface.cpm.move_abs(2, int(controller.best_params[1]))
    interface.cpm.move_abs(3, int(controller.best_params[2]))
    interface.cpm.move_abs(4, int(controller.best_params[3]))
    print('Final voltage:')
    print(interface.get_voltage())
    #You can also run the default sets of visualizations for the controller with one command
    mlv.show_all_default_visualizations(controller)


#Ensures main is run when this code is run as a script
if __name__ == '__main__':
    main()