import serial
import pygame
import threading
import numpy as np
import time
import math
from collections import deque

# --------- Config ---------
SERIAL_PORT = 'COM8'
BAUD_RATE = 500000
SAMPLES_TO_SHOW = 1000      # Jumlah sampel yang ditampilkan
TRIGGER_LEVEL = 2048        # Level trigger (setengah dari 4096)
TRIGGER_SLOPE = 'rising'    # 'rising' atau 'falling'
TRIGGER_CHANNEL = 0         # Channel untuk trigger (0 atau 1)

# Display settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 1000
PLOT_HEIGHT = 180
PLOT_MARGIN = 50
FPS = 60                    # Target frame rate

# Wave generator settings
WAVE_COUNT = 5              # Jumlah gelombang yang ditampilkan
AMPLITUDE = 1500            # Amplitudo gelombang
OFFSET = 2048               # Offset tengah (12-bit center)
# --------------------------

# Colors untuk setiap gelombang
COLORS = [
    (255, 100, 100),  # Red
    (100, 255, 100),  # Green  
    (100, 100, 255),  # Blue
    (255, 255, 100),  # Yellow
    (255, 100, 255),  # Magenta
]

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
RED = (255, 0, 0)

# Serial configuration (opsional, bisa dimatikan untuk demo)
USE_SERIAL = False
try:
    if USE_SERIAL:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
except:
    USE_SERIAL = False
    print("Serial tidak tersedia, menggunakan generator sinyal")

# Wave parameters yang berubah dinamis
wave_params = [
    {'freq': 1.0, 'phase': 0.0, 'freq_rate': 0.1},    # Slow changing
    {'freq': 2.0, 'phase': 0.0, 'freq_rate': 0.15},   # Medium changing
    {'freq': 3.0, 'phase': 0.0, 'freq_rate': 0.2},    # Fast changing
    {'freq': 0.5, 'phase': 0.0, 'freq_rate': 0.05},   # Very slow
    {'freq': 4.0, 'phase': 0.0, 'freq_rate': 0.25},   # Very fast changing
]

# Buffers untuk setiap gelombang
wave_buffers = [deque(maxlen=SAMPLES_TO_SHOW * 3) for _ in range(WAVE_COUNT)]
display_buffers = [[OFFSET] * SAMPLES_TO_SHOW for _ in range(WAVE_COUNT)]
lock = threading.Lock()

# Performance monitoring
frame_count = 0
last_fps_time = time.time()
current_fps = 0
time_counter = 0.0

def generate_dynamic_waves():
    """Generate waves dengan periode yang dinamis berubah"""
    global time_counter, wave_params
    
    time_counter += 0.01  # Time step
    
    # Update frekuensi setiap gelombang secara dinamis
    for i, params in enumerate(wave_params):
        # Frekuensi berubah secara sinusoidal
        base_freq = [1.0, 2.0, 3.0, 0.5, 4.0][i]
        freq_variation = math.sin(time_counter * params['freq_rate']) * 0.5
        params['freq'] = base_freq + freq_variation
        
        # Generate sample baru
        sample_value = OFFSET + AMPLITUDE * math.sin(2 * math.pi * params['freq'] * time_counter + params['phase'])
        sample_value = max(0, min(4095, int(sample_value)))  # Clamp to 12-bit range
        
        with lock:
            wave_buffers[i].append(sample_value)

def wave_generator_thread():
    """Thread untuk generate gelombang secara kontinu"""
    while True:
        generate_dynamic_waves()
        time.sleep(0.001)  # 1kHz sample rate

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

def update_display_buffers():
    """Update display buffers dengan trigger pada gelombang yang dipilih"""
    global display_buffers
    
    with lock:
        # Gunakan gelombang pertama sebagai trigger reference
        trigger_buffer = wave_buffers[TRIGGER_CHANNEL]
        
        if len(trigger_buffer) >= SAMPLES_TO_SHOW:
            trigger_data = list(trigger_buffer)
            trigger_point = find_trigger_point(trigger_data, TRIGGER_LEVEL, TRIGGER_SLOPE)
            
            if trigger_point is not None:
                # Apply trigger point ke semua gelombang
                for i in range(WAVE_COUNT):
                    if len(wave_buffers[i]) >= SAMPLES_TO_SHOW:
                        triggered_data = list(wave_buffers[i])[trigger_point:trigger_point + SAMPLES_TO_SHOW]
                        if len(triggered_data) == SAMPLES_TO_SHOW:
                            display_buffers[i] = triggered_data

