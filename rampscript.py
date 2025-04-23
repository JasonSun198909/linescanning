import numpy as np
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType, TaskMode
from nidaqmx.constants import WAIT_INFINITELY
import matplotlib.pyplot as plt
import time
from datetime import timedelta

"""
Simple python code to scan a 2D surface using the USB-6259
Device Name: Dev2
Damen Rajkumar, 21/03/2023
"""    
  # first change by jason  
  # this frist branch change 
"""
Queries Device name, product type and availabel input and output channels
"""    
def query_devices():    
  local = ni.system.System.local()
  for device in local.devices:
    print(f'Device Name: {device.name}, Product Type: {device.product_type}')
    print('Input channels:', [chan.name for chan in device.ai_physical_chans])
    print('Output channels:', [chan.name for chan in device.ao_physical_chans])

"""
move_galvomirror (Name should be changed)
Function to move x- or y-axis mirror down or across as the opposing mirror scans across/along.
Currently uses ao1 to output voltages
Parameters:
  -----------
  data: 
    single data input to output from analog output.  
"""
def move_galvomirror(data, output_mapping=['Dev1/ao1']):
  max_out_range = 10 # output range of USB-6001
  max_outdata = np.max(np.abs(data))
  if max_outdata > max_out_range:
    raise ValueError(
      f"outdata amplitude ({max_outdata:.2f}) larger than allowed range"
      f"(+-{max_out_range}).")

  with ni.Task() as write_task:
    for o in output_mapping:
      aochan = write_task.ao_channels.add_ao_voltage_chan(o)
      aochan.ao_max = max_out_range
      aochan.ao_min = -max_out_range
      
    # trigger write_task as soon as read_task starts
    write_task.write(data, auto_start=True)
    write_task.start()  # write_task doesn't start at read_task's start_trigger without this
    time.sleep(0.0005) # 0.1 is 100ms, delay for mirror
  return
  
def run_output(data, sr, input_mapping=['Dev1/ai0'], output_mapping=['Dev1/ao0']):
  """Simultaneous playback and recording though NI device.
  Got it from https://github.com/ni/nidaqmx-python/issues/162
  Parameters:
  -----------
  data: 
    single data input to output from analog output.  
  sr: int
    Samplerate
  input_mapping: list of str
    Input device channels
  output_mapping: list of str
    Output device channels

  Returns
  -------
  output voltage measured by analog input
    Recorded data

  """
  max_out_range = 10 # output range of USB-6001
  max_in_range = 10   # input range of USB-6001
  max_outdata = np.max(np.abs(data))
  if max_outdata > max_out_range:
    raise ValueError(
      f"outdata amplitude ({max_outdata:.2f}) larger than allowed range"
      f"(+-{max_out_range}).")

  data = np.asarray(data).T
  nsamples = data.shape[0]
  # nsamples = 10
  # print(data.shape[0])
  with ni.Task() as read_task, ni.Task() as write_task:
    for o in output_mapping: # assigns analog output voltage channels
      aochan = write_task.ao_channels.add_ao_voltage_chan(o)
      aochan.ao_max = max_out_range
      aochan.ao_min = -max_out_range
    for i in input_mapping: # assigns analog input voltage channels
      aichan = read_task.ai_channels.add_ai_voltage_chan(i)
      aichan.ai_min = -max_in_range
      aichan.ai_max = max_in_range

    for task in (read_task, write_task):
      task.timing.cfg_samp_clk_timing(sr, samps_per_chan=nsamples) # timing settings set depending on sampling rate
   # trigger write_task as soon as read_task starts
    write_task.triggers.start_trigger.cfg_dig_edge_start_trig(read_task.triggers.start_trigger.term)
    write_task.write(data, auto_start=False)
    # print(data)
    write_task.start()  # write_task doesn't start at read_task's start_trigger
                        # without this               
    indata = read_task.read(nsamples, timeout=1) # do not time out
    # print(indata)
                                                               # for long inputs WAIT_INFINITELY
  return np.asarray(indata).T

if __name__ == "__main__":
    start_time = time.monotonic()
    query_devices()

    # voltage steps for x and y-axis (V)
    xsteps = 0.2
    ysteps = 0.2
    # max/min voltage for x and y-axis (V)
    ymax = 9 # 3.4 for QR code, 9 for container 
    xmax = 9 # 1.7 for QR code
    print(ymax)
    # voltage array for x and y mirror range
    x_volt = np.arange(xmax*-1, xmax+xsteps, xsteps)
    y_volt = np.arange(ymax*-1, ymax+ysteps, ysteps)
    sr = 100000 # sample rate (Hz)
    duration = 0.01 # seconds (s)
    points = (duration*sr) # how many points you want, depends on duration and sampling rate
    steps = ((2*xmax)*(2*ymax))/points # step size for each point divided evenly

    t = np.linspace(0, duration, int(duration*sr), endpoint=False)
   # t = np.linspace(0, duration, 1000, endpoint=False) # was 50000
    rampsig = (((2*xmax) / duration) * t) - xmax # equation to generate ramp voltage for QR code
    # rampsig = (((2*5.5) / duration) * t) - 8 # equation to generate ramp voltage for container
    # rampsig = np.linspace()
    testarray = [] # normal list
    
    print(rampsig.shape[0])

    for yvolts in range(0, len(y_volt)):
      with ni.Task() as task: # reset voltage back to start
        task.ao_channels.add_ao_voltage_chan("Dev1/ao0") # adds voltage channel ao0 
        task.write(-xmax, auto_start=True) # assigns start voltage to task
        task.start() # task doesn't start unless this command is set
        task.stop() # stops task
      indatay = move_galvomirror(y_volt[yvolts]) # uses galvo mirror to move down for y-axis
      print("y = ", y_volt[yvolts]) # print current y-axis step, can be changed to a progress bar
      indata = run_output(rampsig, sr) # array of measurements for one x-axis line scan
      testarray.append(indata)
    testarray = np.stack(testarray, axis=0)
    end_time = time.monotonic()
    print(timedelta(seconds=end_time - start_time))
    print(testarray.shape)
    np.savetxt('yellow_1310_3.txt', testarray, delimiter=',')
    plt.imshow(testarray, extent = [0, 1, 0, 1], aspect = 'auto') # plots 2d measurement of surface
    plt.show()

  