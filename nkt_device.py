import NKTP_DLL as nktp

"""
NKT Photonics Fianium Class
"""
class Fianium:

    status_messages = {
        0: 'Emission on',
        1: 'Interlock relays off',
        2: 'Interlock supply voltage low (possible short circuit)',
        3: 'Interlock loop open',
        4: 'Output Control signal low',
        5: 'Supply voltage low',
        6: 'Internal temperature out of range',
        7: 'Clock battery low voltage',
        8: 'Date/time not set',
        9: '-',
        10: '-',
        11: '-',
        12: '-',
        13: 'CRC error on startup (possible module address conflict)',
        14: 'Log error code present',
        15: 'System error code present'
        }
    """
    dict : system status translation bits > string

    =========  ========================================================
    Bit Index  Status
    =========  ========================================================
    Bit 0:     Emission on
    Bit 1:     Interlock relays off
    Bit 2:     Interlock supply voltage low (possible short circuit)
    Bit 3:     Interlock loop open
    Bit 4:     Output Control signal low
    Bit 5:     Supply voltage low
    Bit 6:     Inlet temperature out of range
    Bit 7:     Clock battery low voltage
    ...
    Bit 13:     CRC error on startup (possible module address conflict)
    Bit 14:     Log error code present
    Bit 15:     System error code present
    =========  ========================================================
    """
    setup_options = {
        0: 'Internal power control mode',
        4: 'External feedback mode (Power Lock)'
            }
    def __init__(self, portname=None):
        """
        Searches for connected NKT lasers and defines instrument parameters.

        Make sure devices are not connected via another program already.
        If multiple Extreme/Fianium lasers are connected to the same computer,
        specificy the port of the desired laser upon instantiation.

        Parameters
        ----------
        portname : str, optional
            Enter if portname for laser is known/multiple lasers are connected.
            If not supplied, system searches for laser. None by default.

        Raises
        ------
        RuntimeError
            Throws error if multiple NKT lasers are found on one computer.
            Supply portname for desired laser if multiple present.
        """
        print('Searching for connected NKT Laser...')
        self._portname = None  # COM port for laser. Auto found if not given.
        self._module_address = 15  # module address = 15 for Fianium
        self._device_type = None  # Should be 0x88 for Fianium
        self._emission_state = None
        self._setup_status = None
        self._interlock_status = None
        self._pulse_picker_ratio = None
        self._watchdog_interval = None
        self._power_level = None
        self._nim_delay = None


        if portname:  # Allow user to init specific NKT Laser on portname
            self._portname = portname
            self._device_type = 136  # Could put check here

        else:  # Search for connection w/ laser
            # Open available ports
            nktp.openPorts(nktp.getAllPorts(), 1, 1)

            # Get open NKT ports
            portlist = nktp.getOpenPorts().split(',')
            nkt_device_found = False

            for portName in portlist:  # Sweep open nkt ports
                # get binary devList of connected nkt devices
                comm_result, devList = nktp.deviceGetAllTypes(portName)
                # Get byte at location 15 (device address for fianium)
                device_type = devList[self.module_address]

                # Double check device_type matches fianium laser
                if hex(device_type) == '0x88':  # 136 == 0x88 in hex
                    if nkt_device_found:  # If fianium found on other port, error
                        err_msg = ('''Multiple NKT Lasers found on computer.
                        COM port 1 = %s
                        COM port 2 = %s
                        Please initialize Fianium class with designated \
                        portname to avoid conflict'''
                                   % (self.portname, portName))

                        raise RuntimeError(err_msg)

                    else:  # If this is first laser found,
                        nkt_device_found = True
                        self._portname = portName
                        self._device_type = device_type

        # Close all ports
        closeResult = nktp.closePorts('')
        if nkt_device_found:
            print('NKT Fianium Found:')
            print('Comport: ', self.portname, 'Device type: ', "0x%0.2X"
                  % self.device_type, 'at address:', self.module_address)

        else:
            print('No Fianium Laser Found')

    module_address = property(lambda self: self._module_address)
    """`int`, read-only: Module address = 15 for Fianium."""

    device_type = property(lambda self: self._device_type)
    """`int`, read-only: Should be 96 (0x88) for Fianium.
    Assigned and checked during object init."""

    portname = property(lambda self: self._portname)
    """`str`, read-only: COM port for laser.
    Autofound during init if not given. User can supply when creating object.
    """
    @property
    def setup_status(self):
        """
        Reads value of register 0x16 and returns corresponding status message.

        See Fianium.setup_options for possible outcomes. Use Fianium.set_mode()
        to change value.

        Returns
        -------
        str
            Current setup status of laser based on manual values.
        """
        register_address = 0x31
        comm_result, setup_key = nktp.registerReadU16(self.portname,
                                                    self.module_address,
                                                    register_address, -1)
        self._setup_status = Fianium.setup_options[setup_key]
        return self._setup_status
    
    @property
    def interlock_status(self):
        """
        Print interlock status to terminal.

        Reads register 0x32 and converts bytes into strings based on manual.

        Manual:
        Reading the interlock register returns the current interlock status,
        which consists of two unsigned bytes. The first byte (LSB) tells if the
        interlock circuit is open or closed. The second byte (MSB) tells where
        the interlock circuit is open, if relevant.

        === === =======================================
        MSB LSB Description
        === === =======================================
        -   0   Interlock off (interlock circuit open)
        0   1   Waiting for interlock reset
        0   2   Interlock is OK
        1   0   Front panel interlock / key switch off
        2   0   Door switch open
        3   0   External module interlock
        4   0   Application interlock
        5   0   Internal module interlock
        6   0   Interlock power failure
        7   0   Interlock disabled by light source
        255 -   Interlock circuit failure
        === === =======================================

        Return
        ------
        tuple(int, str)
            (LSB, Desription) returns result according to table in manual.
        """
        register_address = 0x32
        comm_result, reading = nktp.registerRead(self.portname,
                                                self.module_address,
                                                register_address, -1)

        LSB = reading[0]  # What manual calls first byte
        MSB = reading[1]  # What manual calls second byte
        # Interlock status message based on manual
        output_options = ['Interlock off (interlock circuit open)',
                          'Front panel interlock/key switch off',
                          'Door switch open',
                          'External module interlock',
                          'Application interlock',
                          'Internal module interlock',
                          'Interlock power failure',
                          'Interlock disabled by light source']
        if LSB == 0:
            reason = output_options[MSB]
            self._interlock_status = (LSB, 'Interlocked: %s' % reason)

        elif LSB == 1:
            self._interlock_status = (LSB, 'Waiting for interlock reset')

        elif LSB == 2:
            self._interlock_status = (LSB, 'Interlock is OK')
        return self._interlock_status
    
    @property
    def pulse_picker_ratio(self):
        """
        Get pulse picker ratio by reading register 0x34.

        Manual:
        For SuperK EXTREME Systems featuring the pulse picker option, the
        divide ratio for the pulse picker can be controlled with the pulse
        picker ratio register. Note: When reading the pulse picker value, an
        8-bit unsigned integer will be returned if the ratio is lower than 256,
        and a 16-bit unsigned integer otherwise.This is for historical reasons.

        Return
        ------
        ratio : int
            Pulse picker divide ratio
        """
        register_address = 0x34
        comm_result, ratio = nktp.registerReadU16(self.portname,
                                                 self.module_address,
                                                 register_address, -1)
        self._pulse_picker_ratio = ratio
        return self._pulse_picker_ratio

    @property
    def watchdog_interval(self):
        """
        Get the watchdog interval by reading register 0x36.

        Manual:
        The system can be set to make an automatic shut-off (laser emission
        only – not electrical power) in case of lost communication. The value
        in the watchdog interval register determines how many seconds with no
        communication the system will tolerate. If the value is 0, the
        feature is disabled. 8-bit unsigned integer.

        Return
        ------
        ratio : int
            Pulse picker divide ratio
        """
        register_address = 0x36
        comm_result, interval = nktp.registerReadU8(self.portname,
                                                   self.module_address,
                                                   register_address, -1)
        self._watchdog_interval = interval
        return self._watchdog_interval

    @property
    def emission_state(self):
        """
        Accesses register 0x30 to return emission state of laser.

        Updates the value of non-public attr when called.

        Return
        ------
        bool
            True = emission off; False = emission on
        """
        register_address = 0x30
        comm_result, value = nktp.registerReadU8(self.portname,
                                                self.module_address,
                                                register_address, -1)
        if value == 3:
            self._emission_state = True
        elif value == 0:
            self._emission_state = False
        else:
            self._emission_state = 'Unknown'
            print('Unknown Emissions State Detected')

        return self._emission_state
    
    @property
    def power_level(self):
        """
        Get power level setpoint with 0.1% precision.

        Read register 0x37 and converts from permille to percent.

        Return
        ------
        power_level : float
            Power level setpoint in percent w/ 0.1% precision.
        """
        register_address = 0x37
        comm_result, power = nktp.registerReadU16(self.portname,
                                                 self.module_address,
                                                 register_address, -1)
        self._power_level = power / 10
        return self._power_level

    @property
    def nim_delay(self):
        """
        Get NIM trigger delay time.

        Reads register 0x38 and converts from int value to delay in seconds.

        Manual:
        On systems with NIM trigger output, the delay of this trigger signal
        can be adjusted with the NIM delay register. The input for this
        register should be an unsigned 16-bit value from 0 to 1023. The range
        is 0 – 9.2 ns. The average step size is 9 ps.

        Return
        ------
        nim_delay : float
            Delay time given in seconds.
        """
        register_address = 0x39
        step = 9e-12  # Step size for delay is 9 ps
        comm_result, delay = nktp.registerReadU16(self.portname,
                                                self.module_address,
                                                register_address, -1)
        self._nim_delay = delay * step
        return self._nim_delay

    def set_power(self, power):
        """
        Set power level setpoint with 0.1% precision.

        Converts from percent to permille and write register 0x37.

        Parameters
        ----------
        power : float
            Power level setpoint in percent w/ 0.1% precision. (0 <= P <= 100)
        """
        register_address = 0x37
        setpoint = int(power * 10)
        if (power >= 0) and (power <= 100):
            nktp.registerWriteU16(self.portname, self.module_address,
                                 register_address, setpoint, -1)
        else:
            self.set_emission(False)
            self.set_power(0)
            raise ValueError("Power must be between 0 and 100%\n"
                             "Setting output to 0.")
    
    def set_emission(self, state):
        """
        Change emission state of laser to on/off

        Uses nktp_dll to write to register 0x30.

        Parameters
        ----------
        state : bool
            True turns laser on, false turns emission off
        """
        register_address = 0x30

        # checks if interlock is on/off
        if state is True:
            print("Ensure Laser Safety Goggles are on")
            nktp.registerWriteU8(self.portname, self.module_address,
                                register_address, 0x03, -1)
        elif state is False:
            print("Laser off")
            nktp.registerWriteU8(self.portname, self.module_address,
                                register_address, 0x00, -1)
    
    def set_mode(self, setup_key):
        """
        Sets the "setup" of the laser according to options in manual.

        Checks value provided is withing Fianium.setup_options.keys(),
        then writes to register 0x131. Get current status w/
        Fianium.setup_status

        Manual:
        With the Setup register, the operation mode of the SuperK Fianium
        System can be controlled. The possible values are listed below;
        however, in some systems, not all modes are available.16-bit unsigned
        integer.

        0: Internal power control mode
        4: External feedback mode (Power Lock)

        Parameters
        ----------
        setup_key : int
            Interger corresponding to a key inside Fianium.setup_options
        """
        register_address = 0x31
        if setup_key in Fianium.setup_options.keys():
            nktp.registerWriteU8(self.portname, self.module_address,
                                register_address, setup_key, -1)
            print('Mode set to: ', self.setup_status)
        else:
            print('Warning: Invalid Key Provided')
            print('Mode remains as: ', self.setup_status)

    def set_pulse_picker_ratio(self, ratio):
        """
        Sets pulse picker ratio by writing register 0x34.

        Manual:
        For SuperK EXTREME Systems featuring the pulse picker option, the
        divide ratio for the pulse picker can be controlled with the pulse
        picker ratio register.

        Parameters
        ----------
        ratio : int
            Interger corresponding to a key inside Extreme.setup_options
        """
        register_address = 0x34
        if type(ratio) is int:
            nktp.registerWriteU16(self.portname, self.module_address,
                                 register_address, ratio, -1)
        else:
            raise ValueError('ratios needs to be int')

    def set_watchdog_interval(self, timeout):
        """
        Set the watchdog interval by calling registerWriteU8 on 0x36.

        Manual:
        The system can be set to make an automatic shut-off (laser emission
        only – not electrical power) in case of lost communication. The value
        in the watchdog interval register determines how many seconds with no
        communication the system will tolerate. If the value is 0, the
        feature is disabled. 8-bit unsigned integer.

        Parameters
        ----------
        timeout : int
            time (seconds) the system will toleratre for communication loss.
        """
        register_address = 0x36
        if type(timeout) is int:
            nktp.registerWriteU8(self.portname, self.module_address,
                                register_address, timeout, -1)
        else:
            raise ValueError('timeout needs to be int')

    def set_nim_delay(self, nim_delay):
        """
        Set NIM trigger delay time.

        Writes register 0x39 and converts from delay time in seconds to
        corresponding int value using setpoint = int(nim_delay/9e-12)

        Manual:
        On systems with NIM trigger output, the delay of this trigger signal
        can be adjusted with the NIM delay register. The input for this
        register should be an unsigned 16-bit value from 0 to 1023. The range
        is 0 – 9.2 ns. The average step size is 9 ps.

        Parameters
        ----------
        nim_delay : float
            Delay time given in seconds. (0 <= nim_delay <= 9.207e-9)
        """
        register_address = 0x39
        step = 9e-12  # Step size for delay is 9 ps
        int_delay = int(nim_delay/step)
        if (int_delay >= 0) and (int_delay <= 1023):
            nktp.registerWriteU16(self.portname, self.module_address,
                                 register_address, int_delay, -1)
        else:
            print('NIM Delay Value Out of Range (0 <= Delay <= 9.207e-9)')

    def print_status(self):
        """
        Read system status in bytes, translate to str, print.

        Reads system status using registerReadU16 on register 0x66.
        Translates binary into str for of equipment status through
        Extreme.status_messages.

        Returns
        -------
        str : bits
            binary results of register read in string format.
        """
        register_address = 0x66
        result, byte = nktp.registerReadU16(self.portname, self.module_address,
                                           register_address, -1)
        print(nktp.RegisterResultTypes(result))
        bits = bin(byte)
        for index, bit in enumerate(reversed(bits)):
            if bit == 'b':
                break
            elif bit == '1':
                print(Fianium.status_messages[index])

        return (bits)

    def test_read_funcs(self):
        """
        Method to output current laser setting to print.

        Reads system settings when defined. 

        Returns
        -------
        Message to print
        """
        outputs = (self.emission_state,
                   self.setup_status,
                   str(self.interlock_status),
                   self.power_level)
        output_msg = ("""
        Emission state = %s
        Setup status = %s
        Interlock Status = %s
        Power level = %s
        """ % outputs)
        print(output_msg)
