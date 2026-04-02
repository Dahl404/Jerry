#!/usr/bin/env python3
"""Splash screen with edge-diffusion, radial build, shimmer, and smooth evaporation."""

import curses
import time
import random
import math
import os
import subprocess
import json


def hide_termux_keyboard():
    try:
        subprocess.run(['termux-hide-keyboard'], capture_output=True, timeout=2)
    except:
        pass


def show_termux_keyboard():
    try:
        subprocess.run(['termux-show-keyboard'], capture_output=True, timeout=2)
    except:
        pass


class Particle:
    def __init__(self, src_row, src_col, char, color_pair=0):
        self.src_row = float(src_row)
        self.src_col = float(src_col)
        self.char = char
        self.color_pair = color_pair
        self.x = 0.0
        self.y = 0.0
        self.base_x = 0.0
        self.base_y = 0.0
        self.start_x = 0.0
        self.start_y = 0.0
        self.alpha = 0.0

        # Phases for organic movement and shimmering
        self.phase = random.uniform(0, math.pi * 2)
        self.shimmer_phase = random.uniform(0, math.pi * 2)
        self.speed = random.uniform(0.8, 1.5)
        self.diffusion_r = random.uniform(0.7, 1.3)

        # Calculated later based on distance from center
        self.arrival_delay = 0.0


def create_particles(lines, color_grid=None):
    particles = []
    for row_idx, line in enumerate(lines):
        for col_idx, char in enumerate(line):
            if char not in (' ', '\n', '\t'):
                color_pair = color_grid[row_idx][col_idx] if color_grid else 0
                for _ in range(2):  # Double particles for a denser effect
                    off_r = random.uniform(-0.15, 0.15)
                    off_c = random.uniform(-0.15, 0.15)
                    p = Particle(row_idx + off_r, col_idx + off_c, char, color_pair)
                    particles.append(p)
    return particles


# --- Easing Functions ---

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

def ease_in_quint(t):
    return pow(t, 5)

def ease_in_out_sine(t):
    return -(math.cos(math.pi * t) - 1) / 2

def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)


# --- Visual Mapping ---

def get_build_char(alpha, original):
    """Gradual character density for building/fading."""
    if alpha < 0.10: return None
    if alpha < 0.25: return '.'
    if alpha < 0.45: return ':'
    if alpha < 0.65: return '-'
    if alpha < 0.85: return '+'
    return original


def get_shimmer_char(original):
    """Returns a lighter 'sparkle' character for the shimmer effect."""
    if original in ('.', ':', '-', '+'):
        return original
    sparkles = ['*', '+', ':', '.']
    return random.choice(sparkles)


def render(stdscr, particles, height, width, current_time, is_shimmering=False, fading_out=False, skip_erase=False):
    """Renders the particle array to the screen.
    
    Uses erase() + draw + refresh pattern which prevents tearing because
    curses only updates the physical screen on refresh().

    Args:
        stdscr: Curses screen
        particles: Particle array
        height: Screen height
        width: Screen width
        current_time: Current animation time
        is_shimmering: Whether to apply shimmer effect
        fading_out: Whether particles are fading out
        skip_erase: If True, don't clear screen (for overlay rendering)
    """
    if not skip_erase:
        stdscr.erase()

    for p in particles:
        # Continuous diffusion - always active, smooth and subtle
        wx = math.sin(current_time * p.speed + p.phase) * p.diffusion_r * 0.5
        wy = math.cos(current_time * p.speed * 0.7 + p.phase) * p.diffusion_r * 0.3

        px = int(round(p.x + wx))
        py = int(round(p.y + wy))

        if 0 <= py < height and 0 <= px < width - 1:
            ch = None
            attr = curses.A_NORMAL

            if fading_out:
                ch = get_build_char(p.alpha, p.char)
                attr = curses.A_DIM
            elif p.alpha < 1.0:
                ch = get_build_char(p.alpha, p.char)
                attr = curses.A_DIM
            else:
                # Fully assembled - apply shimmer if active
                if is_shimmering:
                    shimmer_val = math.sin(current_time * 4.0 + p.shimmer_phase)

                    if shimmer_val > 0.92:
                        ch = get_shimmer_char(p.char)
                        attr = curses.A_BOLD
                    elif shimmer_val > 0.85:
                        ch = p.char
                        attr = curses.A_BOLD
                    elif shimmer_val < -0.90:
                        ch = p.char
                        attr = curses.A_DIM
                    else:
                        ch = p.char
                        attr = curses.A_NORMAL
                else:
                    ch = p.char
                    attr = curses.A_NORMAL

            if ch:
                if p.color_pair > 0:
                    attr = attr | curses.color_pair(p.color_pair)
                try:
                    stdscr.addch(py, px, ch, attr)
                except curses.error:
                    pass

    stdscr.refresh()


