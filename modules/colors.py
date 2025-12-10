#!/usr/bin/env python3
"""
OOPUO Desktop Environment - BTOP-Inspired Color Theme
"""
import random
from config import config

def col(text, color_code):
    """Apply ANSI 256-color to text"""
    return f"\033[38;5;{color_code}m{text}\033[0m"

def bg(text, color_code):
    """Apply ANSI 256-color background"""
    return f"\033[48;5;{color_code}m{text}\033[0m"

def bold(text):
    """Bold text"""
    return f"\033[1m{text}\033[0m"

def dim(text):
    """Dim text"""
    return f"\033[2m{text}\033[0m"

# Theme colors from config
C_PRIMARY = config.get('theme.primary', 51)
C_SUCCESS = config.get('theme.success', 46)
C_ERROR = config.get('theme.error', 196)
C_MUTED = config.get('theme.muted', 240)
C_ACCENT = config.get('theme.accent', 198)
C_TEXT = config.get('theme.text', 255)

# BTOP-inspired gradient colors for graphs
GRAPH_GRADIENT = [
    232, 233, 234, 235, 236, 237,  # Dark greys
    25, 26, 27, 33, 39,            # Deep blues
    45, 51, 87, 123,               # Bright blues
    117, 159, 195, 231,            # Cyan-ish
    194, 158, 122, 86              # Gradient to green
]

GPU_GRADIENT = [
    46, 47, 48, 49, 50,            # Greens (low temp)
    226, 220, 214, 208,            # Yellows (medium temp)
    202, 196, 160, 124             # Oranges/Reds (high temp)
]

def gradient_bar(value, max_value, width=20, gradient=GRAPH_GRADIENT):
    """
    Create a horizontal gradient bar like BTOP
    
    Args:
        value: Current value (e.g., 45 for 45% CPU)
        max_value: Maximum value (e.g., 100 for percentage)
        width: Width of the bar in characters
        gradient: List of color codes to use
    
    Returns:
        Colored string representing the bar
    """
    filled = int((value / max_value) * width)
    bar = ""
    
    for i in range(width):
        if i < filled:
            # Calculate which gradient color to use
            color_idx = int((i / width) * (len(gradient) - 1))
            color = gradient[color_idx]
            bar += col("▁", color)
        else:
            bar += col("▁", C_MUTED)
    
    return bar

def sparkline(values, height=8, width=20):
    """
    Create a sparkline graph like BTOP
    
    Args:
        values: List of numeric values (recent first)
        height: Height in characters
        width: Width in characters
    
    Returns:
        Multi-line string with graph
    """
    if not values:
        return ""
    
    # Normalize values to height
    max_val = max(values) if max(values) > 0 else 1
    normalized = [int((v / max_val) * height) for v in values[-width:]]
    
    # Build graph from top to bottom
    chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    lines = []
    
    for y in range(height - 1, -1, -1):
        line = ""
        for x, val in enumerate(normalized):
            if val > y:
                # Calculate gradient color based on height
                color_idx = int((y / height) * (len(GRAPH_GRADIENT) - 1))
                color = GRAPH_GRADIENT[color_idx]
                line += col(chars[min(val - y, 7)], color)
            else:
                line += " "
        lines.append(line)
    
    return "\n".join(lines)

def glitch_text(text, probability=0.05):
    """
    Apply subtle glitch effect to text (OOPUO signature)
    
    Args:
        text: Input string
        probability: Chance each character glitches (0.0-1.0)
    
    Returns:
        Glitched string
    """
    glitch_chars = "▓▒░█▄▀"
    result = ""
    
    for char in text:
        if char != ' ' and random.random() < probability:
            result += col(random.choice(glitch_chars), C_ACCENT)
        else:
            result += char
    
    return result

def box_chars(style='double'):
    """
    Get box drawing characters
    
    Args:
        style: 'single', 'double', or 'rounded'
    
    Returns:
        Dict with box chars
    """
    styles = {
        'single': {
            'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
            'h': '─', 'v': '│', 't': '┬', 'b': '┴', 'l': '├', 'r': '┤', 'x': '┼'
        },
        'double': {
            'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
            'h': '═', 'v': '║', 't': '╦', 'b': '╩', 'l': '╠', 'r': '╣', 'x': '╬'
        },
        'rounded': {
            'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯',
            'h': '─', 'v': '│', 't': '┬', 'b': '┴', 'l': '├', 'r': '┤', 'x': '┼'
        }
    }
    
    return styles.get(style, styles['double'])

def temp_color(temp, thresholds=(60, 80)):
    """
    Get color code for temperature
    
    Args:
        temp: Temperature in Celsius
        thresholds: (low, high) thresholds
    
    Returns:
        Color code (int)
    """
    if temp < thresholds[0]:
        return config.get('theme.gpu_temp_low', 46)
    elif temp < thresholds[1]:
        return config.get('theme.gpu_temp_mid', 226)
    else:
        return config.get('theme.gpu_temp_high', 196)
