import clr
import os
import time

# Update this path if your Kinesis is installed elsewhere
KINESIS_PATH = r"C:\Program Files\Thorlabs\Kinesis"

# Load the required Kinesis .NET DLLs
clr.AddReference(os.path.join(KINESIS_PATH, "Thorlabs.MotionControl.DeviceManagerCLI.dll"))
clr.AddReference(os.path.join(KINESIS_PATH, "Thorlabs.MotionControl.KCube.LaserDiodeCLI.dll"))

from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.KCube.LaserDiodeCLI import KCubeLaserDiode

def control_laser(serial_no, turn_on=True):
    try:
        DeviceManagerCLI.BuildDeviceList()
    
        # Get all connected KLD101 serial numbers
        serials = DeviceManagerCLI.GetDeviceList(KCubeLaserDiode.DevicePrefix)
        if len(serials) == 0:
            print("No KLD101 devices found.")
            return
        # Create and connect to the device
        laser = KCubeLaserDiode.CreateKCubeLaserDiode(serial_no)
        laser.Connect(serial_no)

        # Wait until settings are initialized
        while not laser.IsSettingsInitialized():
            time.sleep(0.1)

        laser.StartPolling(250)
        time.sleep(0.1)  # Allow polling to stabilize
        laser.EnableDevice()

        if turn_on:
            laser.SetOn()
            print(f"Laser {serial_no} turned ON.")
        else:
            laser.SetOff()
            print(f"Laser {serial_no} turned OFF.")

        laser.StopPolling()
        laser.Disconnect()

    except Exception as e:
        print(f"Error controlling laser {serial_no}: {e}")
