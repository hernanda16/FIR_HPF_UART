import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import threading
import numpy as np
import time

# --------- Config ---------
SERIAL_PORT = 'COM8'
BAUD_RATE = 500000
SAMPLES_TO_SHOW = 1000      # Jumlah sampel yang ditampilkan
UPDATE_INTERVAL = 50        # ms - interval update plot
TRIGGER_LEVEL = 2048        # Level trigger (setengah dari 4096)
TRIGGER_SLOPE = 'rising'    # 'rising' atau 'falling'
TRIGGER_CHANNEL = 0         # Channel untuk trigger (0 atau 1)
# --------------------------

# Serial configuration
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

# Buffer untuk menyimpan data mentah - dual channel
raw_buffer_ch0 = deque(maxlen=SAMPLES_TO_SHOW * 3)  # Buffer lebih besar untuk mencari trigger
raw_buffer_ch1 = deque(maxlen=SAMPLES_TO_SHOW * 3)
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
    
    # Reconstruct DATA0 (12-bit)
    data0_high = frame_bytes[1]  # bits 11-4
    data0_low = frame_bytes[2] >> 4  # bits 3-0 (shifted back)
    data0 = (data0_high << 4) | data0_low
    
    # Reconstruct DATA1 (12-bit)
    data1_high = frame_bytes[3]  # bits 11-4
    data1_low = frame_bytes[4] >> 4  # bits 3-0 (shifted back)
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
                        expected_bytes = 5  # Need 5 more bytes
                
                elif frame_state == 'COLLECTING':
                    frame_data.append(byte_val)
                    expected_bytes -= 1
                    
                    if expected_bytes == 0:
                        # Frame complete, parse it
                        data0, data1 = parse_frame_data(frame_data)
                        
                        if data0 is not None and data1 is not None:
                            # Add to buffers
                            with lock:
                                raw_buffer_ch0.append(data0)
                                raw_buffer_ch1.append(data1)
                        
                        # Reset for next frame
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

# Setup matplotlib untuk dual channel
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

# Channel 0 plot
line0, = ax1.plot([], [], 'b-', linewidth=1.5, label='Channel 0')
trigger_line0 = ax1.axhline(y=TRIGGER_LEVEL, color='r', linestyle='--', alpha=0.7, 
                           label=f'Trigger Level: {TRIGGER_LEVEL}')

# Channel 1 plot
line1, = ax2.plot([], [], 'g-', linewidth=1.5, label='Channel 1')
trigger_line1 = ax2.axhline(y=TRIGGER_LEVEL, color='r', linestyle='--', alpha=0.7, 
                           label=f'Trigger Level: {TRIGGER_LEVEL}')

# Setup sumbu - BENAR-BENAR STATIS
x_data = np.arange(SAMPLES_TO_SHOW)

# Channel 0 axis setup
ax1.set_xlim(0, SAMPLES_TO_SHOW)
ax1.set_ylim(0, 4096)
ax1.set_title(f"Channel 0 - ADC Plot (Trigger: {'ON' if TRIGGER_CHANNEL == 0 else 'OFF'})")
ax1.set_ylabel("Nilai ADC")
ax1.grid(True, alpha=0.3)
ax1.legend()

# Channel 1 axis setup
ax2.set_xlim(0, SAMPLES_TO_SHOW)
ax2.set_ylim(0, 4096)
ax2.set_title(f"Channel 1 - ADC Plot (Trigger: {'ON' if TRIGGER_CHANNEL == 1 else 'OFF'})")
ax2.set_xlabel("Sampel (Posisi Statis)")
ax2.set_ylabel("Nilai ADC")
ax2.grid(True, alpha=0.3)
ax2.legend()

def update(frame):
    """Update plot dengan trigger - tampilan STATIS untuk dual channel"""
    global display_buffer_ch0, display_buffer_ch1
    
    with lock:
        # Pilih channel untuk trigger
        if TRIGGER_CHANNEL == 0:
            trigger_buffer = raw_buffer_ch0
            other_buffer = raw_buffer_ch1
        else:
            trigger_buffer = raw_buffer_ch1
            other_buffer = raw_buffer_ch0
        
        if len(trigger_buffer) >= SAMPLES_TO_SHOW and len(other_buffer) >= SAMPLES_TO_SHOW:
            # Convert deque ke list untuk pencarian trigger
            trigger_data = list(trigger_buffer)
            other_data = list(other_buffer)
            
            # Cari titik trigger pada channel yang dipilih
            trigger_point = find_trigger_point(trigger_data, TRIGGER_LEVEL, TRIGGER_SLOPE)
            
            if trigger_point is not None:
                # Ambil data mulai dari titik trigger untuk kedua channel
                triggered_data_ch0 = list(raw_buffer_ch0)[trigger_point:trigger_point + SAMPLES_TO_SHOW]
                triggered_data_ch1 = list(raw_buffer_ch1)[trigger_point:trigger_point + SAMPLES_TO_SHOW]
                
                if len(triggered_data_ch0) == SAMPLES_TO_SHOW and len(triggered_data_ch1) == SAMPLES_TO_SHOW:
                    display_buffer_ch0 = triggered_data_ch0
                    display_buffer_ch1 = triggered_data_ch1
    
    # Update kedua line dengan data yang sudah di-trigger (POSISI STATIS)
    line0.set_data(x_data, display_buffer_ch0)
    line1.set_data(x_data, display_buffer_ch1)
    
    return line0, line1

# Animasi
ani = animation.FuncAnimation(
    fig, 
    update, 
    interval=UPDATE_INTERVAL,
    blit=True
)

plt.tight_layout()

print(f"Trigger Level: {TRIGGER_LEVEL}")
print(f"Trigger Slope: {TRIGGER_SLOPE}")
print(f"Trigger Channel: {TRIGGER_CHANNEL}")
print("Format: FRAMING.vhd (S + DATA0_H + DATA0_L + DATA1_H + DATA1_L + E)")
print("Grafik akan statis pada posisi trigger yang sama")

try:
    plt.show()
except KeyboardInterrupt:
    print("Stopping...")
finally:
    ser.close()
    print("Serial port closed.")