"""
NKT Photonics Select Class
This class depends on the RF driver Class
Registers that have not been implemented are:
    -   Monitor 1 and 2 readout
    -   Monitor 1 and 2 gain
    -   Monitor switch
"""
class Select:
    def __init__(self, portname=None):
        """
        Searches for connected NKT Select and defines instrument parameters.

        Make sure devices are not connected via another program already.
        If multiple Selects are connected to the same computer,
        specificy the port of the desired laser upon instantiation.

        Parameters
        ----------
        portname : str, optional
            Enter if portname for laser is known/multiple Select are connected.
            If not supplied, system searches for laser. None by default.

        Raises
        ------
        RuntimeError
            Throws error if multiple NKT Select are found on one computer.
            Supply portname for desired laser if multiple present.
        """
        print('Searching for connected NKT Select...')
        self._portname = None  # COM port for laser. Auto found if not given.
        self._module_address = 18  # module address = 15 for Select
        self._device_type = None  # Should be 0x67 for Select
        self._rf_switch = None # Operation mode of SELECT

        if portname:  # Allow user to init specific NKT Laser on portname
            self._portname = portname
            self._device_type = 103  # Could put check here

        else:  # Search for connection w/ laser
            # Open available ports
            nktp.openPorts(nktp.getAllPorts(), 1, 1)

            # Get open NKT ports
            portlist = nktp.getOpenPorts().split(',')
            nkt_device_found = False

            for portName in portlist:  # Sweep open nkt ports
                # get binary devList of connected nkt devices
                comm_result, devList = nktp.deviceGetAllTypes(portName)
                # Get byte at location 15 (device address for select)
                device_type = devList[self.module_address]

                # Double check device_type matches select laser
                if hex(device_type) == '0x67':  # 103 == 0x67 in hex
                    if nkt_device_found:  # If select found on other port, error
                        err_msg = ('''Multiple NKT Lasers found on computer.
                        COM port 1 = %s
                        COM port 2 = %s
                        Please initialize Select class with designated \
                        portname to avoid conflict'''
                                   % (self.portname, portName))

                        raise RuntimeError(err_msg)

                    else:  # If this is first laser found,
                        nkt_device_found = True
                        self._portname = portName
                        self._device_type = device_type

        # Close all ports
        closeResult = nktp.closePorts('')
        if nkt_device_found:
            print('NKT Select Found:')
            print('Comport: ', self.portname, 'Device type: ', "0x%0.2X"
                  % self.device_type, 'at address:', self.module_address)

        else:
            print('No Select Module Found')

    module_address = property(lambda self: self._module_address)
    """`int`, read-only: Module address = 18 for Select."""

    device_type = property(lambda self: self._device_type)
    """`int`, read-only: Should be 103 (0x67) for Select.
    Assigned and checked during object init."""

    portname = property(lambda self: self._portname)
    """`str`, read-only: COM port for laser.
    Autofound during init if not given. User can supply when creating object.
    """

    @property
    def crystal_1_min(self):
        """
        Reads first crystal minimum usable wavelength value in nm from register 0x90 
        and returns corresponding status message.

        Returns
        -------
        wavelength: float
            Minimum usable wavelength in crystal 1 (Resolution is in 0.1 nm)
        """
        register_address = 0x90
        comm_result, reading = nktp.registerReadU32(self.portname,
                                                    self.module_address,
                                                    register_address, -1)
        return reading/1000
    
    @property
    def crystal_1_max(self):
        """
        Reads first crystal maximum usable wavelength value in nm from register 0x91 
        and returns corresponding status message.

        Returns
        -------
        wavelength: float
            Maximum usable wavelength in crystal 1 (Resolution is in 0.1 nm)
        """
        register_address = 0x91
        comm_result, reading = nktp.registerReadU32(self.portname,
                                                    self.module_address,
                                                    register_address, -1)
        return reading/1000
    
    @property
    def crystal_2_min(self):
        """
        Reads second crystal minimum usable wavelength value in nm from register 0xA0 
        and returns corresponding status message.

        Returns
        -------
        wavelength: float
            Minimum usable wavelength in crystal 2 (Resolution is in 0.1 nm)
        """
        register_address = 0xA0
        comm_result, reading = nktp.registerReadU32(self.portname,
                                                    self.module_address,
                                                    register_address, -1)
        return reading/1000
    
    @property
    def crystal_2_max(self):
        """
        Reads second crystal maximum usable wavelength value in nm from register 0xA1 
        and returns corresponding status message.

        Returns
        -------
        wavelength: float
            Maximum usable wavelength in crystal 2 (Resolution is in 0.1 nm)
        """
        register_address = 0xA1
        comm_result, reading = nktp.registerReadU32(self.portname,
                                                    self.module_address,
                                                    register_address, -1)
        return reading/1000
    
    @property
    def get_switch_settings(self):
        """
        Reads current operations of AOTF crystals. When activated, the RF switch swaps 
        the two RF connections. 
        Settings:
            0:  Normal operation
            1:  Swap crystal connections

        Returns
        -------
        (setting bit, operation mode): (int, str)
        """
        register_address = 0x34
        comm_result, reading = nktp.registerReadU8(self.portname,
                                                    self.module_address,
                                                    register_address, -1)
        if reading == 0:
            self._rf_switch = (reading, 'Normal operation')

        elif reading == 1:
            self._rf_switch = (reading, 'Swapped Crystal Connections')

        return self._rf_switch
    
    def set_switch_settings(self, switch):
        """
        Sets current operations of AOTF crystals. When activated, the RF switch swaps 
        the two RF connections. Ensure that RF driver is off when setting operation.
        Settings:
            0:  Normal operation
            1:  Swap crystal connections

        Returns
        -------
        (setting bit, operation mode): (int, str)
        """
        register_address = 0x34
        if switch is 0:
            print("Setting to normal operation")
            nktp.registerWriteU8(self.portname, self.module_address, register_address, 0x00, -1)
        elif switch is 1:
            print("Switching RF connection")
            nktp.registerWriteU8(self.portname, self.module_address, register_address, 0x01, -1)