# --- Animations ---

def animate_assembly(stdscr, particles, height, width, scale, splash_w):
    fps = 24
    duration = 4.5

    actual_w = splash_w * scale
    offset_x = (width - actual_w) / 2

    # Calculate bounding center for radial build
    center_x = offset_x + (actual_w / 2)
    max_y = max((p.src_row * scale for p in particles)) if particles else height
    center_y = max_y / 2

    # Initialize positions and radial delays
    max_dist = 0
    for p in particles:
        p.base_x = offset_x + p.src_col * scale
        p.base_y = p.src_row * scale

        # Calculate distance from center for radial arrival mapping
        dist = math.hypot(p.base_x - center_x, p.base_y - center_y)
        if dist > max_dist:
            max_dist = dist

        # Spawn at a random edge just outside the screen
        edge = random.randint(0, 3)
        if edge == 0:   # Top
            p.start_x = random.uniform(0, width)
            p.start_y = -random.uniform(10, 30)
        elif edge == 1: # Right
            p.start_x = width + random.uniform(10, 30)
            p.start_y = random.uniform(0, height)
        elif edge == 2: # Bottom
            p.start_x = random.uniform(0, width)
            p.start_y = height + random.uniform(10, 30)
        else:           # Left
            p.start_x = -random.uniform(10, 30)
            p.start_y = random.uniform(0, height)

        p.x = p.start_x
        p.y = p.start_y
        p.alpha = 0.0

    # Normalize radial delays so center particles have delay ~0, edges ~0.6
    for p in particles:
        if max_dist > 0:
            # The further from the center, the longer the delay
            p.arrival_delay = (math.hypot(p.base_x - center_x, p.base_y - center_y) / max_dist) * 0.6
        else:
            p.arrival_delay = 0

    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break


        t = elapsed / duration

        for p in particles:
            # Map time based on radial delay
            arr_t = max(0.0, min(1.0, (t - p.arrival_delay) / (1.0 - p.arrival_delay)))
            arr_ease = ease_out_cubic(arr_t)

            # Drift inward
            p.x = p.start_x + (p.base_x - p.start_x) * arr_ease
            p.y = p.start_y + (p.base_y - p.start_y) * arr_ease

            p.alpha = arr_ease

        render(stdscr, particles, height, width, elapsed, is_shimmering=False)
        time.sleep(1/fps)

    # Settle at targets - no snap, just ensure alpha is full
    for p in particles:
        p.alpha = 1.0

    # Hold full image with shimmer before scrolling
    hold_start = time.time()
    while time.time() - hold_start < 1.0:
        render(stdscr, particles, height, width, time.time(), is_shimmering=True)
        time.sleep(1/fps)


def animate_scroll(stdscr, particles, height, width, splash_h, scale):
    fps = 24
    total_img_h = splash_h * scale
    max_scroll = total_img_h - height

    if max_scroll <= 0:
        # Fits on screen - just shimmer in place
        hold_start = time.time()
        while time.time() - hold_start < 2.0:
            render(stdscr, particles, height, width, time.time(), is_shimmering=True)
            time.sleep(1/fps)
        return

    duration = 4.0
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed >= duration:
            break

        t = elapsed / duration
        scroll = max_scroll * ease_in_out_sine(t)

        # Update particle positions
        for p in particles:
            p.y = p.base_y - scroll

        render(stdscr, particles, height, width, elapsed, is_shimmering=True)
        time.sleep(1/fps)

    # Lock scroll position
    for p in particles:
        p.y = p.base_y - max_scroll

    # Pause at bottom with shimmer
    hold_start = time.time()
    while time.time() - hold_start < 2.0:
        render(stdscr, particles, height, width, time.time(), is_shimmering=True)
        time.sleep(1/fps)


def animate_out(stdscr, particles, height, width, jerry_frame=None):
    """Randomly flip splash characters to reveal Jerry UI."""
    fps = 24
    duration = 1.2
    start_time = time.time()

    if not jerry_frame:
        jerry_frame = [' ' * (width - 1) for _ in range(height)]

    # Build list of all positions and shuffle
    flip_positions = [(y, x) for y in range(height) for x in range(width - 1)]
    random.shuffle(flip_positions)

    total = len(flip_positions)
    done = 0

    while done < total:
        elapsed = time.time() - start_time
        t = min(1.0, elapsed / duration)
        target = max(done + 1, int(t * total))

        for i in range(done, min(target, total)):
            y, x = flip_positions[i]
            try:
                ch = jerry_frame[y][x] if x < len(jerry_frame[y]) else ' '
                stdscr.addch(y, x, ch, curses.A_NORMAL)
            except:
                pass

        done = target
        stdscr.refresh()
        if done < total:
            time.sleep(1/fps)


