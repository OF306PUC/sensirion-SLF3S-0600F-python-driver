import time 
from command import ShdlcCommand

import logging
log = logging.getLogger(__name__)


class ShdlcGetVersionBase(ShdlcCommand): 
    """
    SHDLC command ID: 0x01 "Get Version".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcGetVersionBase, self).__init__(
            0xD1, *args, **kwargs
        )

class ShdlcGetVersion(ShdlcGetVersionBase):
    def __init__(self): 
        super(ShdlcGetVersion, self).__init__(
            data=[], max_response_time=0.1,
            min_response_length=7, max_response_length=7
        )

    def interpret_response(self, data): 
        """
        :return dict: Version information with keys:
                      'major', 'minor', 'debug_state',
                      'hardware_major', 'hardware_minor',
                      'shdlc_protocol_major', 'shdlc_protocol_minor'.
        """
        data_bytes = bytearray(data)  
        version_major = int(data_bytes[0])
        version_minor = int(data_bytes[1])
        debug_state = bool(data_bytes[2])
        hardware_major = int(data_bytes[3])
        hardware_minor = int(data_bytes[4])
        shdlc_protocol_major = int(data_bytes[5])
        shdlc_protocol_minor = int(data_bytes[6])
        info = {
            'major': version_major,
            'minor': version_minor,
            'debug_state': debug_state,
            'hardware_major': hardware_major,
            'hardware_minor': hardware_minor,
            'shdlc_protocol_major': shdlc_protocol_major,
            'shdlc_protocol_minor': shdlc_protocol_minor
        }
        return info


class ShdlcDeviceSelfTestBase(ShdlcCommand):
    """
    SHDLC command ID: 0x22 "Device Self Test".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcDeviceSelfTestBase, self).__init__(
            0x22, *args, **kwargs
        )

class ShdlcDeviceSelfTest(ShdlcDeviceSelfTestBase):
    def __init__(self): 
        super(ShdlcDeviceSelfTest, self).__init__(
            data=[], max_response_time=1.0,
            min_response_length=2, max_response_length=2
        )

    def interpret_response(self, data): 
        """
        Self test result code. uint16 [bit encoded]
        0: EEPROM error
        1: MCU supply voltage too high/low
        2: Failure on I2C line
        3: Failure on supply voltage line
        :return dict: Self test result with keys:
                      'eeprom_error', 'mcu_supply_voltage_error',
                      'i2c_line_error', 'supply_voltage_error'.
        """
        data_bytes = bytearray(data)  
        data_bytes = (data_bytes[0] << 8) | data_bytes[1]
        eeprom_error = bool(data_bytes & 0x0001)
        mcu_supply_voltage_error = bool(data_bytes & 0x0002)
        i2c_line_error = bool(data_bytes & 0x0004)
        supply_voltage_error = bool(data_bytes & 0x0008)
        result = {
            'eeprom_error': eeprom_error,
            'mcu_supply_voltage_error': mcu_supply_voltage_error,
            'i2c_line_error': i2c_line_error,
            'supply_voltage_error': supply_voltage_error
        }
        return result 
    

class ShdlcGetVoltageBase(ShdlcCommand): 
    """
    SHDLC command ID: 0x23 "Get Sensor Voltage".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcGetVoltageBase, self).__init__(
            0x23, *args, **kwargs
        )

class ShdlcGetVoltage(ShdlcGetVoltageBase):
    def __init__(self): 
        super(ShdlcGetVoltage, self).__init__(
            data=[], max_response_time=0.1,
            min_response_length=2, max_response_length=2
        )

    def interpret_response(self, data): 
        """
        Voltage Setting : uint8t[0,1]
        0: Sensor Voltage = 3.5V
        1: Sensor Voltage = 5V
        :return int: Sensor voltage in millivolts.
        """
        data_bytes = bytearray(data)  
        data_bytes = (data_bytes[0] << 8) | data_bytes[1]
        if int(data_bytes) == 0: 
            return 3.5
        else: 
            return 5.0
        

class ShdlcGetSensorTypeBase(ShdlcCommand):
    """
    SHDLC command ID: 0x24 "Get Sensor Type".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcGetSensorTypeBase, self).__init__(
            0x24, *args, **kwargs
        )

class ShdlcGetSensorType(ShdlcGetSensorTypeBase):
    def __init__(self): 
        super(ShdlcGetSensorType, self).__init__(
            data=[], max_response_time=0.1,
            min_response_length=2, max_response_length=2
        )

    def interpret_response(self, data): 
        """
        Sensor Type: u8t[0…4]
        0: Flow Sensor (SF04 based products)
        1: Humidity Sensor (SHTxx products)
        2: Flow Sensor (SF05 based products)
        3: Flow Sensor (SF06 based products) (Firmware ≥1.7)
        4: not available
        :return int: Sensor type ID.
        """
        data_bytes = bytearray(data)  
        data_bytes = (data_bytes[0] << 8) | data_bytes[1]
        sensor_type = int(data_bytes)
        if sensor_type == 0: 
            return "Flow Sensor (SF04 based products)"
        elif sensor_type == 1: 
            return "Humidity Sensor (SHTxx products)"
        elif sensor_type == 2: 
            return "Flow Sensor (SF05 based products)"
        elif sensor_type == 3: 
            return "Flow Sensor (SF06 based products)"
        else: 
            return "Not available"


