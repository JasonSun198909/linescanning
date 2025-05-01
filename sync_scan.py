import nidaqmx
from nidaqmx.constants import (
    Edge,
    AcquisitionType,
    WAIT_INFINITELY,
)
import numpy as np
import matplotlib.pyplot as plt
import time 

def record_on_low_digital_trigger(
    data_channel, trigger_line, samples_per_channel, rate, timeout=10.0
):
    """
    Records analog data using NI-DAQmx after a digital trigger on the specified line goes low.

    Args:
        data_channel (str): The analog input channel for data acquisition (e.g., "Dev1/ai0").
        trigger_line (str): The digital input line for the trigger (e.g., "Dev1/PFI0").
        samples_per_channel (int): The number of samples to acquire per channel.
        rate (float): The sampling rate in samples per second per channel.
        timeout (float): The maximum time in seconds to wait for the trigger.

    Returns:
        numpy.ndarray or None: The acquired analog data, or None if a timeout occurs.
    """
    data = None
    try:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(data_channel)
            task.timing.cfg_samp_clk_timing(
                rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samples_per_channel
            )

            # Configure digital edge start trigger
            task.triggers.start_trigger.cfg_dig_edge_start_trig(
                trigger_line, trigger_edge=Edge.FALLING
            )

            print(f"Waiting for a low-going digital trigger on {trigger_line}...")
            task.start()

            try:
                data = task.read(
                    number_of_samples_per_channel=samples_per_channel, timeout=timeout
                )
                print("Data acquisition complete for this trigger.")
            except nidaqmx.errors.DAQmxTimeoutError:
                print(
                    "Timeout occurred while waiting for trigger or acquiring data."
                )
            except Exception as e:
                print(f"An error occurred during data acquisition: {e}")

    except nidaqmx.errors.DaqError as e:
        print(f"NI-DAQmx Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        return np.array(data) if data is not None else None


if __name__ == "__main__":
    # --- User Configuration ---
    analog_data_channel = "Dev1/ai0"  # Data signal on AI0
    digital_trigger_channel = "PFI0"  # Trigger signal on PFI0

    mirror_feedfrequency=120
    scan_freq=mirror_feedfrequency/3

    sampling_rate = 200000.0  # Samples per second
    num_samples = sampling_rate/scan_freq  # Number of samples to acquire after each trigger
    trigger_timeout = 5.0  # Timeout in seconds to wait for each trigger
    num_repetitions = 100  # Number of times to repeat the acquisition
    repetition_to_plot = 1  # The repetition number to plot (1-based index)
    delaytimer=0.01
    

    colors = plt.get_cmap('viridis', num_repetitions)

    # --- Perform Repeated Acquisition ---
    all_recorded_data = []
    time.sleep(5)
    for i in range(num_repetitions):
        print(f"\n--- Repetition {i+1} ---")
        acquired_data = record_on_low_digital_trigger(
            analog_data_channel,
            digital_trigger_channel,
            num_samples,
            sampling_rate,
            trigger_timeout,
        )
        time.sleep(delaytimer)
        if acquired_data is not None:
            all_recorded_data.append(acquired_data)
        else:
            print(f"Data acquisition failed for repetition {i+1}.")

    # --- Plot as an Image and Plot One Repetition ---
    if all_recorded_data:
        output_matrix = np.array(all_recorded_data)

        # Image Plot
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)  # Create a subplot for the image
        plt.imshow(
            np.flipud(output_matrix),
            aspect="auto",
            cmap="viridis",
            extent=[0, num_samples / sampling_rate, 0, num_repetitions],
        )
        plt.colorbar(label="Voltage (V)")
        plt.xlabel("Time (s)")
        plt.ylabel("Repetition Number")
        plt.title("Acquired Data as Image Over Multiple Triggers")
        plt.grid(False)

        #Line Plot of One Repetition
        plt.subplot(1, 2, 2)  # Create a subplot for the line plot
        if 1 <= repetition_to_plot <= len(all_recorded_data):
            data_to_plot = all_recorded_data[repetition_to_plot - 1]
            time = np.linspace(
                0, num_samples / sampling_rate, num_samples, endpoint=False
            )
            for i, data in enumerate(all_recorded_data):
                color = colors(i)  # Get a color from the colormap
                plt.plot(time, data, label=f"Repetition {i+1}", color=color)

            plt.xlabel("Time (s)")
            plt.ylabel("Voltage (V)")
            plt.title(f"Acquired Data for Repetition {repetition_to_plot}")
            plt.grid(True)
        else:
            print(
                f"Invalid repetition number specified for plotting: {repetition_to_plot}. "
                f"Please choose a value between 1 and {len(all_recorded_data)}."
            )

        plt.tight_layout()  # Adjust subplot parameters for a tight layout
        plt.show()
    else:
        print("No data was successfully acquired.")