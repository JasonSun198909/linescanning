"""
Example code to sweep laser wavelengths using SuperK Select
Damen Rajkumar
"""
from nkt_device import *
import time

def main():
    laser = Fianium() # define Fianium class
    rfdriver = RF_driver() # define RF driver class
    aotf = Select() # define Seleck class

    min_wave = 600 # minimum wavelength (nm)
    max_wave = 700 # maximum wavelength (nm)
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
        # current_max_wave = rfdriver.get_max_wavelength()
    
        if current_min_wave <= min_wave and max_wave <= current_max_wave:
            print(f"Select is ready for use.")
        else:
            print(f"Still outside crystal range. Check the selection.")

    print(current_min_wave)
    print(current_max_wave)
    current_wave = min_wave # starting wavelength
    rfdriver.set_amplitude_channel(1, 100) # sets channel 1 power to 100 percent
    rfdriver.set_RF_power(True) # set rf driver on

    laser.set_power(100) # sets laser power to 50%
    print(f"Fianium laser set to {laser.power_level}%.")
    laser.set_emission(True) # set laser on

    # Set wavelength + amplitude to loop uyntil user cancels
    while True:
        # rfdriver.set_wavelength_channel(1, 1550)
        # print(rfdriver.get_wavelength_channel(1))
        # Run code normally
        if current_wave < max_wave:
            rfdriver.set_wavelength_channel(1, current_wave) # set to current wavelength
            print(f"channel 1:{current_wave} ")
            print(rfdriver.get_amplitude_channel(1))
            # time.sleep(delay_time) # delay depending on time defined
            current_wave += stepsize # increment by 50nm
        else: 
            current_wave = min_wave # start at the beginning
            rfdriver.set_wavelength_channel(1, current_wave) # set to current wavelength
            print(rfdriver.get_amplitude_channel(1))
            # time.sleep(delay_time) # delay depending on time defined

        # Ask the user if they want to continue or stop
        user_input = input("Do you want to stop? (yes to stop, anything else to continue): ").strip().lower()
        if user_input == 'yes':
            print("Stopping the loop.")
            break


    rfdriver.set_RF_power(False) # set rf driver off
    laser.set_emission(False) # set laser off

if __name__ == "__main__":
    main()