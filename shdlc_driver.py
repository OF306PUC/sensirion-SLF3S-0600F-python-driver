"""
Sensirion SHDLC Driver Module
- Runs a dual threaded architecture to handle SHDLC communication via serial port.
- Uses Sensirion SCC1-RS485 and SCC1-USB adapters for communication.
"""

# In order to run in Raspberry Pi / Linux systems, the following steps are needed to load the FTDI driver:
"""
Linux FTDI driver loading: 
- Run the following as root: 
    1. modprobe ftdi_sio
    2. echo 0403 7168 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id
- The above commands will only add the Sensor Bridge dynamically until reboot. 
- Automation on startup creating a custom udev rule: 
    SUBSYSTEMS=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="7168", RUN+="/sbin/modprobe ftdi_sio", RUN+="/bin/sh -c  \
        'echo 0403 7168 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"
    
    udevadm control --reload-rules
    
    udevadm trigger
"""
from queue import Queue
from i2c_command import ShdlcCmdGetI2cSlaveAddress, \
    ShdlcCmdI2cTransceive
from interface import ShdlcI2CInterface
from port import ShdlcSerialPort

import os 
import time 
import threading

serial_port_ = "/dev/ttyUSB1"
baudrate_ = 115200
slave_address_ = 0x00       # Sensor Bridge default address. RS485 address is 0
queue_size_ = 1000
sampling_interval_ = 5000   # ms


def init_csv_logger(file_path, queue): 
    """
    Threaded CSV logger for SHDLC sensor data.
    """
    data_dir = 'data/'
    os.makedirs(os.path.dirname(data_dir), exist_ok=True)
    with open(data_dir+file_path, 'w') as f: 
        f.write("RelativeTime_s,Flow_ul_min,Temperature_degC,Flag_Air,Flag_High_Flow\n")
        while True: 
            item = queue.get(timeout=1)
            time_rel, flow_ul_min, temp_c, flag_air, flag_high_flow = item
            f.write(f"{time_rel},{flow_ul_min},{temp_c},{flag_air},{flag_high_flow}\n")
            f.flush()


def in_device_communication(port, baudrate, queue, slave_address, sampling_interval): 
    """
    Threaded SHDLC device communication via serial port.
    - Reads data from the SHDLC device and puts it into a queue.
    """
    with ShdlcSerialPort(port=port, baudrate=baudrate) as shdlc_port:
        interface = ShdlcI2CInterface(port=shdlc_port)

        # [CHECK] Get I2C slave address
        get_i2c_addr_cmd = ShdlcCmdGetI2cSlaveAddress()
        i2c_addr, error = interface.execute(get_i2c_addr_cmd)
        print(f"Sensor I2C Address: {i2c_addr:#04x}, Error state: {error}")

        # [CHECK] I2C Transceive command to start continuous measurement
        transceive_start_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            tx_data=ShdlcCmdI2cTransceive._MEDIUM_WATER,
            rx_length=0,
            max_response_time=0.1
        )
        interface.i2c_execute(slave_address, transceive_start_cmd)

        # [CHECK] Read measurement data in a loop
        i2c_header = (ShdlcCmdI2cTransceive._I2C_ADDRESS << 1) | \
                ShdlcCmdI2cTransceive._READ_BIT 
        transceive_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            tx_data=b'\x00',            #[i2c_header],       # Read measurement command
            rx_length=9,                # 9 bytes max for SLF3S-0600F sensor
            max_response_time=0.1
        )

        # [CHECK] Stopping continuous measurement 
        transceive_stop_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            tx_data=ShdlcCmdI2cTransceive._STOP_CODE,
            rx_length=0,
            max_response_time=0.1
        )

        start_time = time.time()
        while True: 
            t0 = time.time()
            flow_raw, temp_raw, air_in_line_flag, high_flow_flag = interface.i2c_execute(
                                                                                slave_address, transceive_cmd)    

            print(f"Raw Flow: {flow_raw}, Raw Temp: {temp_raw}, Air-in-line: {air_in_line_flag}, High-flow: {high_flow_flag}")

            time_rel = time.time() - start_time

            queue.put((float(time_rel), float(flow_raw), float(temp_raw), int(air_in_line_flag), int(high_flow_flag)))

            t1 = time.time()
            elapsed_ms = (t1 - t0) * 1000
            sleep_time_ms = sampling_interval - elapsed_ms
            if sleep_time_ms > 0: 
                time.sleep(sleep_time_ms / 1000.0)


def main(): 
    queue_ = Queue(maxsize=1000)

    t_comm = threading.Thread(
        target=in_device_communication, 
        args=(serial_port_, baudrate_, queue_, slave_address_, sampling_interval_), 
        daemon=True)

    t_logger = threading.Thread(
        target=init_csv_logger, args=("sensor_data_log.csv", queue_), daemon=True)

    t_comm.start()
    t_logger.start()

    while True:
        time.sleep(1)  # keep main alive


if __name__ == "__main__":
    main()

