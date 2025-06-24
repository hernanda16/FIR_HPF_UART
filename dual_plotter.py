import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import threading
import numpy as np
import time

# --------- Config ---------
SERIAL_PORT = 'COM3'
BAUD_RATE = 2000000
SAMPLES_TO_SHOW = 250       # Jumlah sampel yang ditampilkan
UPDATE_INTERVAL = 50        # ms - interval update plot
TRIGGER_LEVEL = 2048        # Level trigger (setengah dari 4096)
TRIGGER_SLOPE = 'rising'    # 'rising' atau 'falling'
OVERLAY_MODE = True        # True: Overlay kedua channel, False: Separate plots
# --------------------------

# Serial configuration
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

# Buffer untuk menyimpan data mentah - dual channel
raw_buffer_ch0 = deque(maxlen=SAMPLES_TO_SHOW * 3)  # Channel 0: RAW signal
raw_buffer_ch1 = deque(maxlen=SAMPLES_TO_SHOW * 3)  # Channel 1: Processed signal
display_buffer_ch0 = [0] * SAMPLES_TO_SHOW  # Buffer untuk ditampilkan (statis)
display_buffer_ch1 = [0] * SAMPLES_TO_SHOW
lock = threading.Lock()

# Frame parsing state
frame_state = 'WAIT_START'
frame_data = []
expected_bytes = 0

def find_trigger_point(data, level, slope='rising'):
    """Mencari titik trigger dalam data"""
    if len(data) < 2:
        return None
    
    for i in range(1, len(data) - SAMPLES_TO_SHOW):
        if slope == 'rising':
            if data[i-1] < level and data[i] >= level:
                return i
        else:  # falling
            if data[i-1] > level and data[i] <= level:
                return i
    return None

def parse_frame_data(frame_bytes):
    """Parse frame sesuai format FRAMING.vhd"""
    if len(frame_bytes) != 6:
        return None, None
    
    # Check start and end markers
    if frame_bytes[0] != 0x53 or frame_bytes[5] != 0x45:  # 'S' and 'E'
        return None, None
    
    # Reconstruct DATA0 (12-bit) - RAW SIGNAL
    data0_high = frame_bytes[1]
    data0_low = frame_bytes[2] >> 4
    data0 = (data0_high << 4) | data0_low
    
    # Reconstruct DATA1 (12-bit) - PROCESSED SIGNAL
    data1_high = frame_bytes[3]
    data1_low = frame_bytes[4] >> 4
    data1 = (data1_high << 4) | data1_low
    
    return data0, data1

def uart_reader():
    """Thread untuk membaca data UART dengan frame parsing"""
    global frame_state, frame_data, expected_bytes
    
    while True:
        try:
            if ser.in_waiting > 0:
                byte_val = ser.read(1)[0]
                
                if frame_state == 'WAIT_START':
                    if byte_val == 0x53:  # 'S' start marker
                        frame_data = [byte_val]
                        frame_state = 'COLLECTING'
                        expected_bytes = 5
                
                elif frame_state == 'COLLECTING':
                    frame_data.append(byte_val)
                    expected_bytes -= 1
                    
                    if expected_bytes == 0:
                        data0, data1 = parse_frame_data(frame_data)
                        
                        if data0 is not None and data1 is not None:
                            with lock:
                                raw_buffer_ch0.append(data0)    # RAW signal
                                raw_buffer_ch1.append(data1)    # Processed signal
                        
                        frame_state = 'WAIT_START'
                        frame_data = []
            else:
                time.sleep(0.001)
                
        except Exception as e:
            print(f"UART error: {e}")
            frame_state = 'WAIT_START'
            frame_data = []
            time.sleep(0.01)

# Start thread untuk baca data
threading.Thread(target=uart_reader, daemon=True).start()

# Setup matplotlib
if OVERLAY_MODE:
    # Single plot with both channels overlayed
    fig, ax = plt.subplots(figsize=(14, 8))
    
    line0, = ax.plot([], [], 'b-', linewidth=2, label='Channel 0 (RAW)', alpha=0.8)
    line1, = ax.plot([], [], 'r-', linewidth=2, label='Channel 1 (Processed)', alpha=0.8)
    trigger_line = ax.axhline(y=TRIGGER_LEVEL, color='g', linestyle='--', alpha=0.7, 
                             label=f'Trigger Level: {TRIGGER_LEVEL}')
    
    ax.set_xlim(0, SAMPLES_TO_SHOW)
    ax.set_ylim(0, 4096)
    ax.set_title("Dual Channel Comparison - RAW vs Processed Signal")
    ax.set_xlabel("Sampel (Posisi Statis)")
    ax.set_ylabel("Nilai ADC")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
