# Sensirion SHDLC Python Driver  
Robust Data Logger for SLF3S-0600F  
**Raspberry Pi – Raspbian Bookworm**

---

## Overview

This project implements a **robust, long-running data logger** for Sensirion SHDLC-based sensors (e.g. SLF3S-0600F) using:

- SHDLC over RS485 / USB (FTDI)
- Dual-threaded architecture (acquisition + logging)
- CSV + binary logging
- Persistent error logging with context
- Ring buffer for last measurements
- Graceful shutdown on SIGINT / SIGTERM

### Execution model (IMPORTANT)

- The logger is **started manually by the user via SSH**
- The logger **continues running after SSH disconnect**
- The logger **does NOT start automatically on reboot**
- No systemd service is used

This behavior is achieved using **`nohup`**, which detaches the process from the SSH session safely.

---

## 1. Connect to the Raspberry Pi

From your host machine:

```bash
ssh pi@<raspberry_pi_ip>
```

Or, if you use an SSH config alias:

```bash
ssh pi10
```

---

## 2. Verify USB device detection

Plug in the Sensirion SCC1-USB / RS485 adapter.

Check that the FTDI driver is loaded automatically:

```bash
ls /dev/ttyUSB*
```

Expected output (example):

```
/dev/ttyUSB0
```

Optional diagnostics:

```bash
lsmod | grep ftdi
dmesg | grep ttyUSB
```

> On **Raspbian Bookworm**, the `ftdi_sio` driver is loaded automatically.  
> No manual driver binding is required.

---

## 3. Ensure system time is synchronized

Correct timestamps require NTP synchronization.

Enable NTP:

```bash
sudo timedatectl set-ntp true
```

Verify:

```bash
timedatectl
timedatectl show -p NTPSynchronized
```

Expected:

```
NTPSynchronized=yes
```

---

## 4. Project structure

Example directory layout:

```
sensirion-SLF3S-0600F-python-driver/
├── shdlc_driver.py
├── core.py
├── interface.py
├── port.py
├── i2c_command.py
├── driver_logger.py
├── Temp/
│   ├── DataLog.csv
│   ├── DataLog.bin
│   └── ErrorLog.txt
└── README.md
```

---

## 5. Running the logger (robust against SSH disconnect)

### 5.1 Go to the project directory

```bash
cd ~/sensirion-SLF3S-0600F-python-driver
```

---

### 5.2 Start the logger using `nohup`

```bash
nohup python3 shdlc_driver.py   --hours-to-log 12   --sampling-ms 500   > sensirion.log 2>&1 &
```

What this does:

- `nohup` prevents the process from receiving `SIGHUP`
- `&` runs the process in the background
- Output is redirected to `sensirion.log`
- The process **continues running after SSH disconnect**

---

### 5.3 Verify the logger is running

```bash
pgrep -af shdlc_driver.py
```

Example output:

```
12345 python3 shdlc_driver.py --hours-to-log 12 --sampling-ms 500
```

---

### 5.4 Disconnect SSH safely

You can now close the SSH session:

```bash
exit
```

The logger will **continue running** on the Raspberry Pi.

---

## 6. Viewing logs and data

### 6.1 View runtime log

Reconnect via SSH and run:

```bash
tail -f sensirion.log
```

---

### 6.2 Check data output files

```bash
ls -lh Temp/
```
