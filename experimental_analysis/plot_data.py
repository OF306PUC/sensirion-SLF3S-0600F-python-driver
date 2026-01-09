
import utils 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

FILE_PATH = "../Temp/DataLog.csv"
TIME_WINDOW_SEC = 10
TIME_WINDOW_CORR_SEC = 300

NUM_FLOW_RATE = 5           # mL/hr
INFUSION_BOMB_VOLUME = 300  # mL

slf3s_0600f_df = pd.read_csv(FILE_PATH)

# UTC_Time,Flow_ul_min,Volume_uL,DeviceTemperature_degC,Flag_Air,Flag_High_Flow,Exp_Smoothing,Flags_Value
utc_time = slf3s_0600f_df['UTC_Time'].to_numpy()
rel_time = utc_time - utc_time[0]

Ts = np.mean(np.diff(utc_time))
window_size = int(TIME_WINDOW_SEC / Ts)

flow_ul_min = slf3s_0600f_df['Flow_ul_min'].to_numpy()
flow_ul_min = np.nan_to_num(flow_ul_min, nan=0.0)
flow_ml_hr = flow_ul_min * 60.0 / 1000.0
flow_ml_hr_moving_avg = utils.moving_avg_nonzero(flow_ml_hr, window_size=window_size)

volume_uL = slf3s_0600f_df['Volume_uL'].to_numpy()
volume_mL = volume_uL / 1000.0
integrated_flow_uL = utils.integrate_flow_rate(time=rel_time, V0=0.0, 
                                                 flow_rate_ul_min=flow_ul_min)
integrated_flow_mL = integrated_flow_uL / 1000.0

device_temp_degC = slf3s_0600f_df['DeviceTemperature_degC'].to_numpy()

flag_air = slf3s_0600f_df['Flag_Air'].to_numpy()
flag_high_flow = slf3s_0600f_df['Flag_High_Flow'].to_numpy()
exp_smoothing = slf3s_0600f_df['Exp_Smoothing'].to_numpy()


# Plot flow rate
(fig, ax) = plt.figure(figsize=(12,8), dpi=300)
ax.step(utc_time, flow_ml_hr, where='post', label='Flow rate', color='blue', alpha=0.8)
ax.step(utc_time, flow_ml_hr_moving_avg, where='post', label='Flow rate - moving avg (10 sec.)', 
        color='red', alpha=0.8)
ax.axhline(y=NUM_FLOW_RATE, color='black', linestyle='--', label=f'Nominal flow rate: {NUM_FLOW_RATE} mL/hr')
ax.set_xlabel("Time (UTC)")
ax.set_ylabel("$q(t)$ (mL/hr)")
ax.grid(True)
ax.legend()

ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

fig.autofmt_xdate()
plt.show()


# Plot device temperature
(fig, ax) = plt.figure(figsize=(12,8), dpi=300)
ax.step(utc_time, device_temp_degC, where='post', label='Device temperature', color='orange', alpha=0.8)
ax.set_xlabel("Time (UTC)")
ax.set_ylabel("$T(t)$ (°C)")
ax.grid(True)
ax.legend()

ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

fig.autofmt_xdate()
plt.show()


# Plot integrated volume
(fig, ax) = plt.figure(figsize=(12,8), dpi=300)
ax.step(utc_time, volume_mL, where='post', label='Integrated (dispensed) volume', color='green', alpha=0.8)
ax.step(utc_time, integrated_flow_mL, where='post', 
        label='Integrated flow rate', color='purple', alpha=0.8)
ax.axhline(y=INFUSION_BOMB_VOLUME, color='black', linestyle='--', 
           label=f'Infusion bomb volume: {INFUSION_BOMB_VOLUME} mL')
ax.set_xlabel("Time (UTC)")
ax.set_ylabel("$V(t)$ (mL)")
ax.grid(True)
ax.legend()

ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

fig.autofmt_xdate()
plt.show()


# Compute cross-correlation between flow rate and device temperature
window_size_corr = int(TIME_WINDOW_CORR_SEC / Ts)
mask = np.isfinite(flow_ml_hr) & np.isfinite(device_temp_degC)

flow_ml_hr_valid = flow_ml_hr[mask]
device_temp_degC_valid = device_temp_degC[mask]
utc_time_valid = utc_time[mask]

flow_f = pd.Series(flow_ml_hr_valid).rolling(window_size_corr, center=True).mean()
temp_f = pd.Series(device_temp_degC_valid).rolling(window_size_corr, center=True).mean()

valid = flow_f.notna() & temp_f.notna()
flow_f = flow_f[valid]
temp_f = temp_f[valid]
utc_time_f = utc_time_valid[valid]

fig, ax = plt.subplots(figsize=(4.5, 4.0))

ax.scatter(flow_f, temp_f, s=5, alpha=0.4)
ax.set_xlabel("Flow (mL/hr)")
ax.set_ylabel("Chip temperature (°C)")
ax.grid(True)

plt.show()