# __baudrate__ = 115200
# __data_bits__ = 8               # LSB first
# __interbyte_timeout__ = 200     # ms
# __slv_response_timeout__ = 500  # ms

# # MOSI frame: | Start (0x7E) | Addr (1 byte) | Cmd (1 byte) | Len (1 byte) | Tx Data (0 ...255 bytes) | CRC (or CHK 1 byte) | Strop (0x7E) |
# # MISO frame: | Start (0x7E) | Addr (1 byte) | State (1 byte) | Len (1 byte) | Rx Data (0 ...255 bytes) | CRC (or CHK 1 byte) | Strop (0x7E) |


# class ShdlcSerialPort: 
#     """
#     SHDLC transceiver via serial port (e.g. UART/RS485). 

#     This class implements the SHDLC interface over the serial port. 
#     It uses Sensirion SCC1-RS485 and SCC1-USB adapters for communication.

#     (Is an adaptation of sensirion-shdlc-driver-python library.)

#     .. note:: This class can be used in a "with"-statement, and it's
#             recommended to do so as it automatically closes the port after
#             using it.
#     """
    
#     def __init__(self, port, baudrate, additional_response_time=0.1, 
#                  do_open=True): 
        
#         self._additional_response_time = float(additional_response_time)
#         self._lock = threading.RLock()
#         self._serial = serial.Serial(
#             port=port,
#             baudrate=baudrate,
#             bytesize=__data_bits__,
#             timeout=__slv_response_timeout__/1000.0,
#             inter_byte_timeout=__interbyte_timeout__/1000.0
#         )


# slave_address = 0x00 # Sensor Bridge default address. RS485 address is 0
# _START_STOP_BYTE = 0x7E
# _ESCAPE_BYTE = 0x7D
# _ESPAPE_XOR = 0x20
# _CHARS_TO_ESCAPE = [_START_STOP_BYTE, _ESCAPE_BYTE, 0x11, 0x13]

# def stuff_data_bytes(data): 
#     """
#     SHDLC needed byte stuffing
#     """
#     result = bytearray()
#     for byte in data:
#         if byte in _CHARS_TO_ESCAPE:
#             result.append(_ESCAPE_BYTE)
#             result.append(byte ^ _ESPAPE_XOR)
#         else:
#             result.append(byte)
#     return result



# def calculate_checksum(frame): 
#     return ~sum(frame) & 0xFF

# def mosi_frame_builder(slave_address, command, data): 
#     slv_addr = int(slave_address) & 0xFF
#     cmd = int(command) & 0xFF
#     data_bytes = bytes(bytearray(data))

#     # to bytes: 
#     frame_content = bytearray([slv_addr, cmd, len(data_bytes)]) + bytearray(data_bytes)
#     frame_content.append(calculate_checksum(frame_content))
#     raw_frame = bytearray()
#     raw_frame.append(_START_STOP_BYTE)
#     raw_frame.extend(stuff_data_bytes(frame_content))
#     raw_frame.append(_START_STOP_BYTE)
#     return bytes(raw_frame)

# def miso_frame_builder(raw_frame): 
#     """
#     Parse MISO frame from raw bytes: 
#     | Start (0x7E) | Addr (1 byte) | State (1 byte) | Len (1 byte) | Rx Data (0 ...255 bytes) | CRC (or CHK 1 byte) | Strop (0x7E) |
#     """



#     if raw_frame[0] != _START_STOP_BYTE or raw_frame[-1] != _START_STOP_BYTE:
#         raise ValueError("Invalid start/stop bytes")

#     # Unstuff data bytes
#     data = bytearray()
#     i = 1
#     while i < len(raw_frame) - 1:
#         byte = raw_frame[i]
#         if byte == _ESCAPE_BYTE:
#             i += 1
#             byte = raw_frame[i] ^ _ESPAPE_XOR
#         data.append(byte)
#         i += 1

#     # Parse frame content
#     slv_addr = data[0]
#     state = data[1]
#     length = data[2]
#     rx_data = data[3:3+length]
#     checksum = data[3+length]

#     # Verify checksum
#     if calculate_checksum(data[:-1]) != checksum:
#         raise ValueError("Invalid checksum")

#     return slv_addr, state, rx_data


# if __name__ == "__main__":

#     port = "/dev/ttyUSB1"
#     baudrate = 115200
    
#     _serial = serial.Serial(
#         port=port,
#         baudrate=baudrate,
#         bytesize=serial.EIGHTBITS,
#         stopbits=serial.STOPBITS_ONE,
#         timeout=0.01, 
#         xonxoff=False,
#     )

#     # Get device address command: comand_id = 0x90
#     # Get baudrate command: command_id = 0x91
#     raw_frame = mosi_frame_builder(slave_address=0x00, command=0x25, data=[])
#     print("Sending frame:", raw_frame)


#     while True: 
#         _serial.write(raw_frame)
#         time.sleep(0.1)
#         line = _serial.readline()
#         print("Received:", line)
        
#         time.sleep(5)
#          ###############




