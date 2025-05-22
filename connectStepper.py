import serial
import time

def send_serial_command(com_port, move_value):
    """
    Sends a moveTo command with a numeric value to a serial device and returns the response.
    
    Args:
        com_port (str): The serial port to use (e.g., 'COM4')
        move_value (int/float): The numeric value for the moveTo command
        baud_rate (int): Baud rate for serial communication (default: 9600)
        timeout (float): Read timeout in seconds (default: 2)
    
    Returns:
        str: Device response or error message
    """
    try:
        baud_rate=9600
        timeout=2
        # Construct the command with the numeric value
        command = f"moveTo {move_value}\r\n"
        
        with serial.Serial(com_port, baud_rate, timeout=timeout) as ser:
            # Wait briefly for port to initialize
            time.sleep(0.5)
            
            # Print port info
            print(f"Connected to {ser.name}")
            ser.dtr = False
            
            # Clear input buffer
            ser.reset_input_buffer()
            
            # Send command
            print(f"Sending command: {command.strip()}")
            response = ser.readline().decode('utf-8').strip()

            ser.write(command.encode('utf-8'))
            
                
    except serial.SerialException as e:
        error_msg = f"Serial communication error: {e}"
        print(error_msg)
        return error_msg
    except UnicodeDecodeError as e:
        error_msg = f"Error decoding response: {e}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        return error_msg
    finally:
        print("Serial communication session ended")
