"""
Configuration settings for Fleet Management System
"""
import os
from tkinter import font

# Application paths. Keep runtime data separate from source code so the app
# behaves the same when launched from a shortcut, PowerShell, or a Git clone.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")
MOVEMENTS_DIR = os.path.join(DATA_DIR, "kiniseis")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# Database configuration
DB_PATH = os.path.join(DATA_DIR, "oximata.db")
TANK_MIN_LEVEL = 500
TANK_CAPACITY = 10000  # Συνολική χωρητικότητα δεξαμενής σε λίτρα
DEFAULT_PASSWORD = "1"
SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")  # Αρχείο για αποθήκευση ρυθμίσεων χρήστη

import json

def ensure_app_directories():
    """Create runtime directories used by the application."""
    for path in (DATA_DIR, IMAGES_DIR, BACKUPS_DIR, MOVEMENTS_DIR, LOGS_DIR):
        os.makedirs(path, exist_ok=True)

ensure_app_directories()

def save_user_setting(key, value):
    """Save user setting to file"""
    try:
        # Load existing settings
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except FileNotFoundError:
            settings = {}
        
        # Update setting
        settings[key] = value
        
        # Save back to file
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving setting {key}: {e}")
        return False

def load_user_setting(key, default_value=None):
    """Load user setting from file"""
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return settings.get(key, default_value)
    except FileNotFoundError:
        return default_value
    except Exception as e:
        print(f"Error loading setting {key}: {e}")
        return default_value