def capture_jerry_frame(stdscr, jerry_callback, height, width):
    """Capture Jerry's first frame to a buffer.

    Args:
        stdscr: Curses screen
        jerry_callback: Function to render Jerry UI
        height: Screen height
        width: Screen width

    Returns:
        List of strings representing Jerry's frame
    """
    # Create offscreen window
    try:
        capture_win = curses.newwin(height, width - 1, 0, 0)
    except curses.error:
        return None

    # We need to temporarily make jerry_callback render to capture_win
    # This requires modifying how the callback works
    # For now, return None and handle in animate_out
    return None


def rgb_to_color_index(r, g, b):
    """Convert RGB to nearest curses color index (0-255 for 256-color terminals)."""
    # Map RGB to 6x6x6 color cube (216 colors) + grayscale
    if r == g == b:
        # Grayscale
        if r < 8:
            return 16  # Black
        elif r > 248:
            return 231  # White
        else:
            return 232 + int((r - 8) / 240 * 23)
    else:
        # 6x6x6 color cube
        r_idx = int(r / 256 * 6)
        g_idx = int(g / 256 * 6)
        b_idx = int(b / 256 * 6)
        r_idx = min(5, r_idx)
        g_idx = min(5, g_idx)
        b_idx = min(5, b_idx)
        return 16 + 36 * r_idx + 6 * g_idx + b_idx


