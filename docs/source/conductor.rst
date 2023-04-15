conductor package
=================================================

conductor.conductor module
----------------------------------------------------------

.. automodule:: conductor.conductor
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: call_if_available, cam_info

conductor.devices module
----------------------------------------------------------

Conductor devices for configuring hardware when the experiment is run.

TODO: Document this more, including how to write a conductor device

.. automodule:: conductor.devices
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: call_if_available, cam_info

   conductor.devices.conductor_device module
   ----------------------------------------------------------

   Includes :mod:`conductor.devices.conductor_device`, which is the base class for all conductor parameters.

   .. automodule:: conductor.devices.conductor_device
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.conductor_device.conductor_parameter module
      ---------------------------------------------------------------
      
      .. automodule:: conductor.devices.conductor_device.conductor_parameter
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.3xAD9959_0 module
   ----------------------------------------------------------
   
   Conductor device for controlling 3x AD9959 DDS, using :mod:`dds.dds_server`. Not currently used in the experiment.

   .. automodule:: conductor.devices.3xAD9959_0
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.3xAD9959_0.downlegexp module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.3xAD9959_0.downlegexp
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

      conductor.devices.3xAD9959_0.uplegdp module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.3xAD9959_0.uplegdp
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   

   conductor.devices.ad9910 module
   ----------------------------------------------------------
   
   Conductor device for controlling AD9910 DDS, using :mod:`ad9910.ad9910_server`. We currently have two units, each controlled by a conductor parameter, :mod:`conductor.devices.ad9910.update` for controlling the K RF.

   .. automodule:: conductor.devices.ad9910
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.ad9910.helpers module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.ad9910.helpers
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

      conductor.devices.ad9910.update module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.ad9910.update
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.arp33220A module
   ----------------------------------------------------------
   
   Conductor device for controlling Keysight/Agilent 33220A AWG's sine output, using :mod:`gpib.gpib_server`. This controls the AWG on port ``GPIB0::22::INSTR`` on the ``krbjila`` computer. The AWG's output is currently connected to the lattice intensity servo and used for parametric heating.

   .. automodule:: conductor.devices.arp33220A
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.arp33220A.amplitude module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.arp33220A.amplitude
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

      conductor.devices.arp33220A.frequency module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.arp33220A.frequency
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.dg800 module
   ----------------------------------------------------------
   
   Conductor device for controlling Rigol DG800 series AWG's sine output, using :mod:`awgs.RigolDG800Server`. This controls the lowest-indexed AWG connected to the ``imaging`` computer.

   .. automodule:: conductor.devices.dg800
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.dg800.sin module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.dg800.sin
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.E8257D module
   ----------------------------------------------------------
   
   Conductor device for controlling Keysight/Agilent E8257D microwave synthesizer, using :mod:`gpib.gpib_server`. This controls the synthesizer connected to the ``krbjila`` computer, located on the cloud of the experiment table near the air filter. The synthesizer is used to generate the rubidium RF.

   .. automodule:: conductor.devices.E8257D
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.E8257D.enable module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.E8257D.enable
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.electrode module
   ----------------------------------------------------------
   
   Conductor device for setting electrode presets, using :mod:`electrode.electrode_server`.
   
   This is not yet fully implemented, and not currently used in the experiment.

   .. automodule:: conductor.devices.electrode
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.electrode.update module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.electrode.update
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.elliptec module
   ----------------------------------------------------------
   
   Conductor device for controlling a Thorlabs Elliptec stage, using :mod:`motion.elliptec_server`. This controls the stage attached to the ``imaging`` computer, which is used to control the position of the razor blade in front of the side/ axial imaging camera.

   Because setting the stage is not completely robust (sometimes the stage moves to the zero position), the conductor device is not currently used in the experiment.

   .. automodule:: conductor.devices.elliptec
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.elliptec.position module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.elliptec.position
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.highFieldRbARP module
   ----------------------------------------------------------
   
   Conductor device for Keysight/Agilent 33220A AWG, using :mod:`gpib.gpib_server`. This controls the AWG on port ``GPIB0::10::INSTR`` on the ``krbjila`` computer. The AWG is located on top of the main optics table's cloud.

   The AWG generates ramps, which are used to modulate the Agilent E8257D's frequency (controlled by :mod:`conductor.devices.E8257D`) for the rubidium ARPs.

   .. automodule:: conductor.devices.highFieldRbARP
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.highFieldRbARP.duration module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.highFieldRbARP.duration
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.kd1 module
   ----------------------------------------------------------
   
   Conductor device for Agilent MXG synthesizer, using :mod:`gpib.gpib_server`. This controls the AWG on port ``GPIB0::1::INSTR`` on the ``krbjila`` computer. The synthesizer is located on the wire shelves on top of the main optics table's cloud. The synthesizer's screen is broken, so this conductor device is the best way to control it.

   The synthesizer generates an RF tone for an EOM which makes sidebands on the K D1 light, to be used for gray molasses cooling.

      "They don't make those EOMs anymore, so try not to break it" - William G. Tobias (2021)

   .. automodule:: conductor.devices.kd1
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.kd1.amplitude module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.kd1.amplitude
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

      conductor.devices.kd1.frequency module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.kd1.frequency
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.magevaptimer module
   ----------------------------------------------------------
   
   Conductor device for automatically setting the ``*MagEvapTime`` parameter (used as a column length in the ``magEvap`` sequence) based on the duration of the magnetic evaporation, as saved in `magnetic_evaporation/evap.json <https://github.com/krbjila/labrad_tools/blob/master/magnetic_evaporation/evap.json>`_.

   .. automodule:: conductor.devices.magevaptimer
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.magevaptimer.time module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.magevaptimer.time
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.pixelfly module
   ----------------------------------------------------------
   
   Conductor device for controlling a pco pixelfly camera using :mod:`cameras.pco_server`.

   Not currently used on the experiment, but should be set up to control the pixelfly for imaging the MOT region, rather than the current MATLAB GUI.

   .. automodule:: conductor.devices.pixelfly
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.pixelfly.recordimage module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.pixelfly.recordimage
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.pulseShaperAWG module
   ----------------------------------------------------------
   
   Conductor device for controlling an Agilent 33220A AWG through the :mod:`usb.usb_server`. The AWG is connected to the ``polarkrb`` computer at address ``USB0::0x0957::0x0407::MY44005958::INSTR``.

   The AWG output is mixed with the \|0,0\> to \|1,0\> RF (controlled by :mod:`conductor.devices.ad9910.update`) to enable shaped pulses.

   .. automodule:: conductor.devices.pulseShaperAWG
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.pulseShaperAWG.blackman module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.pulseShaperAWG.blackman
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.sequencer module
   ----------------------------------------------------------
   
   Conductor device for loading a sequence, substituting parameters, and uploading the sequence to the TTL and DAC FPGAs.

   TODO: Finish documenting this

   .. automodule:: conductor.devices.sequencer
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.sequencer.sequence module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.sequencer.sequence
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   conductor.devices.time module
   ----------------------------------------------------------
   
   Conductor device for logging the time when the experiment was run.

   .. automodule:: conductor.devices.time
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.time.timestamp module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.time.timestamp
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info


   conductor.devices.stirap module
   ----------------------------------------------------------
   
   Conductor device for setting the EOM frequencies which offset the STIRAP lasers from the cavity.

   .. automodule:: conductor.devices.stirap
      :members:
      :undoc-members:
      :show-inheritance:
      :exclude-members: call_if_available, cam_info

      conductor.devices.stirap.helpers module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.stirap.helpers
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

      conductor.devices.stirap.down module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.stirap.down
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

      conductor.devices.stirap.up module
      ----------------------------------------------------------
      
      .. automodule:: conductor.devices.stirap.up
         :members:
         :undoc-members:
         :show-inheritance:
         :exclude-members: call_if_available, cam_info

   