# Font configuration - using system fonts for better compatibility
def get_system_fonts():
    """Get available system fonts"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        available_fonts = list(font.families())
        root.destroy()
        
        # Preferred fonts in order
        preferred_fonts = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans"]
        
        for font_name in preferred_fonts:
            if font_name in available_fonts:
                return font_name
        
        return "TkDefaultFont"
    except:
        return "TkDefaultFont"

SYSTEM_FONT = get_system_fonts()

def get_adaptive_font_sizes(screen_width=None, screen_height=None):
    """Get font sizes adapted to screen size"""
    if screen_width is None or screen_height is None:
        # Default sizes for unknown screen
        return {
            'FONT_BIG': (SYSTEM_FONT, 18, "bold"),
            'FONT_NORMAL': (SYSTEM_FONT, 12),
            'FONT_SMALL': (SYSTEM_FONT, 10),
            'FONT_TITLE': (SYSTEM_FONT, 16, "bold"),
            'FONT_SUBTITLE': (SYSTEM_FONT, 14, "bold")
        }
    
    # Calculate font sizes based on screen resolution
    if screen_width < 1366:  # Small laptop screens
        return {
            'FONT_BIG': (SYSTEM_FONT, 14, "bold"),
            'FONT_NORMAL': (SYSTEM_FONT, 10),
            'FONT_SMALL': (SYSTEM_FONT, 8),
            'FONT_TITLE': (SYSTEM_FONT, 12, "bold"),
            'FONT_SUBTITLE': (SYSTEM_FONT, 11, "bold")
        }
    elif screen_width < 1920:  # Standard laptop/desktop screens
        return {
            'FONT_BIG': (SYSTEM_FONT, 16, "bold"),
            'FONT_NORMAL': (SYSTEM_FONT, 11),
            'FONT_SMALL': (SYSTEM_FONT, 9),
            'FONT_TITLE': (SYSTEM_FONT, 14, "bold"),
            'FONT_SUBTITLE': (SYSTEM_FONT, 12, "bold")
        }
    else:  # Large desktop monitors
        return {
            'FONT_BIG': (SYSTEM_FONT, 18, "bold"),
            'FONT_NORMAL': (SYSTEM_FONT, 12),
            'FONT_SMALL': (SYSTEM_FONT, 10),
            'FONT_TITLE': (SYSTEM_FONT, 16, "bold"),
            'FONT_SUBTITLE': (SYSTEM_FONT, 14, "bold")
        }

# Default font sizes (will be updated dynamically)
FONT_BIG = (SYSTEM_FONT, 18, "bold")
FONT_NORMAL = (SYSTEM_FONT, 12)
FONT_SMALL = (SYSTEM_FONT, 10)
FONT_TITLE = (SYSTEM_FONT, 16, "bold")
FONT_SUBTITLE = (SYSTEM_FONT, 14, "bold")

# Color themes
THEMES = {
    "light": {
        "bg": "#f8f9fa",
        "fg": "#212529",
        "select_bg": "#007bff",
        "select_fg": "#ffffff",
        "button_bg": "#007bff",
        "button_fg": "#ffffff",
        "button_hover": "#0056b3",
        "entry_bg": "#ffffff",
        "tree_bg": "#ffffff",
        "frame_bg": "#ffffff",
        "accent": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "success": "#28a745",
        "info": "#17a2b8",
        "border": "#dee2e6",
        "text_muted": "#6c757d"
    },
    "dark": {
        "bg": "#1a1a1a",
        "fg": "#e0e0e0",
        "select_bg": "#0d7377",
        "select_fg": "#ffffff",
        "button_bg": "#0d7377",
        "button_fg": "#ffffff",
        "button_hover": "#14a085",
        "entry_bg": "#2d2d2d",
        "tree_bg": "#2d2d2d",
        "frame_bg": "#252525",
        "accent": "#4caf50",
        "warning": "#ff9800",
        "danger": "#f44336",
        "success": "#4caf50",
        "info": "#2196f3",
        "border": "#404040",
        "text_muted": "#b0b0b0"
    },
    "blue": {
        "bg": "#f0f4f8",
        "fg": "#1a202c",
        "select_bg": "#3182ce",
        "select_fg": "#ffffff",
        "button_bg": "#3182ce",
        "button_fg": "#ffffff",
        "button_hover": "#2c5282",
        "entry_bg": "#ffffff",
        "tree_bg": "#ffffff",
        "frame_bg": "#edf2f7",
        "accent": "#38a169",
        "warning": "#d69e2e",
        "danger": "#e53e3e",
        "success": "#38a169",
        "info": "#3182ce",
        "border": "#cbd5e0",
        "text_muted": "#718096"
    },
    "green": {
        "bg": "#f0fff4",
        "fg": "#1a202c",
        "select_bg": "#38a169",
        "select_fg": "#ffffff",
        "button_bg": "#38a169",
        "button_fg": "#ffffff",
        "button_hover": "#2f855a",
        "entry_bg": "#ffffff",
        "tree_bg": "#ffffff",
        "frame_bg": "#e6fffa",
        "accent": "#38a169",
        "warning": "#d69e2e",
        "danger": "#e53e3e",
        "success": "#38a169",
        "info": "#3182ce",
        "border": "#9ae6b4",
        "text_muted": "#718096"
    },
    "purple": {
        "bg": "#faf5ff",
        "fg": "#1a202c",
        "select_bg": "#805ad5",
        "select_fg": "#ffffff",
        "button_bg": "#805ad5",
        "button_fg": "#ffffff",
        "button_hover": "#6b46c1",
        "entry_bg": "#ffffff",
        "tree_bg": "#ffffff",
        "frame_bg": "#e9d8fd",
        "accent": "#805ad5",
        "warning": "#d69e2e",
        "danger": "#e53e3e",
        "success": "#38a169",
        "info": "#3182ce",
        "border": "#c4b5fd",
        "text_muted": "#718096"
    }
}

# Button styles
BUTTON_STYLES = {
    "primary": {
        "bg": "#007bff",
        "fg": "#ffffff",
        "activebackground": "#0056b3",
        "activeforeground": "#ffffff",
        "relief": "flat",
        "borderwidth": 0,
        "padx": 20,
        "pady": 8,
        "font": FONT_NORMAL
    },
    "success": {
        "bg": "#28a745",
        "fg": "#ffffff",
        "activebackground": "#1e7e34",
        "activeforeground": "#ffffff",
        "relief": "flat",
        "borderwidth": 0,
        "padx": 20,
        "pady": 8,
        "font": FONT_NORMAL
    },
    "warning": {
        "bg": "#ffc107",
        "fg": "#212529",
        "activebackground": "#e0a800",
        "activeforeground": "#212529",
        "relief": "flat",
        "borderwidth": 0,
        "padx": 20,
        "pady": 8,
        "font": FONT_NORMAL
    },
    "danger": {
        "bg": "#dc3545",
        "fg": "#ffffff",
        "activebackground": "#c82333",
        "activeforeground": "#ffffff",
        "relief": "flat",
        "borderwidth": 0,
        "padx": 20,
        "pady": 8,
        "font": FONT_NORMAL
    },
    "secondary": {
        "bg": "#6c757d",
        "fg": "#ffffff",
        "activebackground": "#545b62",
        "activeforeground": "#ffffff",
        "relief": "flat",
        "borderwidth": 0,
        "padx": 20,
        "pady": 8,
        "font": FONT_NORMAL
    }
}

# Logging configuration
LOGGING_CONFIG = {
    'filename': os.path.join(LOGS_DIR, "oximata.log"),
    'level': "INFO",
    'format': "%(asctime)s %(levelname)s: %(message)s"
}