def load_png_as_ascii(png_path, target_chars_w, target_chars_h):
    """Load PNG and convert to colored ASCII."""
    try:
        from PIL import Image
    except ImportError:
        return None, None
    
    try:
        img = Image.open(png_path)
        img = img.convert('RGB')
    except Exception:
        return None, None
    
    img_quantized = img.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    img = img_quantized.convert('RGB')
    
    # Scale by width, account for 2:1 character cell aspect ratio in PIL resize
    img_w, img_h = img.size
    scale = target_chars_w / img_w
    new_w = target_chars_w
    new_h = int(img_h * scale)
    
    # Resize with aspect ratio correction - characters are 2x tall as wide
    img_resized = img.resize((new_w, new_h // 2), Image.Resampling.LANCZOS)
    
    # Fine gradient for detail
    density = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
    lines = []
    color_grid = []
    
    for y in range(img_resized.size[1]):
        line = ""
        colors = []
        for x in range(new_w):
            r, g, b = img_resized.getpixel((x, y))
            brightness = (r + g + b) / 3
            char_idx = min(len(density) - 1, int(brightness / 256 * len(density)))
            line += density[char_idx]
            colors.append(rgb_to_color_index(r, g, b))
        lines.append(line)
        color_grid.append(colors)
    
    return lines, color_grid


def init_color_pairs_from_hex(stdscr, color_grid, max_pairs=128):
    """Initialize curses color pairs from hex color codes."""
    # Get unique colors
    unique_colors = set()
    for row in color_grid:
        for hex_color in row:
            unique_colors.add(hex_color)
    
    try:
        curses.start_color()
        curses.use_default_colors()
    except:
        return {}
    
    # Map hex colors to color pairs (start at 65 to leave room for Jerry's UI)
    color_map = {}
    pair_num = 65
    
    for hex_color in unique_colors:
        if pair_num > 255 or pair_num >= 65 + max_pairs:
            break
        
        # Convert hex to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        try:
            curses.init_color(pair_num, r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
            curses.init_pair(pair_num, pair_num, -1)
            color_map[hex_color] = pair_num
            pair_num += 1
        except:
            pass
    
    return color_map


def init_color_pairs(stdscr, color_grid, max_pairs=128):
    """Initialize curses color pairs from a color grid.

    Args:
        stdscr: Curses screen
        color_grid: 2D array of color indices
        max_pairs: Maximum color pairs to use (leave room for Jerry's UI)

    Returns:
        Dictionary mapping original color indices to curses color pair numbers
    """
    # Get unique colors from the grid
    unique_colors = set()
    for row in color_grid:
        for color_idx in row:
            unique_colors.add(color_idx)

    # Initialize colors if terminal supports it
    try:
        curses.start_color()
        curses.use_default_colors()
    except:
        return {}

    # Map color indices to color pairs (1-255, 0 is default)
    # Reserve pairs 1-64 for Jerry's UI, use 65+ for splash
    color_map = {}
    pair_num = 65

    for color_idx in unique_colors:
        if pair_num > 255 or pair_num >= 65 + max_pairs:
            break  # Max color pairs reached
        
        # Convert 256-color index back to RGB approximation
        if color_idx < 16:
            # Standard colors
            r, g, b = _get_standard_color_rgb(color_idx)
        elif color_idx < 232:
            # 6x6x6 color cube
            idx = color_idx - 16
            r = (idx // 36) % 6
            g = (idx // 6) % 6
            b = idx % 6
            r = 0 if r == 0 else 55 + r * 40
            g = 0 if g == 0 else 55 + g * 40
            b = 0 if b == 0 else 55 + b * 40
        else:
            # Grayscale
            gray = 8 + (color_idx - 232) * 10
            r = g = b = gray

        try:
            curses.init_color(pair_num, r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
            curses.init_pair(pair_num, pair_num, -1)  # Foreground color, default background
            color_map[color_idx] = pair_num
            pair_num += 1
        except:
            pass

    return color_map


def _get_standard_color_rgb(idx):
    """Get RGB values for standard 16 colors."""
    colors = [
        (0, 0, 0),      # 0: Black
        (128, 0, 0),    # 1: Red
        (0, 128, 0),    # 2: Green
        (128, 128, 0),  # 3: Yellow
        (0, 0, 128),    # 4: Blue
        (128, 0, 128),  # 5: Magenta
        (0, 128, 128),  # 6: Cyan
        (192, 192, 192),# 7: White
        (128, 128, 128),# 8: Bright Black
        (255, 0, 0),    # 9: Bright Red
        (0, 255, 0),    # 10: Bright Green
        (255, 255, 0),  # 11: Bright Yellow
        (0, 0, 255),    # 12: Bright Blue
        (255, 0, 255),  # 13: Bright Magenta
        (0, 255, 255),  # 14: Bright Cyan
        (255, 255, 255),# 15: Bright White
    ]
    return colors[idx] if idx < len(colors) else (128, 128, 128)


def main(stdscr, jerry_frame=None, face_panel_capture=None):
    """Run splash screen animation.

    Args:
        stdscr: Curses screen
        jerry_frame: Optional pre-captured Jerry UI frame for transition
    """
    # Don't hide keyboard - Jerry will handle it
    # hide_termux_keyboard()
    curses.curs_set(0)
    curses.noecho()
    stdscr.timeout(0)

    try:
        curses.start_color()
        curses.use_default_colors()
    except:
        pass

    script_dir = os.path.dirname(os.path.abspath(__file__))
    faces_dir = os.path.join(script_dir, '..', 'faces')

    height, width = stdscr.getmaxyx()
    margin = 2

    # Try to load pre-generated colored ASCII art from faces directory
    # Rarity: plain (80%), unique (15%), old B&W splash_faces (5%)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    faces_dir = os.path.normpath(os.path.join(script_dir, '..', 'faces'))
    lines = None
    color_grid = None
    
    # Determine which splash to use based on rarity
    roll = random.random()
    if roll < 0.05:
        # 5% chance - old B&W splash_faces
        chosen_file = None
    elif roll < 0.20:
        # 15% chance - unique
        chosen_file = 'face_unique.json'
    else:
        # 80% chance - plain
        chosen_file = 'face_plain.json'
    
    if chosen_file:
        face_path = os.path.join(faces_dir, chosen_file)
        if os.path.exists(face_path):
            try:
                with open(face_path, 'r') as f:
                    data = json.load(f)
                lines = data.get('lines', [])
                if 'colors' in data:
                    color_grid = data['colors']
            except:
                pass  # Silently fallback to splash_faces
    
    # Fallback to splash_faces if JSON not found or B&W selected
    if lines is None:
        splash_path = os.path.join(script_dir, 'splash_faces')
        try:
            with open(splash_path, 'r') as f:
                content = f.read()
            lines = content.rstrip('\n').split('\n')
        except FileNotFoundError:
            stdscr.addstr(0, 0, "Error: 'splash_faces' file not found!")
            stdscr.refresh()
            time.sleep(2)
            return

    splash_h = len(lines)
    splash_w = max(len(line) for line in lines) if lines else 0

    scale = (width - margin * 2) / splash_w if splash_w > 0 else 1

    # Initialize color pairs if we have color data
    color_map = {}
    if color_grid:
        # Convert hex colors to curses color pairs
        color_map = init_color_pairs_from_hex(stdscr, color_grid)
        # Remap color_grid to use color pair numbers
        for row_idx in range(len(color_grid)):
            for col_idx in range(len(color_grid[row_idx])):
                orig_color = color_grid[row_idx][col_idx]
                color_grid[row_idx][col_idx] = color_map.get(orig_color, 0)

    particles = create_particles(lines, color_grid)

    # 1. Edge-diffusion radial build in the center
    animate_assembly(stdscr, particles, height, width, scale, splash_w)

    # 2. Scroll up while shimmering, stop at bottom
    animate_scroll(stdscr, particles, height, width, splash_h, scale)

    # 3. Diffuse out the top (evaporate) - fade into Jerry
    animate_out(stdscr, particles, height, width, jerry_frame)

    # Don't show keyboard - Jerry will handle it
    # show_termux_keyboard()


if __name__ == '__main__':
    curses.wrapper(main)

