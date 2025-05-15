import serial
import time

# Serial port settings for KLD101
port = 'COM3'  # Replace with your COM port (e.g., 'COM3' on Windows or '/dev/ttyUSB0' on Linux)
baud_rate = 115200
data_bits = 8
stop_bits = 1
parity = serial.PARITY_NONE

# APT protocol settings
destination = 0x50  # Generic USB device (KLD101 K-Cube)
source = 0x01       # Host PC
channel = 0x01      # Channel 1 (KLD101 is single-channel)

# Helper function to create APT command packet
def create_apt_packet(msg_id, param1, param2, dest, src, data=None):
    if data is None:
        # Short format: 6 bytes
        packet = bytearray(6)
        packet[0] = msg_id & 0xFF
        packet[1] = (msg_id >> 8) & 0xFF
        packet[2] = param1
        packet[3] = param2
        packet[4] = dest
        packet[5] = src
    else:
        # Long format: 6-byte header + data
        data_len = len(data)
        packet = bytearray(6 + data_len)
        packet[0] = msg_id & 0xFF
        packet[1] = (msg_id >> 8) & 0xFF
        packet[2] = data_len & 0xFF
        packet[3] = (data_len >> 8) & 0xFF
        packet[4] = dest | 0x80  # Set data packet bit
        packet[5] = src
        packet[6:] = data
    return packet

# Initialize serial port
try:
    ser = serial.Serial(
        port=port,
        baudrate=baud_rate,
        bytesize=data_bits,
        stopbits=stop_bits,
        parity=parity,
        timeout=1
    )
    print(f"Connected to {port}")

    # Command 1: Identify device (blinks LED panel)
    identify_cmd = create_apt_packet(
        msg_id=0x0223,  # MOD_IDENTIFY
        param1=channel,
        param2=0x00,
        dest=destination,
        src=source
    )
    ser.write(identify_cmd)
    print("Sent identify command (LED should blink)")
    time.sleep(1)  # Wait for command to process

    # Command 2: Enable laser output
    enable_cmd = create_apt_packet(
        msg_id=0x0210,  # LD_SET_CHANENABLESTATE
        param1=channel,
        param2=0x01,  # Enable channel
        dest=destination,
        src=source
    )
    ser.write(enable_cmd)
    print("Sent enable laser command")
    time.sleep(1)

    # Command 3: Set laser current to 50 mA
    current_ma = 50  # Desired current in mA
    current_code = int(current_ma * 100)  # Convert to 0.01 mA units (per protocol)
    current_data = bytearray([current_code & 0xFF, (current_code >> 8) & 0xFF])
    set_current_cmd = create_apt_packet(
        msg_id=0x0212,  # LD_SET_LASERDIODCURRENT
        param1=channel,
        param2=0x00,
        dest=destination,
        src=source,
        data=current_data
    )
    ser.write(set_current_cmd)
    print(f"Sent set current command to {current_ma} mA")
    time.sleep(1)

    # Command 4: Disable laser output
    disable_cmd = create_apt_packet(
        msg_id=0x0210,  # LD_SET_CHANENABLESTATE
        param1=channel,
        param2=0x02,  # Disable channel
        dest=destination,
        src=source
    )
    ser.write(disable_cmd)
    print("Sent disable laser command")
    time.sleep(1)

except serial.SerialException as e:
    print(f"Serial error: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("Serial port closed")