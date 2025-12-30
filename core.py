"""
core.py library module.

Provides core functionality for SHDLC data interpretation.
- Flow rate: 16-bit signed integer number. (two's complement range: -32768 to 32767). 
    Sensor output internally saturates in +-3250 uLmin range so it will output within that range (scaled by 10 (ul/min)^{-1}).
- Temperature: 16-bit signed integer number. (two's complement range: -32768 to 32767).
"""

SCALE_FLOW = 10.0
SCALE_TEMPERATURE = 200.0

UL_MIN_TO_ML_HR = (60.0 / 1000.0)
UL_MIN_TO_ML_SEC = (1.0 / 1000.0 / 60.0)

def u16_to_i16(x): 
    """
    Convert unsigned 16-bit integer to signed 16-bit integer.
    signed = x - 2**16 if masked(x)
    
    :param x:
    """
    return x - 0x10000 if x & 0x8000 else x

def interpret_flow_temp_raw(flow_raw, temp_raw):
    """
    interpret raw data bytes from SHDLC device and return flow and temperature values.

    raw response for the SLF3S-0600F sensor is 18-bit long: 
    raw_data = (flow[15:0], temp[15:0], signaling flags 8msb, signaling flags 8lsb) 
    
    :param raw_data: raw data bytes from SHDLC device
    :return: flow in uL/min (or) mL/hr. and temperature in degC.
    """ 
    raw_flow = u16_to_i16(flow_raw)
    raw_temp = u16_to_i16(temp_raw)

    flow_ul_min = float(raw_flow) / SCALE_FLOW
    temperature_degC = float(raw_temp) / SCALE_TEMPERATURE

    return flow_ul_min, temperature_degC