"""
NKT Photonics RF Driver Class
This class is supposed to be dependent on the Fianium class
Registers that have not been implemented are:
    -   Setup bits
    -   FSK mode
    -   Daughter board enable/disable
    -   Modulation gain settings
"""
class RF_driver:
    def __init__(self, portname=None):
        """
        Searches for connected NKT RF drivers and defines instrument parameters.

        Make sure devices are not connected via another program already.
        If multiple Select lasers are connected to the same computer,
        specificy the port of the desired laser upon instantiation.

        Parameters
        ----------
        portname : str, optional
            Enter if portname for laser is known/multiple lasers are connected.
            If not supplied, system searches for laser. None by default.

        Raises
        ------
        RuntimeError
            Throws error if multiple NKT RF drivers are found on one computer.
            Supply portname for desired RF driver if multiple present.
        """
        print('Searching for connected NKT Laser...')
        self._portname = None  # COM port for laser. Auto found if not given.
        self._module_address = 16  # module address = 16 for RF driver
        self._device_type = None  # Should be 0x66 for RF driver
        self._RF_power_status = None
        self._wavelength_registers = { # Wavelength register channels 
            1: 0x90,
            2: 0x91,
            3: 0x92,
            4: 0x93,
            5: 0x94,
            6: 0x95,
            7: 0x96,
            8: 0x97
        }
        self._amplitude_registers = { # Amplitude register channels
            1: 0xB0,
            2: 0xB1,
            3: 0xB2,
            4: 0xB3,
            5: 0xB4,
            6: 0xB5,
            7: 0xB6,
            8: 0xB7
        }
        self._wavelength_channels = {} # Used to store wavelength settings
        self._amplitude_channels = {} # Used to store amplitude of wavelength

        if portname:  # Allow user to init specific NKT Laser on portname
            self._portname = portname
            self._device_type = 102  # Could put check here

        else:  # Search for connection w/ laser
            # Open available ports
            nktp.openPorts(nktp.getAllPorts(), 1, 1)

            # Get open NKT ports
            portlist = nktp.getOpenPorts().split(',')
            nkt_device_found = False

            for portName in portlist:  # Sweep open nkt ports
                # get binary devList of connected nkt devices
                comm_result, devList = nktp.deviceGetAllTypes(portName)
                # Get byte at location 15 (device address for select)
                device_type = devList[self.module_address]

                # Double check device_type matches select laser
                if hex(device_type) == '0x66':  # 102 == 0x66 in hex
                    if nkt_device_found:  # If select found on other port, error
                        err_msg = ('''Multiple NKT Lasers found on computer.
                        COM port 1 = %s
                        COM port 2 = %s
                        Please initialize Select class with designated \
                        portname to avoid conflict'''
                                   % (self.portname, portName))

                        raise RuntimeError(err_msg)

                    else:  # If this is first laser found,
                        nkt_device_found = True
                        self._portname = portName
                        self._device_type = device_type

        # Close all ports
        closeResult = nktp.closePorts('')
        if nkt_device_found:
            print('NKT Select Found:')
            print('Comport: ', self.portname, 'Device type: ', "0x%0.2X"
                  % self.device_type, 'at address:', self.module_address)

        else:
            print('No Select Module Found')

    module_address = property(lambda self: self._module_address)
    """`int`, read-only: Module address = 16 for RF driver."""

    device_type = property(lambda self: self._device_type)
    """`int`, read-only: Should be 102 (0x66) for RF driver.
    Assigned and checked during object init."""

    portname = property(lambda self: self._portname)
    """`str`, read-only: COM port for laser.
    Autofound during init if not given. User can supply when creating object.
    """

    @property
    def RF_power_status(self):
        """
        Reads the RF power output of the RF Driver to the SuperK Select is controlled with the RF 
        power register. Writing the following will either turn on/off the RF driver 
        0   -   Turns RF power off
        1   -   Turns RF power on

        Return
        ------
        tuple(int, str)
            (bit, Desription) returns on/off result of RF driver.
        """
        register_address = 0x30
        comm_result, reading = nktp.registerReadU8(self.portname,
                                                self.module_address,
                                                register_address, -1)

        if reading == 0:
            self._RF_power_status = (reading, 'RF driver is off')

        elif reading == 1:
            self._RF_power_status = (reading, 'RF driver is on')

        return self._RF_power_status
    
    @property
    def RF_setup_bits(self):
        """
        Reads the setup bits of the RF Driver:
        Bit 0   -   Used for temperature compensation. When this feature is on,
                    the RF driver output is compensated for filter temperature.
        Bit 1   -   Use optimal power table. When this feature is on, RF amplitude is
                    compensated for filter temperature.
        Bit 2   -   Blanking level. Can be used to set the Blanking level input high or
                    low, without having an actual blanking level input signal

        Return
        ------
        int
            (bit) returns setup bit of RF driver.
        """
        register_address = 0x31
        comm_result, reading = nktp.registerRead(self.portname,
                                                self.module_address,
                                                register_address, -1)

        return reading
    
    @property
    def get_min_wavelength(self):
        """
        Gets the minimum usable wavelength in nm of the RF Driver:

        Return
        ------
        int
            (wave) returns minimum usable wavelength of crystal.
        """
        register_address = 0x34
        comm_result, reading = nktp.registerReadU32(self.portname,
                                                self.module_address,
                                                register_address, -1)

        return reading/1000
    
    @property
    def get_max_wavelength(self):
        """
        Gets the maximum usable wavelength in nm of the RF Driver:

        Return
        ------
        int
            (wave) returns Maximum usable wavelength of crystal.
        """
        register_address = 0x35
        comm_result, reading = nktp.registerReadU32(self.portname,
                                                self.module_address,
                                                register_address, -1)

        return reading/1000
    
    @property
    def get_crystal_temperature(self):
        """
        Gets the temperature of the connected crystal in Celsius:

        Return
        ------
        int
            (temperature) returns temperature of crystal.
        """
        register_address = 0x38
        comm_result, reading = nktp.registerReadS16(self.portname,
                                                self.module_address,
                                                register_address, -1)

        return reading/10
    
    @property
    def get_connected_crystal(self):
        """
        Gets the index number of the current connected crystal. Crystals are
        numbered consecutively, so the crystals in the SuperK SELECT with the 
        lowest bus address are numbered 1 and 2, the crystals in the next SuperK 
        SELECT are numbered 3 and 4, etc.

        If the return value is 0, then no crystal is connected to the RF driver.
        This value is read-only, and changes automatically when the RF cable is 
        connected to or disconnected from SuperK SELECT RF-ports, or when the position
        of the RF switch in the SELECT is changed

        Return
        ------
        int
            (crystal index) returns index of connected crystal.
        """
        register_address = 0x75
        comm_result, reading = nktp.registerReadU8(self.portname,
                                                self.module_address,
                                                register_address, -1)

        return reading

    def set_RF_power(self, state):
        """
        Change RF power state to on/off

        Uses nktp_dll to write to 0 (off) or 1 (on) to register 0x30.

        Parameters
        ----------
        state : bool
            True turns laser on, false turns emission off
        """
        register_address = 0x30

        if state is True:
            print("RF driver on")
            nktp.registerWriteU8(self.portname, self.module_address,
                                register_address, 0x01, -1)
        elif state is False:
            print("RF driver off")
            nktp.registerWriteU8(self.portname, self.module_address,
                                register_address, 0x00, -1)
            
    def get_wavelength_channel(self, channel):
        """
        Reads the wavelength settings for the specified channel.

        Parameters
        ----------
        channel : int
            The channel number (1 to 8).

        Return
        ------
        list of int
            A list of 32-bit unsigned integers representing the wavelengths.
        """
        if channel not in self._wavelength_registers:
            raise ValueError("Invalid channel number. Must be between 1 and 8.")

        register_address = self._wavelength_registers[channel]
        comm_result, reading = nktp.registerReadU32(self.portname, self.module_address,
                                                         register_address, -1)
        
        return reading/1000

    def set_wavelength_channel(self, channel, wavelengths):
        """
        Set the wavelength settings for the specified channel.

        Parameters
        ----------
        channel : int
            The channel number (1 to 8).
        wavelengths : list of int
            A list of 32-bit unsigned integers. Only the first element is required if FSK mode is not used.
        """
        if channel not in self._wavelength_registers:
            raise ValueError("Invalid channel number. Must be between 1 and 8.")

        register_address = self._wavelength_registers[channel]

        # This is meant for FSK of wavelengths
        # if len(wavelengths) == 1:
        #     wavelengths.extend([0, 0, 0])  # Fill the rest with zeros if only one element is provided

        # if len(wavelengths) != 4:
        #     raise ValueError("Exactly 4 elements are required in the wavelength list")

        print(f"Setting wavelength for channel {channel}")
        result = nktp.registerWriteU32(self.portname, self.module_address, register_address,
                                                 int(wavelengths/0.001), -1)
        print(result)
        
    def get_amplitude_channel(self, channel):
        """
        Reads the amplitude setting for the specified channel.

        Parameters
        ----------
        channel : int
            The channel number (1 to 8).

        Return
        ------
        int
            The amplitude in tenths of a percent (permille, ‰).
        """
        if channel not in self._amplitude_registers:
            raise ValueError("Invalid channel number. Must be between 1 and 8.")

        register_address = self._amplitude_registers[channel]
        comm_result, reading = nktp.registerReadU16(self.portname,
                                                    self.module_address,
                                                    register_address, -1)

        return reading/10

    def set_amplitude_channel(self, channel, amplitude):
        """
        Set the amplitude setting for the specified channel.

        Parameters
        ----------
        channel : int
            The channel number (1 to 8).
        amplitude : int
            The amplitude in tenths of a percent (permille, ‰). Must be between 0 and 1000.
        """
        if channel not in self._amplitude_registers:
            raise ValueError("Invalid channel number. Must be between 1 and 8.")
        if not (0 <= amplitude <= 100):
            raise ValueError("Amplitude must be between 0 and 100 (%).")

        register_address = self._amplitude_registers[channel]

        print(f"Setting amplitude for channel {channel}")
        nktp.registerWriteU16(self.portname, self.module_address, register_address,
                                            int(amplitude/0.1), -1)