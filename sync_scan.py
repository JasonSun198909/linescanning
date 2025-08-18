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
import os # Import the os module for path manipulation
from connectStepper import send_serial_command

# def record_on_low_digital_trigger(
#     data_channel, trigger_line, samples_per_channel, rate, timeout=10.0
# ):
#     """
#     Records analog data using NI-DAQmx after a digital trigger on the specified line goes low.

#     Args:
#         data_channel (str): The analog input channel for data acquisition (e.g., "Dev1/ai0").
#         trigger_line (str): The digital input line for the trigger (e.g., "Dev1/PFI0").
#         samples_per_channel (int): The number of samples to acquire per channel.
#         rate (float): The sampling rate in samples per second per channel.
#         timeout (float): The maximum time in seconds to wait for the trigger.

#     Returns:
#         numpy.ndarray or None: The acquired analog data, or None if a timeout occurs.
#     """
#     data = None
#     try:
#         with nidaqmx.Task() as task:
#             task.ai_channels.add_ai_voltage_chan(data_channel)
#             task.timing.cfg_samp_clk_timing(
#                 rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samples_per_channel
#             )

#             # Configure digital edge start trigger
#             task.triggers.start_trigger.cfg_dig_edge_start_trig(
#                 trigger_line, trigger_edge=Edge.FALLING
#             )

#             print(
#                 f"Waiting for a low-going digital trigger on {trigger_line}...")
#             task.start()

#             try:
#                 data = task.read(
#                     number_of_samples_per_channel=samples_per_channel, timeout=timeout
#                 )
#                 print("Data acquisition complete for this trigger.")
#             except nidaqmx.errors.DAQmxTimeoutError:
#                 print(
#                     "Timeout occurred while waiting for trigger or acquiring data."
#                 )
#             except Exception as e:
#                 print(f"An error occurred during data acquisition: {e}")

#     except nidaqmx.errors.DaqError as e:
#         print(f"NI-DAQmx Error: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#     finally:
#         return np.array(data) if data is not None else None


