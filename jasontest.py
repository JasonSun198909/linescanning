import nidaqmx
import time

# Create a task
with nidaqmx.Task() as task:
    # Add an analog input channel
    # Replace 'Dev1/ai0' with your actual device and channel name
    task.ai_channels.add_ai_voltage_chan(
        "Dev1/ai0",
        min_val=-10.0,  # Minimum expected voltage
        max_val=10.0    # Maximum expected voltage
    )
    
    # Configure sample clock timing
    #task.timing.cfg_samp_clk_timing(1000)  # Sample rate in Hz
    
    print("Starting measurements (press Ctrl+C to stop)...")
    try:
        while True:
            # Read a single sample0
            value = task.read()
            
            # Print the value with timestamp
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Measured voltage: {value:.3f} V")
            
            # Wait 1 second
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nMeasurement stopped by user")
    except nidaqmx.DaqError as e:
        print(f"Error occurred: {e}")
