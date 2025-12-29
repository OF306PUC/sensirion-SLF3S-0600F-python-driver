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
from i2c_command import ShdlcCmdGetI2cSlaveAddress, \
    ShdlcCmdI2cTransceive
from interface import ShdlcI2CInterface
from port import ShdlcSerialPort

import os 
import time 
import threading
import argparse
import core
import queue as queue_module

# Linux: 
serial_port_ = "/dev/ttyUSB0"
baudrate_ = 115200
slave_address_ = 0x00       # Sensor Bridge default address. RS485 address is 0
queue_size_ = 1000

hours_to_log_ = 12.0       # hours
sampling_interval_ = 500   # ms


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sensirion SHDLC data logger"
    )
    parser.add_argument("--port", type=str, default=serial_port_,
        help=f"Serial port (default: {serial_port_})"
    )
    parser.add_argument("--baudrate", type=int, default=baudrate_,
        help=f"Serial port baudrate (default: {baudrate_})"
    )
    parser.add_argument("--slave-address", type=int, default=slave_address_,
        help=f"SHDLC slave address (default: {slave_address_})"
    )
    parser.add_argument("--hours-to-log", type=float, default=hours_to_log_,
        help="Number of hours to log data (default: 12.0)"
    )
    parser.add_argument("--sampling-ms", type=int, default=sampling_interval_,
        help="Sampling interval in milliseconds (default: 500)"
    )
    return parser.parse_args()


def init_csv_logger(file_path, queue): 
    """
    Threaded CSV logger for SHDLC sensor data.
    """
    data_dir = 'Temp/'
    os.makedirs(os.path.dirname(data_dir), exist_ok=True)
    with open(data_dir+file_path, 'w') as f: 
        f.write("RelativeTime_s,Flow_ul_min,Flow_ml_hr,FlowTemperature_degC,"\
                "Flag_Air,Flag_High_Flow,Exp_Smoothing\n")
        while True: 
            try: 
                item = queue.get(timeout=1)
            except queue_module.Empty:
                continue
            time_rel, flow_ul_min, flow_ml_hr, temp_c, flag_air, flag_high_flow, exp_smoothing = item
            f.write(f"{time_rel:.6f},{flow_ul_min:.6f},{flow_ml_hr:.6f},{temp_c:.6f}"
                    f",{flag_air},{flag_high_flow},{exp_smoothing}\n")
            f.flush()


def in_device_communication(port, baudrate, queue, slave_address, 
                            hours_to_log=hours_to_log_, sampling_interval=sampling_interval_): 
    """
    Threaded SHDLC device communication via serial port.
    - Reads data from the SHDLC device and puts it into a queue.
    """
    with ShdlcSerialPort(port=port, baudrate=baudrate) as shdlc_port:
        interface = ShdlcI2CInterface(port=shdlc_port)

        # Get I2C slave address
        get_i2c_addr_cmd = ShdlcCmdGetI2cSlaveAddress()
        i2c_addr, error = interface.execute(slave_address,get_i2c_addr_cmd)
        print(f"Sensor I2C Address: {i2c_addr:#04x}, Error state: {error}")
        time.sleep(1)

        # Stopping continuous measurement 
        transceive_stop_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            tx_data=ShdlcCmdI2cTransceive._STOP_CODE,
            rx_length=0,
            max_response_time=0.1
        )
        data, error  = interface.i2c_execute(slave_address, transceive_stop_cmd)
        print("--- Stopping continuous measurement ---")
        print("Data received from stop command:", data)
        print("Error state from stop command:", error)
        time.sleep(1)

        # I2C Transceive command to start continuous measurement
        transceive_start_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            tx_data=ShdlcCmdI2cTransceive._MEDIUM_WATER,
            rx_length=0,
            max_response_time=0.1
        )
        data, error  = interface.i2c_execute(slave_address, transceive_start_cmd)
        print("--- Starting continuous measurement ---")
        print("Data received from start command:", data)
        print("Error state from start command:", error)
        time.sleep(1)

        # Read measurement data in a loop
        i2c_header = (ShdlcCmdI2cTransceive._I2C_ADDRESS << 1) | \
                ShdlcCmdI2cTransceive._READ_BIT 
        transceive_cmd = ShdlcCmdI2cTransceive(
            i2c_addr=ShdlcCmdI2cTransceive._I2C_ADDRESS,
            tx_data=[i2c_header],       # Read measurement command
            rx_length=9,                # 9 bytes max for SLF3S-0600F sensor
            max_response_time=0.1
        )  

        seconds_to_log = 3600 * hours_to_log
        num_measurements = seconds_to_log * 1000 // sampling_interval
        print(f"Logging for {hours_to_log} hours, total measurements: {num_measurements}")
        measurement_count = 0
        time.sleep(1)

        start_time = time.time()
        while True: 
            if measurement_count >= num_measurements:
                # Send stop command before breaking
                data, error  = interface.i2c_execute(slave_address, transceive_stop_cmd)
                print("--- Stopping continuous measurement ---")
                print("Data received from stop command:", data)
                print("Error state from stop command:", error)
                break
            
            t0 = time.time()
            # reading data from sensor: 
            data, error  = interface.i2c_execute(slave_address, transceive_cmd)    
            if error: 
                print("Error state received during measurement read.")
                continue
            flow_ul_min, flow_ml_hr, temp, air_flag, high_flow_flag, exp_smoothing = \
                core.interpret_flow_temp_raw(data)
            
            # print(f"Flow ul/min: {flow_ul_min}, Flow ml/hr: {flow_ml_hr}, Temp degC: {temp},"\
            #       f"Air-in-line: {air_flag}, High-flow: {high_flow_flag}")
            t = time.time() - start_time
            queue.put((float(t), float(flow_ul_min), float(flow_ml_hr), float(temp), \
                       int(air_flag), int(high_flow_flag), int(exp_smoothing)))

            t1 = time.time()
            elapsed_ms = (t1 - t0) * 1000
            sleep_time_ms = sampling_interval - elapsed_ms
            if sleep_time_ms > 0: 
                time.sleep(sleep_time_ms / 1000.0)

            measurement_count += 1


def main():
    args = parse_args()

    serial_port = args.port
    baudrate = args.baudrate
    slave_address = args.slave_address
    hours_to_log = args.hours_to_log
    sampling_interval_ms = args.sampling_ms

    print(f"Logging for {hours_to_log} hours")
    print(f"Sampling interval: {sampling_interval_ms} ms")

    queue_process = queue_module.Queue(maxsize=queue_size_)

    t_comm = threading.Thread(
        target=in_device_communication,
        args=(serial_port, baudrate, queue_process, slave_address,
            hours_to_log, sampling_interval_ms,),
        daemon=True,
    )

    t_logger = threading.Thread(
        target=init_csv_logger,
        args=("DataLog.csv", queue_process,),
        daemon=True,
    )

    t_comm.start()
    t_logger.start()

    while True:
        time.sleep(1)



if __name__ == "__main__":
    main()
