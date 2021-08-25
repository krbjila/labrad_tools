LabRAD Setup
=================================================

Intro to LabRAD
----------------------------------------------------------

For more information see here:

* `LabRAD package <https://github.com/labrad>`__
* `Pylabrad wiki <ttps://github.com/labrad/pylabrad/wiki>`__
* `AMOLabRAD wiki maintained by Hartmut Haeffner, Wes Campbell, and Hidetoshi Katori groups <https://github.com/AMOLabRAD/AMOLabRAD/wiki>`__
* `Ye group Sr labrad_tools repos <https://github.com/yesrgang?tab=repositories>`__

This is a very brief introduction to how LabRAD is used in our experiment control system.

Labrad (stylized "LabRAD", but we're sometimes lazy) is an `"asynchronous client/server RPC system designed for scientific laboratories" <https://github.com/labrad>`__. **Basically, it provides a protocol for different instruments on the experiment to talk to each other (asynchronously)**. Nearly all of the code that we interact with directly while running the experiment (GUI's, etc.) is independent from Labrad. Labrad just provides the backend for sending information between independent pieces of code.

The basic objects in Labrad are **servers**. Servers expose methods that can be run by **clients** to do things. In our experiment, servers range from very low-level (e.g., a server that sends GPIB commands) to more abstract (e.g., ``conductor``, which tells the various parts of the experiment what to do on each run). Labrad simply provides a protocol for clients to interact with servers, and for servers to interact with each other.

A key feature of this protocol is that it's **asynchronous**. Usually, we're used to working with synchronous code, where lines of code execute in sequence, and each line only executes after the previous one has finished. Asynchronous code instead allows the next line to start executing even though the current line may not have finished (this is particularly helpful when working with hardware). For more information, see `here <https://twistedmatrix.com/documents/current/core/howto/defer-intro.html>`__ for an introduction to asynchronous code using Twisted (which we use extensively via functions like ``twisted.internet.defer.yield`` and ``twisted.internet.defer.Deferred``).

Setup manager and first node
----------------------------------------------------------

Windows 10
^^^^^^^^^^^^^^

This is a quick guide to setting up the Labrad manager and your first node on Windows.

Currently, the Labrad manager is setup and running on the main control computer ("bialkali"). In the unfortunate event that this computer dies, these instructions should be sufficient for getting Labrad running again, using a Windows machine as the main control computer. These instructions can also be used to setup an independent Labrad testbed for debugging new servers, etc.

0. Make sure you're using Python 2!

1. Install pylabrad and anything other python packages you need: ``pip install pylabrad``

2. Install the `Labrad manager <https://github.com/labrad/scalabrad>`__. To do this, download the latest version of the binary distribution `here <https://github.com/labrad/scalabrad/releases>`__ and extract somewhere (e.g., ``C:\Users\username\Desktop\labrad``).

3. Next, we need to configure a few environment variables. To do this, find "Edit system environment variables". Set the following environment variables:
   ::

    LABRADHOST=localhost
    LABRADPASSWORD=your_labrad_password
    LABRADNODE=name_of_your_node
    LABRAD_TLS=off

4. Run the Labrad manager (wherever you extracted the scalabrad distribution, plus ``\bin\labrad.bat``).

5. Now, we should be able to check that Labrad is at least running correctly. Run ``ipython`` and then try the following:

   .. code-block:: python

    import labrad
    cxn = labrad.connect()
    cxn.servers

   This should print a list of running servers (e.g., ``auth``, ``manager``, ``registry``). If there are no errors, then you are good to go!

6. Start your node. This is easy! Just do ``python -m labrad.node``. To check if it worked, follow the directions in (5) again. You should see a new server appear in the list, with the name of the ``LABRADNODE`` environment variable (for example, if you set ``LABRADNODE=test``, you should see a new server ``node_test``). You can now start servers on your new node.



7. Finally, we can optionally add the path to the ``labrad_tools`` folder to the Registry, so Labrad can automatically detect the available servers. This also allows us to start and stop several servers at once using ``labrad_tools/nodecontrol`` (as opposed to starting the python script for each server manually). See instructions in `Adding paths to the Registry`_.

Ubuntu
^^^^^^^^^^^^^^

This is a quick guide to setting up the Labrad manager and your first node on Ubuntu.

