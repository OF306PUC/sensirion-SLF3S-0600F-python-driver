import time 
from command import ShdlcCommand

import logging
log = logging.getLogger(__name__)

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
        :return byte: Self test result code. uint16 [bit encoded]
        0: EEPROM error
        1: MCU supply voltage too high/low
        2: Failure on I2C line
        3: Failure on supply voltage 
        """
        data_bytes = bytearray(data)  
        data_bytes = (data_bytes[0] << 8) | data_bytes[1]
        return data_bytes

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


class ShdlcStartContinuousMeasurementBase(ShdlcCommand): 
    """
    SHDLC command ID: 0x33 "Start Continuous Measurement".
    """

    def __init__(self, *args, **kwargs): 
        super(ShdlcStartContinuousMeasurementBase, self).__init__(
            0x33, *args, **kwargs
        )


class ShdlcStartContinuousMeasurement(ShdlcStartContinuousMeasurementBase):

    _I2C_TIMEOUT = [0x00, 0x64] 

    def __init__(self): 
        super(ShdlcStartContinuousMeasurement, self).__init__(
            data=[], max_response_time=0.1,
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

        print(f"Self Test Result: 0x{selftest_result:04X}, Error state: {error_state}")

        