else:
    # Separate plots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Channel 0 plot
    line0, = ax1.plot([], [], 'b-', linewidth=1.5, label='Channel 0 (RAW)')
    trigger_line0 = ax1.axhline(y=TRIGGER_LEVEL, color='r', linestyle='--', alpha=0.7)
    
    # Channel 1 plot  
    line1, = ax2.plot([], [], 'r-', linewidth=1.5, label='Channel 1 (Processed)')
    trigger_line1 = ax2.axhline(y=TRIGGER_LEVEL, color='r', linestyle='--', alpha=0.7)
    
    # Setup axes
    for axis in [ax1, ax2]:
        axis.set_xlim(0, SAMPLES_TO_SHOW)
        axis.set_ylim(0, 4096)
        axis.grid(True, alpha=0.3)
        axis.legend()
    
    ax1.set_title("Channel 0 - RAW Signal")
    ax1.set_ylabel("Nilai ADC")
    ax2.set_title("Channel 1 - Processed Signal")
    ax2.set_xlabel("Sampel (Posisi Statis)")
    ax2.set_ylabel("Nilai ADC")

# Setup x-axis data
x_data = np.arange(SAMPLES_TO_SHOW)

def update(frame):
    """Update plot - kedua channel sinkron karena data dikirim bersamaan"""
    global display_buffer_ch0, display_buffer_ch1
    
    with lock:
        # Karena data dikirim bersamaan, cukup cek buffer length dan ambil data terbaru
        if len(raw_buffer_ch0) >= SAMPLES_TO_SHOW and len(raw_buffer_ch1) >= SAMPLES_TO_SHOW:
            # Gunakan channel 0 untuk trigger (reference)
            trigger_data = list(raw_buffer_ch0)
            trigger_point = find_trigger_point(trigger_data, TRIGGER_LEVEL, TRIGGER_SLOPE)
            
            if trigger_point is not None:
                # Ambil data dari titik trigger yang sama untuk kedua channel
                triggered_data_ch0 = trigger_data[trigger_point:trigger_point + SAMPLES_TO_SHOW]
                triggered_data_ch1 = list(raw_buffer_ch1)[trigger_point:trigger_point + SAMPLES_TO_SHOW]
                
                if len(triggered_data_ch0) == SAMPLES_TO_SHOW and len(triggered_data_ch1) == SAMPLES_TO_SHOW:
                    display_buffer_ch0 = triggered_data_ch0
                    display_buffer_ch1 = triggered_data_ch1
    
    # Update lines
    line0.set_data(x_data, display_buffer_ch0)
    line1.set_data(x_data, display_buffer_ch1)
    
    if OVERLAY_MODE:
        return line0, line1
    else:
        return line0, line1

# Animasi
ani = animation.FuncAnimation(
    fig, 
    update, 
    interval=UPDATE_INTERVAL,
    blit=True
)

plt.tight_layout()

print("=== Synchronous Dual Channel Analysis ===")
print(f"Trigger Level: {TRIGGER_LEVEL}")
print(f"Trigger Slope: {TRIGGER_SLOPE}")
print(f"Display Mode: {'Overlay' if OVERLAY_MODE else 'Separate'}")
print("")
print("Channel Configuration:")
print("  Channel 0 (Blue): RAW Signal dari ADC")
print("  Channel 1 (Red): Processed Signal dari FPGA")
print("")
print("Catatan:")
print("  - Data dikirim secara sinkron dalam frame yang sama")
print("  - Trigger berdasarkan Channel 0 (RAW)")
print("  - Kedua channel akan tampil pada posisi trigger yang sama")
if OVERLAY_MODE:
    print("  - Mode Overlay: Mudah membandingkan perbedaan amplitude dan fase")

try:
    plt.show()
except KeyboardInterrupt:
    print("Stopping...")
finally:
    ser.close()
    print("Serial port closed.")