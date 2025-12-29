"""
core.py library module.

Provides core functionality for SHDLC data interpretation.
- Flow rate: 16-bit signed integer number. (two's complement range: -32768 to 32767). 
    Sensor output internally saturates in +-3250 uLmin range so it will output within that range (scaled by 10 (ul/min)^{-1}).
- Temperature: 16-bit signed integer number. (two's complement range: -32768 to 32767).
"""

_SCALE_FLOW = 10.0
_SCALE_TEMPERATURE = 200.0

_UL_MIN_TO_ML_HR = (60.0 / 1000.0)

def u16_to_i16(x): 
    """
    Convert unsigned 16-bit integer to signed 16-bit integer.
    signed = x - 2**16 if masked(x)
    
    :param x:
    """
    return x - 0x10000 if x & 0x8000 else x

def interpret_flow_temp_raw(raw_data):
    """
    interpret raw data bytes from SHDLC device and return flow and temperature values.

    raw response for the SLF3S-0600F sensor is 18-bit long: 
    raw_data = (flow[15:0], temp[15:0], signaling flags 8msb, signaling flags 8lsb) 
    
    :param raw_data: raw data bytes from SHDLC device
    :return: flow in uL/min (or) mL/hr. and temperature in degC.
    """ 
    raw_flow = u16_to_i16(raw_data[0])
    raw_temp = u16_to_i16(raw_data[1])

    flow_ul_min = float(raw_flow) / _SCALE_FLOW
    flow_ml_hr = flow_ul_min * _UL_MIN_TO_ML_HR
    temperature_degC = float(raw_temp) / _SCALE_TEMPERATURE

    air_in_line_flag = int(raw_data[2])
    high_flow_flag = int(raw_data[3])
    exp_smoothing = int(raw_data[4])

    return flow_ul_min, flow_ml_hr, temperature_degC, air_in_line_flag, high_flow_flag, exp_smoothing