def draw_plot(surface, data, y_offset, color, title, frequency):
    """Draw a single plot dengan informasi frekuensi"""
    plot_width = WINDOW_WIDTH - 2 * PLOT_MARGIN
    plot_rect = pygame.Rect(PLOT_MARGIN, y_offset, plot_width, PLOT_HEIGHT)
    
    # Draw background
    pygame.draw.rect(surface, DARK_GRAY, plot_rect)
    pygame.draw.rect(surface, WHITE, plot_rect, 1)
    
    # Draw grid
    for i in range(0, plot_width, plot_width // 10):
        pygame.draw.line(surface, GRAY, 
                        (PLOT_MARGIN + i, y_offset), 
                        (PLOT_MARGIN + i, y_offset + PLOT_HEIGHT), 1)
    
    for i in range(0, PLOT_HEIGHT, PLOT_HEIGHT // 4):
        pygame.draw.line(surface, GRAY, 
                        (PLOT_MARGIN, y_offset + i), 
                        (PLOT_MARGIN + plot_width, y_offset + i), 1)
    
    # Draw trigger level (hanya pada channel trigger)
    if title.endswith("(TRIGGER)"):
        trigger_y = y_offset + PLOT_HEIGHT - int((TRIGGER_LEVEL / 4096.0) * PLOT_HEIGHT)
        pygame.draw.line(surface, RED, 
                        (PLOT_MARGIN, trigger_y), 
                        (PLOT_MARGIN + plot_width, trigger_y), 2)
    
    # Draw signal
    if len(data) > 1:
        points = []
        for i, value in enumerate(data):
            x = PLOT_MARGIN + int((i / len(data)) * plot_width)
            y = y_offset + PLOT_HEIGHT - int((value / 4096.0) * PLOT_HEIGHT)
            y = max(y_offset, min(y_offset + PLOT_HEIGHT, y))  # Clamp to plot area
            points.append((x, y))
        
        if len(points) > 1:
            pygame.draw.lines(surface, color, False, points, 2)
    
    # Draw title dengan frekuensi
    font = pygame.font.Font(None, 20)
    title_text = f"{title} - Freq: {frequency:.2f} Hz"
    text = font.render(title_text, True, WHITE)
    surface.blit(text, (PLOT_MARGIN, y_offset - 22))

def draw_info(surface):
    """Draw information panel"""
    font = pygame.font.Font(None, 18)
    info_texts = [
        f"FPS: {current_fps:.1f}",
        f"Trigger Level: {TRIGGER_LEVEL}",
        f"Trigger Channel: {TRIGGER_CHANNEL}",
        f"Trigger Slope: {TRIGGER_SLOPE}",
        f"Time: {time_counter:.1f}s",
        "",
        "Controls:",
        "0-4: Switch trigger channel",
        "R: Reset time counter", 
        "ESC: Exit"
    ]
    
    for i, text in enumerate(info_texts):
        if text == "":
            continue
        color = WHITE if i < 5 else (100, 255, 100)
        rendered = font.render(text, True, color)
        surface.blit(rendered, (10, 10 + i * 20))

def main():
    global frame_count, last_fps_time, current_fps, TRIGGER_CHANNEL, time_counter
    
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Dynamic Multi-Wave Plotter - 5 Gelombang Dinamis")
    clock = pygame.time.Clock()
    
    # Start wave generator thread
    wave_thread = threading.Thread(target=wave_generator_thread, daemon=True)
    wave_thread.start()
    
    print("Dynamic Multi-Wave Plotter Started")
    print("Menampilkan 5 gelombang dengan periode yang berubah dinamis")
    print("Controls:")
    print("  0-4: Switch trigger channel")
    print("  R: Reset time counter")
    print("  ESC: Exit")
    
    running = True
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    time_counter = 0.0
                    print("Time counter reset")
                elif event.key >= pygame.K_0 and event.key <= pygame.K_4:
                    TRIGGER_CHANNEL = event.key - pygame.K_0
                    if TRIGGER_CHANNEL < WAVE_COUNT:
                        print(f"Trigger channel switched to: {TRIGGER_CHANNEL}")
        
        # Update data
        update_display_buffers()
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw all wave plots
        for i in range(WAVE_COUNT):
            y_pos = 50 + i * (PLOT_HEIGHT + 10)
            title = f"Wave {i+1}"
            if i == TRIGGER_CHANNEL:
                title += " (TRIGGER)"
            
            current_freq = wave_params[i]['freq']
            draw_plot(screen, display_buffers[i], y_pos, COLORS[i], title, current_freq)
        
        # Draw info
        draw_info(screen)
        
        # Update display
        pygame.display.flip()
        
        # Calculate FPS
        frame_count += 1
        current_time = time.time()
        if current_time - last_fps_time >= 1.0:
            current_fps = frame_count / (current_time - last_fps_time)
            frame_count = 0
            last_fps_time = current_time
        
        # Control frame rate
        clock.tick(FPS)
    
    # Cleanup
    pygame.quit()
    if USE_SERIAL:
        ser.close()
    print("Dynamic Multi-Wave Plotter stopped")

if __name__ == "__main__":
    main()