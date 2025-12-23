#%% Imports 
import numpy as np
import matplotlib.pyplot as plt

nominal_flow_rate = 5   # mL/hr
sensor_rated_flow_rate = 25 # uL/min
sensor_flow_rate = sensor_rated_flow_rate * (60 / 1000)  # mL/hr
print(f"Sensor Flow Rate: {sensor_flow_rate} mL/hr")

print(170/2.5)

#%% Exp1: 
total_volume = 300  # mL
avg_measured_flow = 66 # uL/min
avg_measured_flow_mLhr = avg_measured_flow * (60 / 1000)  # mL/hr
empty_time = total_volume / avg_measured_flow_mLhr  # hr
print(f"Empty Time for {total_volume} mL at {avg_measured_flow} uL/min: {empty_time:.2f} hr")