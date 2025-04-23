from nkt_device import *
from example_selectk_laser_sweep import *
import rampscript
import numpy as np
import nidaqmx as ni
from nidaqmx.constants import AcquisitionType, TaskMode
from nidaqmx.constants import WAIT_INFINITELY
import matplotlib.pyplot as plt
import time
from datetime import timedelta
from datetime import datetime
import msvcrt     
import os 
def get_save_folder():
    # Ask for folder path in the terminal
    folder_path = input("Please enter the folder path to save files: ").strip()
    
    # Check if the path exists and is a directory
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        print(f"Selected folder: {folder_path}")
        return folder_path
    else:
        print(f"Error: '{folder_path}' is not a valid folder path")
        return None

def switch2right(min_wave,max_wave):

    stepsize = 20 # stepsize in nm
    delay_time = 2 # delay time in seconds


    # Set to normal operation
    rfdriver.set_RF_power(False)  # Turn off the RF driver
    aotf.set_switch_settings(0)  # Set to normal operation

    # Check that the right crystal is used through rf driver
    current_min_wave = rfdriver.get_min_wavelength
    current_max_wave = rfdriver.get_max_wavelength
    print(current_min_wave)
    print(current_max_wave)

    if current_min_wave <= min_wave and max_wave <= current_max_wave:
        print(f"Selected wavelengths are within the current crystal's range.")
    else:
        print(f"Selected wavelengths is not within the current crystal's range. Switching crystals...")
        rfdriver.set_RF_power(False)  # Turn off the RF driver
        aotf.set_switch_settings(1)  # Change to the appropriate crystal
    
        # # Recheck the range after changing the crystal
       # current_min_wave = rfdriver.get_min_wavelength()
      #
      #   current_max_wave = rfdriver.get_max_wavelength()
        
        time.sleep(2)
        current_min_wave = rfdriver.get_min_wavelength
        current_max_wave = rfdriver.get_max_wavelength
        print(current_min_wave)
        print(current_max_wave)
        if current_min_wave <= min_wave and max_wave <= current_max_wave:
            print(f"Select is ready for use.")
        else:
            print(f"Still outside crystal range. Check the selection.")
            

       

def scan(xsteps,ysteps,xmax,ymax,sr,duration):
    start_time = time.monotonic()
    x_volt = np.arange(xmax*-1, xmax+xsteps, xsteps)
    y_volt = np.arange(ymax*-1, ymax+ysteps, ysteps)
    points = (duration*sr) # how many points you want, depends on duration and sampling rate
    steps = ((2*xmax)*(2*ymax))/points # step size for each point divided evenly

    t = np.linspace(0, duration, int(duration*sr), endpoint=False)
   # t = np.linspace(0, duration, 10000, endpoint=False) # was 50000
    rampsig = (((2*xmax) / duration) * t) - xmax # equation to generate ramp voltage for QR code
    # rampsig = (((2*5.5) / duration) * t) - 8 # equation to generate ramp voltage for container
    # rampsig = np.linspace()
    testarray = [] # normal list
    
    #print(rampsig.shape[0])

    for yvolts in range(0, len(y_volt)):
      with ni.Task() as task: # reset voltage back to start
        task.ao_channels.add_ao_voltage_chan("Dev1/ao0") # adds voltage channel ao0 
        task.write(-xmax, auto_start=True) # assigns start voltage to task
        task.start() # task doesn't start unless this command is set
        task.stop() # stops task
        rampscript.move_galvomirror(y_volt[yvolts]) # uses galvo mirror to move down for y-axis
      #print("y = ", y_volt[yvolts]) # print current y-axis step, can be changed to a progress bar
      indata = rampscript.run_output(rampsig, sr) # array of measurements for one x-axis line scan
      testarray.append(indata)
    testarray = np.stack(testarray, axis=0)
    end_time = time.monotonic()
    print(timedelta(seconds=end_time - start_time))
    return testarray
     
def pause_and_count():
    start_time = time.time()
    print("\nProgram paused. Press Enter to continue...")
    
    while True:
        # Calculate and display elapsed time
        elapsed_time = time.time() - start_time
        print(f"\rElapsed time: {elapsed_time:.2f} seconds", end="", flush=True)
        
        # Check for Enter key press (Windows-specific)
        if msvcrt.kbhit():  # Check if a key has been pressed
            key = msvcrt.getch()  # Get the pressed key
            if key == b'\r':  # Enter key
                print("\n\n")  # Prints two empty lines
                break
                
        time.sleep(1)  # Small delay to prevent CPU overload




if __name__ == "__main__":

    laser = Fianium() # define Fianium class
    rfdriver = RF_driver() # define RF driver class
    aotf = Select() # define Seleck class
    min_wave=1450
    max_wave=1550
  # stepsize=50
   # wave=np.arange(min_wave,max_wave+1,stepsize)
    wave=[min_wave,max_wave]
    switch2right(min_wave,max_wave)
    # voltage steps for x and y-axis (V)
    xsteps = 0.1
    ysteps = 0.1
    # max/min voltage for x and y-axis (V)
    ymax = 9 # 3.4 for QR code, 9 for container 
    xmax = 9 # 1.7 for QR code
    sr = 1000000 # sample rate (Hz)
    duration = 0.01 # seconds (s)
    print(wave)
    print("sampling rate and duration for each ramp:", [sr,duration])
    current_wave = min_wave # starting wavelength

    rfdriver.set_amplitude_channel(1, 100) # sets channel 1 power to 100 percent
    rfdriver.set_RF_power(True) # set rf driver on
    laser.set_power(100) # sets laser power to 50%
    print(f"Fianium laser set to {laser.power_level}.")
    laser.set_emission(True) # set laser on
    pause_and_count()
    save_location = get_save_folder()

    if save_location:
        # You can now use this folder path for saving files
        print(f"Files will be saved in: {save_location}")
    else:
        print("Operation cancelled or invalid path provided")
              
    while True: 
        sample_name = input("Enter sample name (or type 'exit' to quit): ")
        if sample_name.lower() == 'exit':
            print("Exiting...")
            break
        datacube=[]
        np.savetxt(f"{save_location}sample_wave_{sample_name}.txt", wave, delimiter=',')

        # Set wavelength + amplitude to loop uyntil user cancels
        for iwave in wave:
            # rfdriver.set_wavelength_channel(1, 1550)
            # print(rfdriver.get_wavelength_channel(1))
            # Run code normally
          
            rfdriver.set_wavelength_channel(1, iwave) # set to current wavelength
            print(f"set channel 1:{iwave}")
            print(rfdriver.get_amplitude_channel(1))
            testarray=scan(xsteps,ysteps,xmax,ymax,sr,duration) 
            #  plt.imshow(testarray, extent = [0, 1, 0, 1], aspect = 'auto') # plots 2d measurement of surface
            #   plt.show()
            datacube.append(testarray)
               
            time.sleep(2) # delay depending on time defined
            
        datacube=np.stack(datacube,axis=0)
        print(datacube.shape)
        reshape_datacube=datacube.reshape(datacube.shape[0],-1)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        np.savetxt(f"{save_location}sample_data_{sample_name}_{timestamp}.txt", reshape_datacube, delimiter=',')
    #print(reshape_dat)
    rfdriver.set_RF_power(False) # set rf driver off
    laser.set_emission(False) # set laser off


     