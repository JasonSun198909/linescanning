import nidaqmx
from nidaqmx.constants import (
    Edge,
    AcquisitionType,
    WAIT_INFINITELY,
)
import numpy as np
import matplotlib.pyplot as plt
import time
from control_laser import control_laser # Assuming this module exists and works
import os 
from connectStepper import send_serial_command
from datetime import datetime # Import datetime here for general use


if __name__ == "__main__":
    # --- User Configuration ---
    analog_data_channel_1 = "Dev1/ai0"  # Data signal on AI0
    analog_data_channel_2 = "Dev1/ai1"  # Data signal on AI1
    digital_trigger_channel = "/Dev1/PFI0"  # Trigger signal on PFI0
    counter = "Dev1/ctr0"  # Counter used to clock AI
    counter_internal = "/Dev1/Ctr0InternalOutput"
    mirror_feedfrequency = 50 
    scan_freq = int(mirror_feedfrequency / 3)
    laserwave=[1650,1450]
    sampling_rate = 100000.0  # Samples per second
    # Number of samples to acquire after each trigger
    num_samples = int(sampling_rate / scan_freq)
    trigger_timeout = 5.0  # Timeout in seconds to wait for each trigger
    num_repetitions = 500  # Number of times to repeat the acquisition
    delaytimer = 0.1
    veticalshift = 200
    colors = plt.get_cmap('viridis', num_repetitions)

    while True:
        # --- Prompt for Sample Name ---
        prompt = f"Please enter a sample name (e.g., 'SampleA_1550nm'): "
        sample_name = input(prompt).strip()
        
        if sample_name.lower() == 'exit':
            print("Exiting...")
            break

        if not sample_name:
            sample_name = "untitled_sample"
            print(f"No sample name entered, using default: '{sample_name}'")
            
        # Sanitize the sample_name for use in filenames
        sample_name = "".join(c for c in sample_name if c.isalnum() or c in ('_', '-')).strip()


        # --- Create a directory for saving data if it doesn't exist ---
        save_directory = "C:/Data/acquired_laser_data"
        os.makedirs(save_directory, exist_ok=True)
        print(f"Saving data to: {os.path.abspath(save_directory)}")

        # --- Perform Acquisition for Single Laser ---
        try:
            # Set up DAQ tasks
            with nidaqmx.Task() as ai_task, nidaqmx.Task() as co_task:
                # --- AI Task Setup (Dual Channel) ---
                ai_task.ai_channels.add_ai_voltage_chan(analog_data_channel_1)
                ai_task.ai_channels.add_ai_voltage_chan(analog_data_channel_2) 
                
                ai_task.timing.cfg_samp_clk_timing(
                    rate=sampling_rate, 
                    source=counter_internal,
                    active_edge=Edge.RISING,
                    sample_mode=AcquisitionType.CONTINUOUS, 
                    samps_per_chan=num_samples * 2
                )
                
                # --- CO Task Setup (Clock Generator) ---
                co_task.co_channels.add_co_pulse_chan_freq(
                    counter,
                    freq=sampling_rate,
                    duty_cycle=0.5
                )
                co_task.timing.cfg_implicit_timing(
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=num_samples
                )

                # --- Trigger Setup (CO Task) ---
                co_task.triggers.start_trigger.cfg_dig_edge_start_trig(
                    digital_trigger_channel, trigger_edge=Edge.FALLING
                )
                co_task.triggers.start_trigger.retriggerable = True

                
                print("\n--- Starting acquisition nm ---")
                
                all_recorded_data = [] # Stores list of 2D arrays (2, num_samples)
                
                # --- Laser and Stepper Control (Pre-Acquisition) ---
                #control_laser(single_laser_id, turn_on=True)  
                #time.sleep(1) # Wait for laser to stabilize
                send_serial_command('COM4', veticalshift)
                time.sleep(delaytimer)

                # Start AI and CO tasks
                ai_task.start()
                co_task.start()
                print("Tasks armed, waiting for digital triggers...")

                successful_reads = 0
                
                # --- Repetitive Acquisition Loop with Exception Handling ---
                for i in range(num_repetitions):
                    print(f"--- Repetition {i+1}/{num_repetitions} ---", end='\r')
                    try:
                        # Read data: returns a 2D array (2 channels x num_samples)
                        acquired_data = ai_task.read(
                            number_of_samples_per_channel=num_samples,
                            timeout=trigger_timeout
                        )
                        all_recorded_data.append(acquired_data)
                        successful_reads += 1

                    except nidaqmx.errors.DaqReadError:
                        # Catch expected timeout error
                        print(f"\n[WARNING] Repetition {i+1} failed to acquire within timeout of {trigger_timeout}s. Skipping...")

                    except Exception as e:
                        # Catch critical errors
                        print(f"\n[ERROR] An unexpected error occurred on Repetition {i+1}: {e}")
                        break 
                        
                # Clean up DAQ tasks
                print("\nStopping DAQ tasks...")
                co_task.stop()
                ai_task.stop()

                # --- Process, Save, and Plot Data ---
                if all_recorded_data:
                    # Convert list of (2, N) arrays into a single (R, 2, N) array
                    output_3d_matrix = np.array(all_recorded_data)
                    
                    # Separate data into Channel 1 and Channel 2 matrices (R, N)
                    data_ch1 = output_3d_matrix[:, 0, :] 
                    data_ch2 = output_3d_matrix[:, 1, :]
                    
                    data_to_save = {
                        analog_data_channel_1: data_ch1,
                        analog_data_channel_2: data_ch2,
                    }

                    # --- Saving Data (One file per channel) ---
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

                    for idx, (channel_name, data_matrix) in enumerate(data_to_save.items()):
                        channel_suffix = channel_name.replace('/', '_') 
                        
                        filename = f"{sample_name}_laser_{laserwave[idx]}nm_{channel_suffix}_{current_time}.csv"
                        filepath = os.path.join(save_directory, filename)
                        
                        header = (
                            f"Acquired data for Sample: {sample_name}, Laser Wavelength: {laserwave[idx]}nm, Channel: {channel_name}\n"
                            f"Rows: Repetition Number | Columns: Sample Number (time increasing)\n"
                            f"Sampling Rate: {sampling_rate} Hz, Samples per Repetition: {num_samples}\n"
                            f"Acquisition Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        
                        np.savetxt(filepath, data_matrix, delimiter=',', fmt='%.6f', header=header, comments='')
                        print(f"Saved data for {channel_name} to {filepath}")


                    # --- Plotting Data ---
                    plt.figure(figsize=(16, 8)) 
                    
                    # Time base for plots
                    timex = np.linspace(0, num_samples / sampling_rate, num_samples, endpoint=False)
                    
                    # --- Channel 1 Image Plot (Top Left) ---
                    plt.subplot(2, 2, 1) 
                    plt.imshow(
                        np.flipud(data_ch1), 
                        aspect="auto",
                        cmap="viridis",
                        extent=[0, timex[-1], 0, data_ch1.shape[0]],
                    )
                    plt.colorbar(label="Voltage (V)")
                    plt.xlabel("Time (s)")
                    plt.ylabel("Repetition Number")
                    plt.title(f"Image - {analog_data_channel_1} (Wavelength: {laserwave[0]}nm)")
                    
                    # --- Channel 2 Image Plot (Bottom Left) ---
                    plt.subplot(2, 2, 3) 
                    plt.imshow(
                        np.flipud(data_ch2), 
                        aspect="auto",
                        cmap="inferno", 
                        extent=[0, timex[-1], 0, data_ch2.shape[0]],
                    )
                    plt.colorbar(label="Voltage (V)")
                    plt.xlabel("Time (s)")
                    plt.ylabel("Repetition Number")
                    plt.title(f"Image - {analog_data_channel_2} (Wavelength: {laserwave[1]}nm)")
                    
                    # --- Combined Average Line Plot (Right Side) ---
                    plt.subplot(1, 2, 2) 
                    
                    plt.plot(timex, np.mean(data_ch1, axis=0), label=f"Average {analog_data_channel_1}", color='C0', linewidth=2)
                    plt.plot(timex, np.mean(data_ch2, axis=0), label=f"Average {analog_data_channel_2}", color='C1', linewidth=2)
                    
                    plt.xlabel("Time (s)")
                    plt.ylabel("Voltage (V)")
                    plt.title(f"Average of All Repetitions\nSample: {sample_name}")
                    plt.grid(True)
                    plt.legend()
                    plt.tight_layout() 
                    plt.show()
                    
                    # --- Laser and Stepper Control (Post-Acquisition) ---
                    #control_laser(single_laser_id, turn_on=False)
                   # time.sleep(1)
                    send_serial_command('COM4', -veticalshift)
                    time.sleep(2)
                
                else:
                    print(f"No data was successfully acquired for sample '{sample_name}")

            print("\n--- Acquisition complete. ---")
            
        except nidaqmx.DaqError as e:
            print(f"\n[CRITICAL NI-DAQmx ERROR] The program encountered a critical DAQ error. Please check your device connections and channel names.")
            print(f"Error Details: {e}")
        except Exception as e:
            print(f"\n[CRITICAL PYTHON ERROR] An unexpected error occurred: {e}")
            
    # Final cleanup before exiting the main loop
    print("Program finished.")