Currently, the Labrad manager is setup and running on the main control computer ("bialkali"). In the unfortunate event that this computer dies, these instructions should be sufficient for getting Labrad running again. These instructions can also be used to setup an independent Labrad testbed for debugging new servers, etc.

0. Make sure you're using Python 2!

1. Install pylabrad and anything other python packages you need: ``pip install pylabrad``

2. Install the `Labrad manager <https://github.com/labrad/scalabrad>`__. To do this, download the latest version of the binary distribution `here <https://github.com/labrad/scalabrad/releases>`__ and extract somewhere (e.g., ``~/labrad``). The manager needs Java to run, so install Java if needed: ``sudo apt install openjdk-8-jdk``

   Next, we need to setup a service to run the Labrad manager. We could just do this manually by running the Labrad manager. For example, if we had extracted the scalabrad distro to ``~/labrad``, we would just need to run ``~/labrad/bin/labrad`` to start the manager (and pass in some arguments). However, it's more convenient to just set up a systemd service here so it runs automatically.

3. To do this, copy ``labrad_tools/systemd/labrad-manager.service`` to ``/etc/systemd/system``. You'll probably need to edit the file before things work. Here is roughly what the file looks like:
   ::

    [Unit]
    Description=labrad manager
    After=syslog.target

    [Service]
    Type=simple
    User=username
    Group=username
    WorkingDirectory=/home/username/labrad_tools
    ExecStart=/home/username/labrad/bin/labrad --tls-required=false --password=password
    StandardOutput=syslog
    StandardError=syslog

    [Install]
    WantedBy=multi-user.target


   Above, you'll want to set **username** to your Linux username. Set **password** to your desired Labrad password. :code:`WorkingDirectory` should match the directory of your :code:`labrad_tools` repo; :code:`ExecStart` should have the path to your Labrad manager executable. You may also need to set the :code:`JAVA_HOME` environment variable. To do this, add the following line to :code:`/etc/environment/` : :code:`JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64/"` (the exact path will depend on your Java installation). Then log out and back in to reload the environment variables.

4. Check that the service is working correctly. First, run ``sudo systemctl daemon-reload`` (this must be done every time a systemd service is modified). Next, run ``sudo systemctl start labrad-manager.service`` to start the service, and ``sudo systemctl status labrad-manager.service`` to check the status. You should see a green circle indicating that the service is active. There is a log that will tell you if any errors occurred when running the manager. Finally, run ``sudo systemctl enable labrad-manager.service`` to run the manager automatically on startup.

5. Next, we need to configure a few environment variables. To do this, edit ``/etc/environment`` (needs root). We need to add the following lines:

   ::

    LABRADHOST=localhost
    LABRADPASSWORD=your_labrad_password
    LABRADNODE=name_of_your_node
    LABRAD_TLS=off

   You'll need to log out and log back in again to load the new environment variables.

6. Now, we should be able to check that Labrad is at least running correctly. Run ``ipython`` and then try the following:

   .. code-block:: python

    import labrad
    cxn = labrad.connect()
    cxn.servers

   This should print a list of running servers (e.g., ``auth``, ``manager``, ``registry``). If there are no errors, then you are good to go!

7. Start your node. This is easy! Just do :code:`python -m labrad.node`. To check if it worked, follow the directions in (6) again. You should see a new server appear in the list, with the name of ``$LABRADNODE`` (for example, if you set :code:`LABRADNODE=test`, you should see a new server :code:`node_test`). You can now start servers on your new node.

8. Finally, we can optionally add the path to the :code:`labrad_tools` folder to the Registry, so Labrad can automatically detect the available servers. This also allows us to start and stop several servers at once using :code:`labrad_tools/nodecontrol` (as opposed to starting the python script for each server manually). See instructions in `Adding paths to the Registry`_.

Setup a new node
----------------------------------------------------------

This is a quick guide to setting up a new Labrad node.

This assumes that you already have a Labrad manager running (see detailed instructions for :ref:`Windows 10` or :ref:`Ubuntu`).

1. Make sure you're running Python 2 (at least for our current version of servers).

2. Install Labrad: :code:`pip install pylabrad` 

3. Set environment variables:
   
   * LABRADHOST: This should be the IP address of the computer running the Manager.
   * LABRADNODE: The name of your new node.
   * LABRADPASSWORD: The Labrad password (which was set when starting up the Manager).
   * LABRAD_TLS=off
  
