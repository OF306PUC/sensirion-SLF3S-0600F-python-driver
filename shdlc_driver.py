"""
Sensirion SHDLC Driver Module
- Runs a dual threaded architecture to handle SHDLC communication via serial port.
- Uses Sensirion SCC1-RS485 and SCC1-USB adapters for communication.
"""

# USB Serial driver note
# ---------------------
# Sensirion SCC1-USB / RS485 adapters use an FTDI USB-to-serial interface.
# On modern Raspberry Pi OS / Linux systems, the required driver (ftdi_sio)
# is loaded automatically and no manual setup is needed.
#
# If the device does not appear as /dev/ttyUSB*, check:
#   lsmod | grep ftdi
#   dmesg | grep ttyUSB
#
# Manual driver binding via modprobe/new_id is only required on older
# kernels or custom Linux images.


# Time synchronization requirement
# -------------------------------
# Ensure the system clock is synchronized (required for valid timestamps).
# On Raspberry Pi / Linux (systemd-based), enable NTP with:
#
#   sudo timedatectl set-ntp true
#
# Verify synchronization with:
#
#   timedatectl
#   timedatectl show -p NTPSynchronized
#
# A working network connection is required for initial synchronization.
# Note:
# Older systems may use the legacy 'ntp' daemon:
#   sudo apt-get install ntp
#   sudo service ntp start
# Do NOT use this together with systemd-timesyncd.


from i2c_command import ShdlcCmdGetI2cSlaveAddress, \
    ShdlcCmdI2cTransceive
from interface import ShdlcI2CInterface
from port import ShdlcSerialPort

import os 
import time 
import threading
import signal 
import argparse
import struct
import core
import queue as queue_module

BIN_RECORD_FMT = ">dhhb"
# >  big-endian
# d  float64 timestamp
# h  int16 flow
# h  int16 temp
# b  uint8 flags

# Linux: 
serial_port_ = "/dev/ttyUSB0"
baudrate_ = 115200
slave_address_ = 0x00       # Sensor Bridge default address. RS485 address is 0
queue_size_ = 1000
hours_to_log_ = 12.0        # hours
sampling_interval_ = 500    # ms

stop_logger_event = threading.Event()
stop_main_thread_event = threading.Event()
def handle_shutdown(signum, frame): 
    print("Shutdown signal received. Stopping threads...")
    stop_logger_event.set()
    stop_main_thread_event.set()

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


def dual_logger(csv_filename, bin_filename, queue, sampling_interval=sampling_interval_): 
    """
    Threaded CSV-binary logger for SHDLC sensor data.
    - Reads data from a queue and writes to CSV and binary files.
    - Integrates flow to compute volume in mL.
    """
    integrated_volume = 0.0  # in mL

    data_dir = 'Temp/'
    os.makedirs(data_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, csv_filename)
    bin_path = os.path.join(data_dir, bin_filename)
    with open(csv_path, 'w') as f_csv, open(bin_path, 'wb') as f_bin: 
        f_csv.write("UTC_Time,Flow_ul_min,Volume_mL,FlowTemperature_degC,"\
                "Flag_Air,Flag_High_Flow,Exp_Smoothing\n")
        
        while not stop_logger_event.is_set() or not queue.empty(): 
            try: 
                item = queue.get(timeout=1)
            except queue_module.Empty:
                continue
            timestamp, flow_raw, temp_raw, \
                flag_air, flag_high_flow, exp_smoothing = item
            
            flow_uL_min, temp_c = core.interpret_flow_temp_raw(flow_raw, temp_raw)
            # Integrate volume in mL
            integrated_volume += (flow_uL_min * core.UL_MIN_TO_ML_SEC) * (sampling_interval / 1000.0)

            f_csv.write(f"{timestamp},{flow_uL_min:.4f},{integrated_volume:.4f},{temp_c:.4f}"
                    f",{flag_air},{flag_high_flow},{exp_smoothing}\n")
            f_csv.flush()

            # Write binary record: 
            # flags = bit0: air_in_line, bit1: high_flow, bit2: exp_smoothing b"XXXX_XXXX"
            flags = (flag_air << 0) | (flag_high_flow << 1) | (exp_smoothing << 2)
            f_bin.write(struct.pack(BIN_RECORD_FMT, timestamp, flow_raw, temp_raw, flags))
            f_bin.flush()


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
        print("")
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
        print("")
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
        print("")
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
        num_measurements = int(seconds_to_log * 1000 // sampling_interval)
        print(f"Logging for {hours_to_log} hours, total measurements: {num_measurements}")
        measurement_count = 0
        time.sleep(1)

        try: 
            while not stop_logger_event.is_set(): 
                if measurement_count > num_measurements:
                    stop_logger_event.set()
                
                t0 = time.time()
                # reading data from sensor: 
                # data is: (flow_ul_min, temp_c, flag_air, flag_high_flow, exp_smoothing)
                data, error  = interface.i2c_execute(slave_address, transceive_cmd)    
                if error: 
                    print("Error state received during measurement read.")
                    continue
                flow_raw, temp_raw, air_flag, high_flow_flag, exp_smoothing = data
                timestamp = time.time()
                queue.put((float(timestamp), int(flow_raw), int(temp_raw), \
                        int(air_flag), int(high_flow_flag), int(exp_smoothing)))

                t1 = time.time()
                elapsed_ms = (t1 - t0) * 1000
                sleep_time_ms = sampling_interval - elapsed_ms
                if sleep_time_ms > 0: 
                    time.sleep(sleep_time_ms / 1000.0)
                measurement_count += 1

        finally: 
            # Send stop command before ending
            data, error  = interface.i2c_execute(slave_address, transceive_stop_cmd)
            print("--- Stopping continuous measurement (shutdown) ---")
            print("Data received from stop command:", data)
            print("Error state from stop command:", error)
            


def main():
    args = parse_args()

    serial_port = args.port
    baudrate = args.baudrate
    slave_address = args.slave_address
    hours_to_log = args.hours_to_log
    sampling_interval_ms = args.sampling_ms

    print(f"Logging for {hours_to_log} hours")
    print(f"Sampling interval: {sampling_interval_ms} ms")

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    queue_process = queue_module.Queue(maxsize=queue_size_)
    t_comm = threading.Thread(
        target=in_device_communication,
        args=(serial_port, baudrate, queue_process, slave_address,
            hours_to_log, sampling_interval_ms,),
        daemon=True,
    )
    t_logger = threading.Thread(
        target=dual_logger,
        args=("DataLog.csv", "DataLog.bin", 
              queue_process, sampling_interval_ms),
        daemon=True,
    )

    t_comm.start()
    t_logger.start()

    while not stop_main_thread_event.is_set(): 
        time.sleep(1)


if __name__ == "__main__":
    main()
