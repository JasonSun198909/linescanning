import nidaqmx as ni
import time  
def query_devices():    
  local = ni.system.System.local()
  for device in local.devices:
    print(f'Device Name: {device.name}, Product Type: {device.product_type}')
    print('Input channels:', [chan.name for chan in device.ai_physical_chans])
    print('Output channels:', [chan.name for chan in device.ao_physical_chans])

query_devices()
# Create a task

with ni.Task() as task:
    # Add analog output channel
    task.ao_channels.add_ao_voltage_chan("Dev1/ao0")
    
    # Define two voltage values
    voltage1 = 8  # First voltage
    voltage2 = -5 # Second voltage
    time.sleep(10)
    task.write(2)
    # try:
    #     while True:
    #         task.write(voltage1)
    #         time.sleep(10)
    #         task.write(voltage2)
    #         time.sleep(1)
    #         print("lala")
    # except KeyboardInterrupt:
    #     print("Stopped by user")