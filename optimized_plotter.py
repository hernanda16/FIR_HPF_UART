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
# --------------------------

# Serial configuration
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

# Buffer untuk menyimpan data mentah
raw_buffer = deque(maxlen=SAMPLES_TO_SHOW * 3)  # Buffer lebih besar untuk mencari trigger
display_buffer = [0] * SAMPLES_TO_SHOW  # Buffer untuk ditampilkan (statis)
lock = threading.Lock()

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

def uart_reader():
    """Thread untuk membaca data UART"""
    expecting_high = True
    high_byte = 0
    
    while True:
        try:
            if ser.in_waiting > 0:
                byte_val = ser.read(1)[0]
                
                if expecting_high:
                    high_byte = byte_val
                    expecting_high = False
                else:
                    # Rekonstruksi nilai 12-bit
                    value = (high_byte << 4) | (byte_val >> 4)
                    expecting_high = True
                    
                    # Tambahkan ke buffer mentah
                    with lock:
                        raw_buffer.append(value)
            else:
                time.sleep(0.001)
                
        except Exception as e:
            print(f"UART error: {e}")
            time.sleep(0.01)

# Start thread untuk baca data
threading.Thread(target=uart_reader, daemon=True).start()

# Setup matplotlib
fig, ax = plt.subplots(figsize=(12, 6))
line, = ax.plot([], [], 'b-', linewidth=1.5)
trigger_line = ax.axhline(y=TRIGGER_LEVEL, color='r', linestyle='--', alpha=0.7, label=f'Trigger Level: {TRIGGER_LEVEL}')

# Setup sumbu - BENAR-BENAR STATIS
x_data = np.arange(SAMPLES_TO_SHOW)
ax.set_xlim(0, SAMPLES_TO_SHOW)
ax.set_ylim(0, 4096)
ax.set_title("ADC Plot - Static Display dengan Trigger")
ax.set_xlabel("Sampel (Posisi Statis)")
ax.set_ylabel("Nilai ADC")
ax.grid(True, alpha=0.3)
ax.legend()

def update(frame):
    """Update plot dengan trigger - tampilan STATIS"""
    global display_buffer
    
    with lock:
        if len(raw_buffer) >= SAMPLES_TO_SHOW:
            # Convert deque ke list untuk pencarian trigger
            data_list = list(raw_buffer)
            
            # Cari titik trigger
            trigger_point = find_trigger_point(data_list, TRIGGER_LEVEL, TRIGGER_SLOPE)
            
            if trigger_point is not None:
                # Ambil data mulai dari titik trigger
                triggered_data = data_list[trigger_point:trigger_point + SAMPLES_TO_SHOW]
                
                if len(triggered_data) == SAMPLES_TO_SHOW:
                    display_buffer = triggered_data
    
    # Update line dengan data yang sudah di-trigger (POSISI STATIS)
    line.set_data(x_data, display_buffer)
    
    return line,

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
print("Grafik akan statis pada posisi trigger yang sama")

try:
    plt.show()
except KeyboardInterrupt:
    print("Stopping...")
finally:
    ser.close()
    print("Serial port closed.")