if __name__ == "__main__":
    # --- User Configuration ---
    analog_data_channel = "Dev1/ai0"  # Data signal on AI0
    digital_trigger_channel = "/Dev1/PFI0"  # Trigger signal on PFI0
    counter = "Dev1/ctr0"              # Counter used to clock AI
    counter_internal = "/Dev1/Ctr0InternalOutput"

    #lasernumber = ["98250937", "98251034"]
    lasernumber = ["98251034"]
    laserwave = [1450, 1550]
    mirror_feedfrequency =120 #`120 `
    scan_freq = int(mirror_feedfrequency / 3)

    sampling_rate = 1000000.0  # Samples per second
    # Number of samples to acquire after each trigger
    num_samples = int(sampling_rate / scan_freq)
    #num_samples = 1000
    trigger_timeout = 5.0  # Timeout in seconds to wait for each trigger
    num_repetitions =1000  # Number of times to repeat the acquisition
    repetition_to_plot = 1  # The repetition number to plot (1-based index)
    delaytimer = 0.1
    veticalshift=200
    colors = plt.get_cmap('viridis', num_repetitions)

    # --- Prompt for Sample Name ---
    sample_name = input("Please enter a sample name (e.g., 'SampleA_run1'): ").strip()
    if not sample_name:
        sample_name = "untitled_sample" # Default name if nothing is entered
        print(f"No sample name entered, using default: '{sample_name}'")
    # Sanitize the sample_name for use in filenames (remove invalid characters)
    sample_name = "".join(c for c in sample_name if c.isalnum() or c in ('_', '-')).strip()


    # --- Create a directory for saving data if it doesn't exist ---
    save_directory = "acquired_laser_data"
    os.makedirs(save_directory, exist_ok=True)
    print(f"Saving data to: {os.path.abspath(save_directory)}")


    # --- Perform Repeated Acquisition ---
   # time.sleep(5) # Initial delay
    with nidaqmx.Task() as ai_task,nidaqmx.Task() as co_task:
        ai_task.ai_channels.add_ai_voltage_chan(analog_data_channel)
        ai_task.timing.cfg_samp_clk_timing(
            rate=sampling_rate, 
            source=counter_internal,
            active_edge=Edge.RISING,
            sample_mode=AcquisitionType.CONTINUOUS, 
            samps_per_chan=num_samples *2
        )
        co_task.co_channels.add_co_pulse_chan_freq(
            counter,
            freq=sampling_rate,
            duty_cycle=0.5
        )
        co_task.timing.cfg_implicit_timing(
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=num_samples
        )

        co_task.triggers.start_trigger.cfg_dig_edge_start_trig(
                 digital_trigger_channel, trigger_edge=Edge.FALLING
        )
        co_task.triggers.start_trigger.retriggerable = True

       # task.triggers.start_trigger.retriggerable=True
        # Start AI first so it's armed and waiting for the sample clock.
       # ai_task.start()
    # Start CO; it now waits for each falling edge to emit 100 pulses
        #co_task.start()
        print("waiting for triggers")
        

        for icurlaser in range(len(lasernumber)):
            print(f"\n--- Starting acquisition for Laser {lasernumber[icurlaser]} at {laserwave[icurlaser]} nm ---")
            
            # Reset data storage for each laser
            all_recorded_data = [] 

            control_laser(lasernumber[icurlaser], turn_on=False)  
            time.sleep(1) # Wait for laser to stabilize
            send_serial_command('COM4',veticalshift)

                # Start AI first so it's armed and waiting for the sample clock.
            ai_task.start()
        # Start CO; it now waits for each falling edge to emit 100 pulses
            co_task.start()
            print("waiting for triggers")
            n=1

            for i in range(num_repetitions):
                print(f"\n--- Repetition {i+1} ---")
                #time.sleep(delaytimer)
                acquired_data=ai_task.read(number_of_samples_per_channel=num_samples,timeout=trigger_timeout)
               # time.sleep(delaytimer)
               # if acquired_data is not None:
               # if (i + 1) % 2 == 0:
                all_recorded_data.append(acquired_data)
               # else:
               #     print("skip")
           # Clean up
            co_task.stop()
            ai_task.stop()

        # --- Process and Save Data for the current laser ---
            if all_recorded_data:
                output_matrix = np.array(all_recorded_data)
            # output_matrix=output_matrix.reshape(num_repetitions,num_samples)
                # Define filename for saving the output_matrix as CSV with sample name
                # Using current date and time for better uniqueness, considering NZST
                from datetime import datetime
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S") # Format: YYYYMMDD_HHMMSS

                filename = f"{sample_name}_laser_{laserwave[icurlaser]}nm_{current_time}.csv"
                filepath = os.path.join(save_directory, filename)
                
                # Save the matrix to a CSV file
                header = f"Acquired data for Sample: {sample_name}, Laser Wavelength: {laserwave[icurlaser]}nm\n" \
                        f"Rows: Repetition Number\n" \
                        f"Columns: Sample Number (time increasing)\n" \
                        f"Sampling Rate: {sampling_rate} Hz, Samples per Repetition: {num_samples}\n" \
                        f"Acquisition Date/Time (NZST): {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
                
              #  np.savetxt(filepath, output_matrix, delimiter=',', fmt='%.6f', header=header, comments='')
                print(f"Saved data for {sample_name} at {laserwave[icurlaser]}nm to {filepath}")

                # Image Plot
                plt.figure(figsize=(12, 6))
                plt.subplot(1, 2, 1)  # Create a subplot for the image
                plt.imshow(
                    np.flipud(output_matrix), # np.flipud flips the array vertically for plotting consistency
                    aspect="auto",
                    cmap="viridis",
                    extent=[0, num_samples, 0, num_repetitions],
                )
                plt.colorbar(label="Voltage (V)")
                plt.xlabel("Time (s)")
                plt.ylabel("Repetition Number")
                plt.title(f"Acquired Data as Image Over Multiple Triggers\nSample: {sample_name}, Wavelength: {laserwave[icurlaser]}nm")
                plt.grid(False)

                # Line Plot of all Repetitions
                plt.subplot(1, 2, 2)  # Create a subplot for the line plot
                timex = np.linspace(
                    0, num_samples / sampling_rate, num_samples, endpoint=False
                )
                
                for i, data in enumerate(all_recorded_data):
                    color = colors(i)  # Get a color from the colormap
                    plt.plot(timex, data, label=f"Repetition {i+1}", color=color)

                plt.xlabel("Time (s)")
                plt.ylabel("Voltage (V)")
                plt.title(f"All Acquired Data\nSample: {sample_name}, Wavelength: {laserwave[icurlaser]}nm")
                plt.grid(True)
                plt.legend(title="Repetitions", bbox_to_anchor=(1.05, 1), loc='upper left') # Add legend
                plt.tight_layout(rect=[0, 0, 0.9, 1]) # Adjust layout to make space for legend

                plt.show()
                
                control_laser(lasernumber[icurlaser], turn_on=False)
                time.sleep(1) # Small delay after turning off laser
                send_serial_command('COM4',-veticalshift)
                time.sleep(2)

            else:
                print(f"No data was successfully acquired for sample '{sample_name}' at laser {laserwave[icurlaser]}nm.")

    print("\n--- All laser acquisitions complete. ---")