class ShdlcCmdGetI2cSlaveAddressBase(ShdlcCommand): 
    """
    SHDLC command ID: 0x25 "Get Sensor Address (I2C)".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcCmdGetI2cSlaveAddressBase, self).__init__(
            0x25, *args, **kwargs
        )

class ShdlcCmdGetI2cSlaveAddress(ShdlcCmdGetI2cSlaveAddressBase):
    def __init__(self): 
        super(ShdlcCmdGetI2cSlaveAddress, self).__init__(
            data=[], max_response_time=0.1,
            min_response_length=1, max_response_length=2
        )

    def interpret_response(self, data): 
        """
        :return byte: I2C Slave Address.
        """
        data_bytes = bytearray(data)  
        i2c_addr = int(data_bytes[0])
        return i2c_addr
    

class ShdlcStartContinuousMeasurementBase(ShdlcCommand): 
    """
    SHDLC command ID: 0x33 "Start Continuous Measurement".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcStartContinuousMeasurementBase, self).__init__(
            0x33, *args, **kwargs
        )


class ShdlcStartContinuousMeasurement(ShdlcStartContinuousMeasurementBase):
    """
    SHDLC command to start continuous measurement mode on the sensor.
    """

    _MEASUREMENT_INTERVAL_100_MS = [0x00, 0x64]  # 100 ms 
    _MEASUREMENT_INTERVAL_50_MS  = [0x00, 0x32]  # 50 ms
    _MEASUREMENT_INTERVAL_20_MS  = [0x00, 0x14]  # 20 ms

    _I2C_MEAS_CMD_MEDIUM_WATER = [0x36, 0x08]    # Medium: H20 calibration
    _I2C_MEAS_CMD_MEDIUM_IPA   = [0x36, 0x15]    # Medium: Isopropyl Alcohol calibration

    def __init__(self, measurement_interval, i2c_medium_command): 
        """
        Constructor.

        :param bytes-like measurement_interval: Measurement interval in ms (2 bytes).
        :param bytes-like i2c_medium_command: I2C medium command (2 bytes).
        """
        data = bytearray()
        data.extend(measurement_interval)
        data.extend(i2c_medium_command)
        super(ShdlcStartContinuousMeasurement, self).__init__(
            data=data, max_response_time=0.1,
            min_response_length=0, max_response_length=0
        )
    
    def interpret_response(self, data): 
        """
        This command does not expect any response data.
        """
        if len(data) != 0:
            log.warning("Unexpected data received for StartContinuousMeasurement: %s", data)
        return None
    

if __name__ == "__main__":
    
    from interface import ShdlcInterface
    from port import ShdlcSerialPort

    port = "/dev/ttyUSB0"  # Example port
    baudrate = 115200
    with ShdlcSerialPort(port=port, baudrate=baudrate) as shdlc_port:
        interface = ShdlcInterface(port=shdlc_port)
        
        get_version_cmd = ShdlcGetVersion()
        version_info, error_state = interface.execute(
            slave_address=0x00,
            command=get_version_cmd
        )

        print(f"Version Info: {version_info}, Error state: {error_state}")

        selftest_cmd = ShdlcDeviceSelfTest()
        selftest_result, error_state = interface.execute(
            slave_address=0x00,
            command=selftest_cmd
        )

        print(f"Self Test Result: {selftest_result}, Error state: {error_state}")

        get_sensor_voltage_cmd = ShdlcGetVoltage()
        sensor_voltage, error_state = interface.execute(
            slave_address=0x00,
            command=get_sensor_voltage_cmd
        )

        print(f"Sensor Voltage: {sensor_voltage} V, Error state: {error_state}")

        get_sensor_type_cmd = ShdlcGetSensorType()
        sensor_type, error_state = interface.execute(
            slave_address=0x00,
            command=get_sensor_type_cmd
        )
        print(f"Sensor Type: {sensor_type}, Error state: {error_state}")

        i2c_slave_address_cmd = ShdlcCmdGetI2cSlaveAddress()
        i2c_address, error_state = interface.execute(
            slave_address=0x00,
            command=i2c_slave_address_cmd
        )
        print(f"I2C Slave Address: {i2c_address:#04x}, Error state: {error_state}")

        start_meas_cmd = ShdlcStartContinuousMeasurement(
            measurement_interval=ShdlcStartContinuousMeasurement._MEASUREMENT_INTERVAL_100_MS,
            i2c_medium_command=ShdlcStartContinuousMeasurement._I2C_MEAS_CMD_MEDIUM_WATER
        )
        _, error_state = interface.execute(
            slave_address=0x00,
            command=start_meas_cmd
        )
        print(f"Started Continuous Measurement, Error state: {error_state}")



        
