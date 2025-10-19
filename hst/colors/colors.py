"""
Simple color constants for terminal output.

Automatically detects if colors should be used based on terminal capability.
Colors are empty strings when not supported, so they can be used directly.
"""

import sys

# Lazy evaluation - only check once when module is imported
use_colors = sys.stdout.isatty()

# Standard colors
BLACK = "\033[30m" if use_colors else ""
RED = "\033[31m" if use_colors else ""
GREEN = "\033[32m" if use_colors else ""
YELLOW = "\033[33m" if use_colors else ""
BLUE = "\033[34m" if use_colors else ""
MAGENTA = "\033[35m" if use_colors else ""
CYAN = "\033[36m" if use_colors else ""
WHITE = "\033[37m" if use_colors else ""

# Bright colors
BRIGHT_BLACK = "\033[90m" if use_colors else ""
BRIGHT_RED = "\033[91m" if use_colors else ""
BRIGHT_GREEN = "\033[92m" if use_colors else ""
BRIGHT_YELLOW = "\033[93m" if use_colors else ""
BRIGHT_BLUE = "\033[94m" if use_colors else ""
BRIGHT_MAGENTA = "\033[95m" if use_colors else ""
BRIGHT_CYAN = "\033[96m" if use_colors else ""
BRIGHT_WHITE = "\033[97m" if use_colors else ""

# Styles
BOLD = "\033[1m" if use_colors else ""
DIM = "\033[2m" if use_colors else ""
UNDERLINE = "\033[4m" if use_colors else ""

# Reset
RESET = "\033[0m" if use_colors else ""