On Windows, this can be done by searching "Edit system environment variables" and using the dialog that pops up. On Ubuntu, set the environment variables in `/etc/environment` (e.g., `LABRADNODE=mynode`), then log out and in to reload the environment variables.

4. Run :code:`python -m labrad.node` .

5. You can check that the node is running properly using :code:`ipython` . Run the following lines:
   
.. code-block:: python

   import labrad
   cxn = labrad.connect()
   cxn.servers

This should print out a list of running Labrad servers, including the name of your new node.

Finally, we can optionally add the path to the :code:`labrad_tools` folder to the Registry, so Labrad can automatically detect the available servers. This also allows us to start and stop several servers at once using :code:`labrad_tools/nodecontrol` (as opposed to starting the python script for each server manually).

6. :ref:`Adding paths to the Registry`

Adding paths to the Registry
----------------------------------------------------------

The Registry server has a directory-like structure that holds dictionaries used by Labrad.

Our most common use case is adding new paths to the Registry, so available Labrad servers can be automatically detected on each node.

1. Start ``ipython`` and run the following:

.. code-block:: python

    import labrad
    cxn = labrad.connect()
    r = cxn.registry()

This should print out a list of available methods to run on the server. Note the directory-like structure (with commands like ``cd()``, ``dir()``, etc.). Running ``r.dir()`` should return a 2-tuple of arrays. The first element of the tuple is the list of available subdirectories. Each directory also has a dictionary-like structure, and the second element of the tuple displays the available dictionary keys.

2. Navigate to your node by running the following:

.. code-block:: python

    r.cd('Nodes')
    r.cd('NAME_OF_YOUR_NODE')
    r.dir()

``'NAME_OF_YOUR_NODE'`` above should be replaced with the actual name of your node. You should get the following output, ``([], ['autostart', 'directories', 'extensions'])``, indicating the available dictionary keys.

3. Set the new path by running

.. code-block:: python

    r.set('directories', ['FULL_PATH_TO_YOUR_LABRAD_TOOLS_FOLDER'])

You can do ``r.get('directories')`` to check that this worked.

4. Finally, to check that everything is working, run:

.. code-block:: python

    cxn.servers['node\_' + 'NAME_OF_YOUR_NODE'].available_servers()

You should see a list of all the available servers in your ``labrad_tools/`` folder on the new node.

.. _labrad-tips-tricks-label:

Labrad Tips & Tricks
----------------------------------------------------------
Working with Labrad Signals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The typical Labrad client-server interaction is driven by the client (by calling the server's ``settings``).

Labrad ``Signals`` provide a way to reverse this control flow, by letting the server send messages to the client. See the `Labrad signals source code <https://github.com/labrad/pylabrad/blob/master/labrad/server.py>`__ for more details.

Here is an example of how to declare a signal (from :mod:`conductor.conductor.ConductorServer`):

.. code-block:: python

    class ConductorServer(LabradServer):
        # ... snip ...
 
        # Declare the signal as a class variable
        # The constructor takes:
        #  - int: the id of the signal
        #  - str: the name of the signal, which determines the signal's name in the server's public API
        #  - str: type tag that describes the signal's payload (here a boolean)
        parameters_updated = Signal(698124, 'signal: parameters_updated', 'b')

To fire the signal, we need to call the class parameter and pass the payload:

.. code-block:: python

     # Somewhere in ConductorServer...
     # Fire the signal
     self.parameters_updated(True)

To receive the signal as a client, we need to subscribe to it:

.. code-block:: python

    # some_client.py

    # ... snip ...

    # self.cxn is a async Labrad connection
    conductor = yield self.cxn.get_server('conductor')

    # Subscribe to the signal
    # Note that the name we subscribe to is the name of the signal (str given in the Signal constructor),
    # with special characters replaced by underscores,
    # as opposed to the name of the class parameter.
    # my_id is the client ID: you can pick any positive int (?)
    yield conductor.signal__parameters_updated(my_id)

    # Here my_callback(context, value) is called when the signal is fired
    #  - context is the Labrad client context
    #  - value is the payload of the signal
    yield conductor.addListener(listener=my_callback, source=None, ID=my_id)
