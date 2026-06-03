#!/usr/bin/env python3
"""
Improved Fleet Management System
Βελτιωμένο Σύστημα Διαχείρισης Στόλου

Key improvements:
- Better code organization with separate modules
- Enhanced UI with modern components
- Improved error handling and validation
- Better user experience with tooltips and status updates
- Enhanced search and filtering capabilities
- Comprehensive logging and audit trail
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
from datetime import datetime
import os
import sys
import logging
import csv
import html

# Import custom modules
from database import DatabaseManager
from ui_components import (
    ModernButton, ModernFrame, SearchableCombobox, 
    StatusBar, ProgressDialog, ConfirmDialog, ValidationMixin, TooltipManager
)
from utils import (
    normalize_plate, normalize_name, ensure_dir, validate_date,
    format_currency, format_distance, format_fuel, hash_password,
    export_to_csv, backup_file, DataValidator, log_user_action
)
from config import (
    THEMES, BUTTON_STYLES, FONT_BIG, FONT_NORMAL, FONT_SMALL,
    FONT_TITLE, FONT_SUBTITLE, IMAGES_DIR, TANK_MIN_LEVEL,
    TANK_CAPACITY, DEFAULT_PASSWORD, LOGGING_CONFIG, BACKUPS_DIR,
    MOVEMENTS_DIR
)

# Configure logging
logging.basicConfig(**LOGGING_CONFIG)

# Optional imports with graceful fallback
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not available - photo features will be limited")

try:
    from openpyxl import Workbook
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logging.warning("openpyxl not available - Excel export disabled")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("reportlab not available - movement order PDF generation disabled")

class FleetManagerImproved(ValidationMixin):
    """Improved Fleet Management System with better UX and code organization"""
    
    def __init__(self, root):
        self.root = root
        # Load saved theme preference
        from config import load_user_setting
        self.current_theme = load_user_setting("theme", "light")
        self.db = None
        self._pdf_font_name = None
        self.tooltip_manager = TooltipManager()
        
        # Initialize application
        self._setup_window()
        self._setup_database()
        
        # Authenticate user
        if not self._authenticate_user():
            self.root.destroy()
            return
        
        # Build UI
        self._build_main_ui()
        self._setup_event_handlers()
        
        # Initialize data
        self._initialize_data()
        
        log_user_action("Application started")
    
    def _setup_window(self):
        """Setup main window properties with adaptive sizing"""
        self.root.title("Οχήματα - Διαχείριση Στόλου")
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate optimal window size based on screen size
        if screen_width < 1366:  # Small laptop screens
            window_width = int(screen_width * 0.95)
            window_height = int(screen_height * 0.90)
        elif screen_width < 1920:  # Standard laptop/desktop screens
            window_width = int(screen_width * 0.85)
            window_height = int(screen_height * 0.85)
        else:  # Large desktop monitors
            window_width = int(screen_width * 0.75)
            window_height = int(screen_height * 0.75)
        
        # Set minimum and maximum sizes
        min_width = 1000
        min_height = 700
        # Allow window to use full screen size when maximized
        max_width = screen_width
        max_height = screen_height
        
        # Ensure window size is within bounds
        window_width = max(min_width, min(window_width, max_width))
        window_height = max(min_height, min(window_height, max_height))
        
        # Set window size and constraints
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(min_width, min_height)
        # Remove maxsize restriction to allow full screen maximize
        # self.root.maxsize(max_width, max_height)
        
        # Enable window resizing in all directions
        self.root.resizable(True, True)
        
        # Update font sizes based on screen size
        self._update_font_sizes(screen_width, screen_height)
        
        # Configure background
        self.root.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Center window on screen
        self.root.update_idletasks()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Store window dimensions for later use
        self.window_width = window_width
        self.window_height = window_height
        
        # Additional window configuration for better behavior
        self.root.state('normal')  # Ensure window starts in normal state
        
        # Configure window attributes for better maximize behavior
        self.root.attributes('-topmost', False)  # Don't keep always on top
        
        # Set window to start in the center of the primary monitor
        # This ensures proper behavior across multiple monitors
        try:
            # Force window to be visible and properly positioned
            self.root.withdraw()  # Hide window temporarily
            self.root.update_idletasks()  # Process all pending events
            self.root.deiconify()  # Show window again
        except Exception as e:
            logging.warning(f"Error in window positioning: {e}")
        
        # Bind window state events for better maximize handling
        self.root.bind('<Configure>', self._on_window_configure)
        
        # Set window icon if available
        self._set_window_icon()
        
        # Log window setup
        logging.info(f"Window setup: {window_width}x{window_height} on {screen_width}x{screen_height} screen")
        
        # Ensure window gets focus and is brought to front
        self.root.focus_force()
        self.root.lift()
        self.root.attributes('-topmost', True)  # Temporarily bring to front
        self.root.after(100, lambda: self.root.attributes('-topmost', False))  # Remove topmost after 100ms
    
    def _set_window_icon(self):
        """Set application icon"""
        try:
            if getattr(sys, 'frozen', False):
                application_path = sys._MEIPASS  # type: ignore
            else:
                application_path = os.path.dirname(os.path.abspath(__file__))

            icon_path = os.path.join(application_path, "fleet_icon.png")
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
        except Exception as e:
            logging.warning(f"Could not set window icon: {e}")
    
    def _on_window_configure(self, event):
        """Handle window configuration changes for better resize behavior"""
        # Only handle main window configure events, not child widgets
        if event.widget == self.root:
            # Get current window dimensions
            current_width = self.root.winfo_width()
            current_height = self.root.winfo_height()
            
            # Update stored dimensions if they've changed significantly
            if (abs(current_width - self.window_width) > 10 or 
                abs(current_height - self.window_height) > 10):
                self.window_width = current_width
                self.window_height = current_height
                
                # Optional: Adjust font sizes if window becomes very large or small
                self._adjust_fonts_for_window_size(current_width, current_height)
    
    def _adjust_fonts_for_window_size(self, width, height):
        """Adjust font sizes based on current window size"""
        try:
            # Calculate a scaling factor based on window size
            base_width = 1200
            base_height = 800
            
            width_scale = width / base_width
            height_scale = height / base_height
            scale_factor = min(width_scale, height_scale)
            
            # Don't scale too much
            scale_factor = max(0.8, min(scale_factor, 1.5))
            
            # Update global font sizes (optional - only if you want dynamic scaling)
            # You can uncomment these if you want fonts to scale with window size
            # global FONT_TITLE, FONT_SUBTITLE, FONT_NORMAL, FONT_SMALL
            # base_title_size = 16
            # base_subtitle_size = 12
            # base_normal_size = 10
            # base_small_size = 8
            
            # FONT_TITLE = ("Segoe UI", int(base_title_size * scale_factor), "bold")
            # FONT_SUBTITLE = ("Segoe UI", int(base_subtitle_size * scale_factor), "bold")
            # FONT_NORMAL = ("Segoe UI", int(base_normal_size * scale_factor))
            # FONT_SMALL = ("Segoe UI", int(base_small_size * scale_factor))
            
        except Exception as e:
            logging.warning(f"Error adjusting fonts for window size: {e}")
    
    def _setup_database(self):
        """Initialize database connection"""
        try:
            ensure_dir(IMAGES_DIR)
            self.db = DatabaseManager()
            logging.info("Database initialized successfully")
        except Exception as e:
            messagebox.showerror("❌ Σφάλμα Βάσης Δεδομένων", 
                               f"Αδυναμία σύνδεσης με τη βάση δεδομένων:\n{str(e)}")
            self.root.destroy()
            raise
    
    def _authenticate_user(self):
        """Authenticate user with improved security"""
        max_attempts = 3
        hash_pwd = hash_password(DEFAULT_PASSWORD)
        
        # Create a custom authentication dialog that stays on top
        return self._show_auth_dialog(max_attempts, hash_pwd)
    
    def _show_auth_dialog(self, max_attempts, hash_pwd):
        """Show authentication dialog that stays on top"""
        for attempt in range(max_attempts):
            remaining = max_attempts - attempt
            
            # Create authentication window
            auth_window = tk.Toplevel(self.root)
            auth_window.title("Κωδικός Πρόσβασης")
            auth_window.geometry("350x180")
            auth_window.resizable(False, False)
            auth_window.configure(bg='#f0f0f0')
            
            # Center the window on screen
            auth_window.update_idletasks()
            x = (auth_window.winfo_screenwidth() // 2) - (350 // 2)
            y = (auth_window.winfo_screenheight() // 2) - (180 // 2)
            auth_window.geometry(f"350x180+{x}+{y}")
            
            # Make it stay on top and modal
            auth_window.transient(self.root)
            auth_window.grab_set()
            auth_window.attributes('-topmost', True)
            auth_window.focus_force()
            
            # Store the result
            result = {'password': None, 'cancelled': False}
            
            # Create UI elements
            tk.Label(auth_window, text="🔐 Εισάγετε κωδικό πρόσβασης:", 
                    font=("Segoe UI", 12), bg='#f0f0f0').pack(pady=15)
            
            tk.Label(auth_window, text=f"(Απομένουν {remaining} προσπάθειες)", 
                    font=("Segoe UI", 10), bg='#f0f0f0', fg='#666').pack(pady=5)
            
            # Password entry
            password_var = tk.StringVar()
            password_entry = tk.Entry(auth_window, textvariable=password_var, 
                                    show="*", font=("Segoe UI", 12), width=20)
            password_entry.pack(pady=10)
            password_entry.focus_set()
            
            # Button frame
            btn_frame = tk.Frame(auth_window, bg='#f0f0f0')
            btn_frame.pack(pady=15)
            
            def on_ok():
                result['password'] = password_var.get()
                auth_window.destroy()
            
            def on_cancel():
                result['cancelled'] = True
                auth_window.destroy()
            
            def on_enter(event):
                on_ok()
            
            # Bind Enter key to OK
            password_entry.bind('<Return>', on_enter)
            auth_window.bind('<Return>', on_enter)
            
            # Buttons
            tk.Button(btn_frame, text="OK", command=on_ok, 
                     font=("Segoe UI", 10), width=8).pack(side=tk.LEFT, padx=5)
            tk.Button(btn_frame, text="Cancel", command=on_cancel, 
                     font=("Segoe UI", 10), width=8).pack(side=tk.LEFT, padx=5)
            
            # Wait for the dialog to close
            auth_window.wait_window()
            
            # Check result
            if result['cancelled']:
                return False
            
            pwd = result['password']
            if pwd and hash_password(pwd) == hash_pwd:
                log_user_action("User authenticated successfully")
                return True
            
            if attempt < max_attempts - 1:  # Not the last attempt
                # Show error message
                error_window = tk.Toplevel(self.root)
                error_window.title("Λάθος Κωδικός")
                error_window.geometry("300x120")
                error_window.resizable(False, False)
                error_window.configure(bg='#f0f0f0')
                
                # Center error window
                error_window.update_idletasks()
                x = (error_window.winfo_screenwidth() // 2) - (300 // 2)
                y = (error_window.winfo_screenheight() // 2) - (120 // 2)
                error_window.geometry(f"300x120+{x}+{y}")
                
                error_window.transient(self.root)
                error_window.grab_set()
                error_window.attributes('-topmost', True)
                error_window.focus_force()
                
                tk.Label(error_window, text="❌ Λάθος κωδικός!", 
                        font=("Segoe UI", 12), bg='#f0f0f0', fg='red').pack(pady=15)
                tk.Label(error_window, text=f"Απομένουν {remaining - 1} προσπάθειες", 
                        font=("Segoe UI", 10), bg='#f0f0f0').pack(pady=5)
                
                def close_error():
                    error_window.destroy()
                
                tk.Button(error_window, text="OK", command=close_error, 
                         font=("Segoe UI", 10)).pack(pady=10)
                
                error_window.wait_window()
        
        # Final error - max attempts exceeded
        final_error = tk.Toplevel(self.root)
        final_error.title("Πρόσβαση Απορρίφθηκε")
        final_error.geometry("350x120")
        final_error.resizable(False, False)
        final_error.configure(bg='#f0f0f0')
        
        # Center final error window
        final_error.update_idletasks()
        x = (final_error.winfo_screenwidth() // 2) - (350 // 2)
        y = (final_error.winfo_screenheight() // 2) - (120 // 2)
        final_error.geometry(f"350x120+{x}+{y}")
        
        final_error.transient(self.root)
        final_error.grab_set()
        final_error.attributes('-topmost', True)
        final_error.focus_force()
        
        tk.Label(final_error, text="❌ Πρόσβαση Απορρίφθηκε!", 
                font=("Segoe UI", 12), bg='#f0f0f0', fg='red').pack(pady=15)
        tk.Label(final_error, text="Υπερβήκατε τον μέγιστο αριθμό προσπαθειών", 
                font=("Segoe UI", 10), bg='#f0f0f0').pack(pady=5)
        
        def close_final():
            final_error.destroy()
        
        tk.Button(final_error, text="OK", command=close_final, 
                 font=("Segoe UI", 10)).pack(pady=10)
        
        final_error.wait_window()
        
        log_user_action("Authentication failed - max attempts exceeded")
        return False
    
    def _build_main_ui(self):
        """Build the main user interface"""
        # Create main container
        self.main_container = tk.Frame(self.root, bg=THEMES[self.current_theme]["bg"])
        self.main_container.pack(fill="both", expand=True)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create tab control
        self._create_tab_control()
        
        # Create status bar with tank indicator
        self.status_bar = StatusBar(self.main_container, bg=THEMES[self.current_theme]["bg"])
        self.status_bar.pack(side="bottom", fill="x")
        
        # Add tank indicator to status bar
        self.tank_indicator = tk.Label(self.status_bar, text="⛽ Φόρτωση...", 
                                      font=FONT_NORMAL, bg=THEMES[self.current_theme]["bg"],
                                      fg=THEMES[self.current_theme]["fg"])
        self.tank_indicator.pack(side="right", padx=10)
        
        self.status_bar.set_status("Εφαρμογή φορτώθηκε επιτυχώς")
    
    def _create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root, bg=THEMES[self.current_theme]["bg"], 
                         fg=THEMES[self.current_theme]["fg"])
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=THEMES[self.current_theme]["bg"], 
                           fg=THEMES[self.current_theme]["fg"])
        menubar.add_cascade(label="📁 Αρχείο", menu=file_menu)
        file_menu.add_command(label="💾 Backup Βάσης", command=self._backup_database)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Έξοδος", command=self._on_close)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0, bg=THEMES[self.current_theme]["bg"], 
                           fg=THEMES[self.current_theme]["fg"])
        menubar.add_cascade(label="🎨 Εμφάνιση", menu=view_menu)
        
        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0, bg=THEMES[self.current_theme]["bg"], 
                            fg=THEMES[self.current_theme]["fg"])
        view_menu.add_cascade(label="🎨 Θέματα", menu=theme_menu)
        
        # Add theme options
        theme_menu.add_command(label="☀️ Φωτεινό", command=lambda: self._change_theme("light"))
        theme_menu.add_command(label="🌙 Σκοτεινό", command=lambda: self._change_theme("dark"))
        theme_menu.add_command(label="💙 Μπλε", command=lambda: self._change_theme("blue"))
        theme_menu.add_command(label="💚 Πράσινο", command=lambda: self._change_theme("green"))
        theme_menu.add_command(label="💜 Μωβ", command=lambda: self._change_theme("purple"))
        
        view_menu.add_separator()
        view_menu.add_command(label="🔄 Ανανέωση Δεδομένων", command=self._refresh_all_data)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0, bg=THEMES[self.current_theme]["bg"], 
                            fg=THEMES[self.current_theme]["fg"])
        menubar.add_cascade(label="🔧 Εργαλεία", menu=tools_menu)
        
        # Theme tools submenu
        theme_tools_menu = tk.Menu(tools_menu, tearoff=0, bg=THEMES[self.current_theme]["bg"], 
                                  fg=THEMES[self.current_theme]["fg"])
        tools_menu.add_cascade(label="🎨 Εναλλαγή Θέματος", menu=theme_tools_menu)
        
        # Quick theme switching
        theme_tools_menu.add_command(label="🔄 Επόμενο Θέμα (Ctrl+T)", command=self._toggle_theme)
        theme_tools_menu.add_separator()
        theme_tools_menu.add_command(label="☀️ Φωτεινό", command=lambda: self._change_theme("light"))
        theme_tools_menu.add_command(label="🌙 Σκοτεινό", command=lambda: self._change_theme("dark"))
        theme_tools_menu.add_command(label="💙 Μπλε", command=lambda: self._change_theme("blue"))
        theme_tools_menu.add_command(label="💚 Πράσινο", command=lambda: self._change_theme("green"))
        theme_tools_menu.add_command(label="💜 Μωβ", command=lambda: self._change_theme("purple"))
        
        tools_menu.add_separator()
        tools_menu.add_command(label="🔄 Ανανέωση Δεδομένων (F5)", command=self._refresh_all_data)
        tools_menu.add_command(label="💾 Backup Βάσης (Ctrl+S)", command=self._backup_database)
        tools_menu.add_separator()
        tools_menu.add_command(label="📊 Στατιστικά Συστήματος", command=self._show_system_stats)
        tools_menu.add_command(label="🧹 Καθαρισμός Παλιών Δεδομένων", command=self._cleanup_old_data)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=THEMES[self.current_theme]["bg"], 
                           fg=THEMES[self.current_theme]["fg"])
        menubar.add_cascade(label="❓ Βοήθεια", menu=help_menu)
        help_menu.add_command(label="📖 Οδηγίες Χρήσης", command=self._show_help)
        help_menu.add_command(label="ℹ️ Σχετικά", command=self._show_about)
    
    def _toggle_theme(self):
        """Toggle between themes in sequence"""
        themes_sequence = ["light", "dark", "blue", "green", "purple"]
        current_index = themes_sequence.index(self.current_theme)
        next_index = (current_index + 1) % len(themes_sequence)
        self._change_theme(themes_sequence[next_index])
    
    def _create_tab_control(self):
        """Create main tab control with beautiful colors"""
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure tab styling with soft colors
        style.configure('TNotebook', 
                       background=THEMES[self.current_theme]["bg"],
                       borderwidth=0)
        
        style.configure('TNotebook.Tab', 
                       padding=[20, 12], 
                       font=FONT_NORMAL,
                       background='#F5F5F5',  # Ουδέτερο γκρι για ανενεργές καρτέλες
                       foreground='#2C3E50',   # Σκούρο γκρι κείμενο
                       borderwidth=1)
        
        style.configure('TNotebook.Tab', 
                       focuscolor='none')
        
        style.map('TNotebook.Tab',
                 background=[('selected', '#34495E'),     # Σκούρο γκρι-μπλε για ενεργή καρτέλα
                            ('active', '#BDC3C7')],       # Ανοιχτό γκρι για hover
                 foreground=[('selected', 'white'),       # Λευκό κείμενο για ενεργή καρτέλα
                            ('active', '#2C3E50')])
        
        self.tab_control = ttk.Notebook(self.main_container, style='TNotebook')
        
        # Create tabs with more distinct soft colors
        self.tab_movements = tk.Frame(self.tab_control, bg='#E8F5E8')    # Απαλό πράσινο φύλλου
        self.tab_vehicles = tk.Frame(self.tab_control, bg='#FFF4E6')     # Απαλό πορτοκαλί/κρεμ
        self.tab_drivers = tk.Frame(self.tab_control, bg='#E6F3FF')      # Απαλό γαλάζιο ουρανού
        self.tab_driver_analytics = tk.Frame(self.tab_control, bg='#F0F8F0')  # Απαλό πράσινο μέντας
        self.tab_fuel = tk.Frame(self.tab_control, bg='#F0E6FF')         # Απαλό λεβάντα/μωβ
        self.tab_purposes = tk.Frame(self.tab_control, bg='#F5F5DC')     # Απαλό μπεζ
        self.tab_reports = tk.Frame(self.tab_control, bg='#FFE6F0')      # Απαλό ρόζ
        
        # Add tabs with improved icons and labels
        self.tab_control.add(self.tab_movements, text="🚗 Κινήσεις Οχημάτων")
        self.tab_control.add(self.tab_vehicles, text="🚙 Διαχείριση Οχημάτων")
        self.tab_control.add(self.tab_drivers, text="👤 Διαχείριση Οδηγών")
        self.tab_control.add(self.tab_driver_analytics, text="📈 Αναλυτικά Οδηγών")
        self.tab_control.add(self.tab_fuel, text="⛽ Διαχείριση Καυσίμων")
        self.tab_control.add(self.tab_purposes, text="🎯 Διαχείριση Σκοπών")
        self.tab_control.add(self.tab_reports, text="📊 Αναφορές & Στατιστικά")
        
        self.tab_control.pack(expand=1, fill="both", padx=10, pady=5)
        
        # Build individual tabs
        self._build_movements_tab()
        self._build_vehicles_tab()
        self._build_drivers_tab()
        self._build_driver_analytics_tab()
        self._build_fuel_tab()
        self._build_purposes_tab()
        self._build_reports_tab()
    
    def _setup_event_handlers(self):
        """Setup global event handlers"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind('<F5>', lambda e: self._refresh_all_data())
        self.root.bind('<Control-s>', lambda e: self._backup_database())
        self.root.bind('<Control-q>', lambda e: self._on_close())
        self.root.bind('<Control-t>', lambda e: self._toggle_theme())  # Theme toggle shortcut
        
        # Window management shortcuts
        self.root.bind('<F11>', self._toggle_fullscreen)
        self.root.bind('<Alt-Return>', self._toggle_maximize)
        self.root.bind('<Control-0>', self._reset_window_size)
        
        # Track fullscreen state
        self.is_fullscreen = False
        
    def _toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        try:
            self.is_fullscreen = not self.is_fullscreen
            if self.is_fullscreen:
                self.root.attributes('-fullscreen', True)
                self.root.bind('<Escape>', self._exit_fullscreen)
            else:
                self.root.attributes('-fullscreen', False)
                self.root.unbind('<Escape>')
        except Exception as e:
            logging.warning(f"Error toggling fullscreen: {e}")
    
    def _exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        try:
            self.is_fullscreen = False
            self.root.attributes('-fullscreen', False)
            self.root.unbind('<Escape>')
        except Exception as e:
            logging.warning(f"Error exiting fullscreen: {e}")
    
    def _toggle_maximize(self, event=None):
        """Toggle maximized state"""
        try:
            if self.root.state() == 'zoomed':
                self.root.state('normal')
            else:
                self.root.state('zoomed')
        except Exception as e:
            logging.warning(f"Error toggling maximize: {e}")
    
    def _reset_window_size(self, event=None):
        """Reset window to default size"""
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Calculate default size (same logic as in _setup_window)
            if screen_width < 1366:
                window_width = int(screen_width * 0.95)
                window_height = int(screen_height * 0.90)
            elif screen_width < 1920:
                window_width = int(screen_width * 0.85)
                window_height = int(screen_height * 0.85)
            else:
                window_width = int(screen_width * 0.75)
                window_height = int(screen_height * 0.75)
            
            # Center window
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            
            self.root.state('normal')
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
        except Exception as e:
            logging.warning(f"Error resetting window size: {e}")
    
    def _initialize_data(self):
        """Initialize application data"""
        try:
            self._refresh_all_data()
            self._update_tank_level()
            self.status_bar.set_status("Δεδομένα φορτώθηκαν επιτυχώς")
        except Exception as e:
            logging.error(f"Error initializing data: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη φόρτωση δεδομένων: {str(e)}")
    
    def _build_movements_tab(self):
        """Build improved movements tab"""
        # Create main scrollable container
        canvas = tk.Canvas(self.tab_movements, bg=THEMES[self.current_theme]["bg"])
        scrollbar = ttk.Scrollbar(self.tab_movements, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # New movement form
        self._create_movement_form(scrollable_frame)
        
        # Active movements section
        self._create_active_movements_section(scrollable_frame)
        
        # Completed movements section
        self._create_completed_movements_section(scrollable_frame)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def _create_movement_form(self, parent):
        """Create new movement form with improved validation"""
        form_frame = ModernFrame(parent, theme=self.current_theme)
        form_frame.pack(fill="x", padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            form_frame, 
            text="📝 Έκδοση Νέας Κίνησης Οχήματος", 
            font=FONT_TITLE, 
            fg=THEMES[self.current_theme]["accent"],
            bg=THEMES[self.current_theme]["frame_bg"]
        )
        title_label.pack(pady=(15, 20))
        
        # Form container with grid layout
        form_container = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        form_container.pack(fill="x", padx=20, pady=10)
        
        # Configure grid weights for responsive design
        for i in range(3):
            form_container.grid_columnconfigure(i, weight=1)
        
        # Date field
        tk.Label(form_container, text="📅 Ημερομηνία:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0, sticky="w", padx=5, pady=8)
        
        self.mov_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.mov_date_entry = tk.Entry(
            form_container, 
            textvariable=self.mov_date_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.mov_date_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=8)
        
        # Add tooltip
        self.tooltip_manager.add_tooltip(self.mov_date_entry, "Μορφή: YYYY-MM-DD")
        
        # Driver field with improved search
        tk.Label(form_container, text="👤 Οδηγός:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=1, column=0, sticky="w", padx=5, pady=8)
        
        self.mov_driver_combo = SearchableCombobox(
            form_container, 
            font=FONT_NORMAL, 
            placeholder="Αναζήτηση οδηγού..."
        )
        self.mov_driver_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=8)
        
        # Vehicle field with improved search
        tk.Label(form_container, text="🚗 Όχημα:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=2, column=0, sticky="w", padx=5, pady=8)
        
        self.mov_vehicle_combo = SearchableCombobox(
            form_container, 
            font=FONT_NORMAL,
            placeholder="Αναζήτηση οχήματος..."
        )
        self.mov_vehicle_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=8)
        
        # Start km field with validation
        tk.Label(form_container, text="🛣️ Χλμ Αναχώρησης:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=3, column=0, sticky="w", padx=5, pady=8)
        
        self.mov_start_km_var = tk.StringVar()
        self.mov_start_km_entry = tk.Entry(
            form_container, 
            textvariable=self.mov_start_km_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.mov_start_km_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=8)
        
        # Route field
        tk.Label(form_container, text="🗺️ Διαδρομή:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=4, column=0, sticky="w", padx=5, pady=8)
        
        self.mov_route_entry = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.mov_route_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=8)

        # Purpose field
        tk.Label(form_container, text="🎯 Σκοπός:", font=FONT_NORMAL,
                 bg=THEMES[self.current_theme]["frame_bg"],
                 fg=THEMES[self.current_theme]["fg"]).grid(row=5, column=0, sticky="w", padx=5, pady=8)
        # Get purposes from database
        self.purpose_options = self.db.get_purpose_names(active_only=True)
        self.mov_purpose_combobox = SearchableCombobox(
            form_container,
            values=self.purpose_options,
            font=FONT_NORMAL,
            width=30,
            placeholder="Επιλέξτε σκοπό..."
        )
        self.mov_purpose_combobox.grid(row=5, column=1, sticky="ew", padx=5, pady=8)
        
        # Submit button
        button_frame = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        button_frame.pack(pady=20)
        
        # Movement submission button
        submit_btn = ModernButton(
            button_frame, 
            text="✅ Έκδοση Κίνησης", 
            style="success",
            command=self._add_movement
        )
        submit_btn.pack(side="left", padx=5)
        
        # Browse movements button
        browse_btn = ModernButton(
            button_frame, 
            text="📁 Περιήγηση Κινήσεων", 
            style="info",
            command=self._browse_movement_documents
        )
        browse_btn.pack(side="left", padx=5)

        # Reprint movement order by movement number
        reprint_btn = ModernButton(
            button_frame,
            text="🖨️ Επανεκτύπωση",
            style="secondary",
            command=self._reprint_movement_document
        )
        reprint_btn.pack(side="left", padx=5)
        
        # Add tooltips
        self.tooltip_manager.add_tooltip(submit_btn, "Δημιουργεί νέα κίνηση και εκτυπώσιμο έγγραφο")
        self.tooltip_manager.add_tooltip(browse_btn, "Περιήγηση στις αποθηκευμένες κινήσεις ανά έτος/μήνα")
        self.tooltip_manager.add_tooltip(reprint_btn, "Επανεκτύπωση εντολής με βάση τον αριθμό κίνησης")
        
        # Bind vehicle selection to auto-fill
        self.mov_vehicle_combo.var.trace("w", self._auto_fill_last_km)
    
    def _create_active_movements_section(self, parent):
        """Create active movements section"""
        active_frame = ModernFrame(parent, theme=self.current_theme)
        active_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Title
        title_label = tk.Label(
            active_frame, 
            text="🚨 Ενεργές Κινήσεις (Δεν έχουν επιστρέψει)", 
            font=FONT_SUBTITLE, 
            fg=THEMES[self.current_theme]["warning"],
            bg=THEMES[self.current_theme]["frame_bg"]
        )
        title_label.pack(pady=(15, 10))
        
        # Search frame
        search_frame = tk.Frame(active_frame, bg=THEMES[self.current_theme]["frame_bg"])
        search_frame.pack(fill="x", padx=15, pady=5)
        
        tk.Label(search_frame, text="🔍 Αναζήτηση:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.active_search_var = tk.StringVar()
        self.active_search_entry = tk.Entry(
            search_frame, 
            textvariable=self.active_search_var,
            font=FONT_NORMAL, 
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.active_search_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.active_search_var.trace("w", lambda *args: self._load_movements())
        
        # Tree for active movements
        tree_frame = tk.Frame(active_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tree_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.tree_active = ttk.Treeview(
            tree_frame,
            columns=("movement_num", "date", "driver", "vehicle", "start_km", "route", "purpose"),
            show="headings",
            height=6
        )
        
        # Configure columns
        columns_config = [
            ("movement_num", "🔢 Αρ. Κίνησης", 100),
            ("date", "📅 Ημερομηνία", 120),
            ("driver", "👤 Οδηγός", 150),
            ("vehicle", "🚗 Όχημα", 120),
            ("start_km", "🛣️ Χλμ Αναχ.", 100),
            ("route", "🗺️ Διαδρομή", 200),
            ("purpose", "🎯 Σκοπός", 150)
        ]
        
        for col, text, width in columns_config:
            self.tree_active.heading(col, text=text)
            self.tree_active.column(col, width=width, anchor="center")
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_active.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree_active.xview)
        self.tree_active.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree_active.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Bind double-click for editing
        self.tree_active.bind("<Double-1>", self._edit_movement_return)
    
    def _create_completed_movements_section(self, parent):
        """Create completed movements section"""
        completed_frame = ModernFrame(parent, theme=self.current_theme)
        completed_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Title
        title_label = tk.Label(
            completed_frame, 
            text="✅ Ολοκληρωμένες Κινήσεις (Σήμερα)", 
            font=FONT_SUBTITLE, 
            fg=THEMES[self.current_theme]["success"],
            bg=THEMES[self.current_theme]["frame_bg"]
        )
        title_label.pack(pady=(15, 10))
        
        # Search frame
        search_frame = tk.Frame(completed_frame, bg=THEMES[self.current_theme]["frame_bg"])
        search_frame.pack(fill="x", padx=15, pady=5)
        
        tk.Label(search_frame, text="🔍 Αναζήτηση:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.completed_search_var = tk.StringVar()
        self.completed_search_entry = tk.Entry(
            search_frame, 
            textvariable=self.completed_search_var,
            font=FONT_NORMAL, 
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.completed_search_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.completed_search_var.trace("w", lambda *args: self._load_movements())
        
        # Tree for completed movements
        tree_frame = tk.Frame(completed_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tree_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.tree_completed = ttk.Treeview(
            tree_frame,
            columns=("movement_num", "date", "driver", "vehicle", "start_km", "end_km", "total_km", "route", "purpose"),
            show="headings",
            height=6
        )
        
        # Configure columns
        columns_config = [
            ("movement_num", "🔢 Αρ. Κίνησης", 100),
            ("date", "📅 Ημερομηνία", 120),
            ("driver", "👤 Οδηγός", 150),
            ("vehicle", "🚗 Όχημα", 120),
            ("start_km", "🛣️ Χλμ Αναχ.", 100),
            ("end_km", "🛣️ Χλμ Επιστρ.", 100),
            ("total_km", "📊 Σύνολο", 100),
            ("route", "🗺️ Διαδρομή", 200),
            ("purpose", "🎯 Σκοπός", 150)
        ]
        
        for col, text, width in columns_config:
            self.tree_completed.heading(col, text=text)
            self.tree_completed.column(col, width=width, anchor="center")
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_completed.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree_completed.xview)
        self.tree_completed.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree_completed.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Bind double-click for editing
        self.tree_completed.bind("<Double-1>", self._edit_completed_movement)
    
    def _build_vehicles_tab(self):
        """Build improved vehicles tab with two-column layout"""
        # Main content frame
        main_content = tk.Frame(self.tab_vehicles, bg=THEMES[self.current_theme]["bg"])
        main_content.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Configure grid weights for responsive design  
        main_content.grid_columnconfigure(0, weight=1)  # Left column (form)
        main_content.grid_columnconfigure(1, weight=2)  # Right column (list)
        main_content.grid_rowconfigure(0, weight=1)
        
        # LEFT COLUMN - Vehicle form
        form_frame = ModernFrame(main_content, bg=THEMES[self.current_theme]["frame_bg"])
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        
        # Title with modern styling
        title_label = tk.Label(form_frame, text="🚙 Προσθήκη/Επεξεργασία Οχήματος", 
                              font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["frame_bg"])
        title_label.pack(pady=(15, 15))

        # Create form container
        form_container = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        form_container.pack(fill="x", padx=15, pady=5)
        
        # Configure grid weights for responsive design
        form_container.grid_columnconfigure(1, weight=1)
        
        # Plate field
        tk.Label(form_container, text="🔢 Πινακίδα:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.ent_plate = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_plate.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # Brand field
        tk.Label(form_container, text="🏭 Μάρκα:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        self.ent_brand = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_brand.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Type field
        tk.Label(form_container, text="🚗 Τύπος:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        
        self.ent_vtype = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_vtype.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # Purpose field
        tk.Label(form_container, text="🎯 Σκοπός:", font=FONT_NORMAL,
                 bg=THEMES[self.current_theme]["frame_bg"],
                 fg=THEMES[self.current_theme]["fg"]).grid(row=3, column=0, sticky="w", padx=5, pady=5)
        # Get purposes from database
        self.vehicle_purpose_options = self.db.get_purpose_names(active_only=True)
        self.ent_vpurpose = SearchableCombobox(
            form_container,
            values=self.vehicle_purpose_options,
            font=FONT_NORMAL,
            width=25,
            placeholder="Επιλέξτε σκοπό..."
        )
        self.ent_vpurpose.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # Photo field
        tk.Label(form_container, text="🖼️ Φωτογραφία:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=4, column=0, sticky="w", padx=5, pady=5)

        # Photo handling with modern styling
        photo_container = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        photo_container.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
        
        self.photo_path_var = tk.StringVar()
        self.photo_label = tk.Label(photo_container, text="Δεν έχει επιλεγεί φωτογραφία", 
                                   fg=THEMES[self.current_theme]["text_muted"],
                                   bg=THEMES[self.current_theme]["frame_bg"], font=FONT_SMALL)
        self.photo_label.pack(side="left")
        
        photo_btn_frame = tk.Frame(photo_container, bg=THEMES[self.current_theme]["frame_bg"])
        photo_btn_frame.pack(side="right")
        
        ModernButton(photo_btn_frame, text="📁", style="secondary", 
                    command=self._select_photo).pack(side="left", padx=1)
        ModernButton(photo_btn_frame, text="👁️", style="info", 
                    command=self._view_photo).pack(side="left", padx=1)

        # Buttons with compact modern styling
        btn_frame = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        btn_frame.pack(pady=15)
        
        ModernButton(btn_frame, text="➕ Προσθήκη", style="success", 
                    command=self._add_vehicle).pack(side="left", padx=3)
        ModernButton(btn_frame, text="✏️ Ενημέρωση", style="primary", 
                    command=self._update_vehicle).pack(side="left", padx=3)
        ModernButton(btn_frame, text="🗑️ Διαγραφή", style="danger", 
                    command=self._delete_vehicle).pack(side="left", padx=3)
        ModernButton(btn_frame, text="🧹 Εκκαθάριση", style="warning", 
                    command=self._clear_vehicle_form).pack(side="left", padx=3)

        # RIGHT COLUMN - Vehicles list section
        vehicles_frame = ModernFrame(main_content, bg=THEMES[self.current_theme]["frame_bg"])
        vehicles_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        
        # Title for vehicles list
        vehicles_title = tk.Label(vehicles_frame, text="📋 Λίστα Οχημάτων", 
                                 font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                                 bg=THEMES[self.current_theme]["frame_bg"])
        vehicles_title.pack(pady=(15, 10))

        # Search frame with modern styling
        search_frame_v = tk.Frame(vehicles_frame, bg=THEMES[self.current_theme]["frame_bg"])
        search_frame_v.pack(fill="x", pady=5, padx=15)
        tk.Label(search_frame_v, text="🔍 Αναζήτηση:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        self.vehicles_search_var = tk.StringVar()
        self.vehicles_search_entry = tk.Entry(search_frame_v, textvariable=self.vehicles_search_var, 
                                             font=FONT_NORMAL, relief="flat", borderwidth=1, highlightthickness=1,
                                             highlightbackground=THEMES[self.current_theme]["border"],
                                             highlightcolor=THEMES[self.current_theme]["accent"])
        self.vehicles_search_entry.pack(side="left", padx=10, fill="x", expand=True)
        self.vehicles_search_var.trace("w", lambda *args: self._load_vehicles())

        # Tree with modern styling
        tree_container = tk.Frame(vehicles_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tree_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.tree_vehicles = ttk.Treeview(tree_container, 
                                        columns=("plate", "brand", "vtype", "purpose"), 
                                        show="headings", height=12)
        
        # Configure columns
        columns_config = [
            ("plate", "🔢 Πινακίδα", 120),
            ("brand", "🏭 Μάρκα", 150),
            ("vtype", "🚗 Τύπος", 120),
            ("purpose", "🎯 Σκοπός", 200)
        ]
        
        for col, text, width in columns_config:
            self.tree_vehicles.heading(col, text=text)
            self.tree_vehicles.column(col, width=width, anchor="center")
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_vehicles.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_vehicles.xview)
        self.tree_vehicles.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree_vehicles.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Bind events
        self.tree_vehicles.bind("<Double-1>", self._select_vehicle_from_tree)
        self.tree_vehicles.bind("<Button-3>", self._show_vehicle_context_menu)  # Right click
        
        # Create context menu for vehicles with modern styling
        self.vehicle_context_menu = tk.Menu(self.root, tearoff=0, 
                                           bg=THEMES[self.current_theme]["frame_bg"], 
                                           fg=THEMES[self.current_theme]["fg"],
                                           activebackground=THEMES[self.current_theme]["select_bg"],
                                           activeforeground=THEMES[self.current_theme]["select_fg"])
        self.vehicle_context_menu.add_command(label="📋 Ιστορικό Κινήσεων", command=self._show_vehicle_history)
        self.vehicle_context_menu.add_command(label="⛽ Ιστορικό Καυσίμων", command=self._show_vehicle_fuel_history)
        self.vehicle_context_menu.add_separator()
        self.vehicle_context_menu.add_command(label="📊 Στατιστικά Οχήματος", command=self._show_vehicle_statistics)
        self.vehicle_context_menu.add_separator()
        self.vehicle_context_menu.add_command(label="✏️ Επεξεργασία", command=self._select_vehicle_from_tree)
        self.vehicle_context_menu.add_command(label="🖼️ Προβολή Φωτογραφίας", command=self._view_vehicle_photo_from_tree)

        # Load initial data
        self._load_vehicles()
    
    def _build_drivers_tab(self):
        """Build improved drivers tab with two-column layout"""
        # Main container with scrollable frame
        main_canvas = tk.Canvas(self.tab_drivers, bg=THEMES[self.current_theme]["bg"], 
                               highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_drivers, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        # Title section
        title_frame = tk.Frame(scrollable_frame, bg=THEMES[self.current_theme]["bg"])
        title_frame.pack(fill="x", padx=10, pady=(10, 5))  # Reduced padding
        
        title_label = tk.Label(title_frame, text="👤 Διαχείριση Οδηγών", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack()

        # Main content section with two columns
        content_section = tk.Frame(scrollable_frame, bg=THEMES[self.current_theme]["bg"])
        content_section.pack(fill="both", expand=True, padx=10, pady=5)  # Reduced padding
        
        # Configure grid weights - optimize space usage
        content_section.grid_columnconfigure(0, weight=2, minsize=300)  # Form column (reduced weight)
        content_section.grid_columnconfigure(1, weight=3, minsize=600)  # List column (increased weight)
        content_section.grid_rowconfigure(0, weight=1)  # Make row expandable

        # Left column - Driver form
        form_frame = ModernFrame(content_section, bg=THEMES[self.current_theme]["frame_bg"])
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)  # Reduced padding
        
        # Form title
        form_title = tk.Label(form_frame, text="➕ Καταχώρηση Οδηγού", 
                             font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                             bg=THEMES[self.current_theme]["frame_bg"])
        form_title.pack(pady=(10, 15))  # Reduced padding

        # Form fields container
        form_container = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        form_container.pack(fill="x", padx=10, pady=5)  # Reduced padding
        
        # Name field
        tk.Label(form_container, text="👤 Όνομα:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        self.ent_name = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_name.pack(fill="x", pady=(0, 15))
        
        # Surname field
        tk.Label(form_container, text="👤 Επώνυμο:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        self.ent_surname = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_surname.pack(fill="x", pady=(0, 15))
        
        # Notes field
        tk.Label(form_container, text="📝 Σημειώσεις:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        self.ent_dnotes = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_dnotes.pack(fill="x", pady=(0, 15))  # Reduced padding

        # Buttons
        btn_frame = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        btn_frame.pack(pady=10)  # Reduced padding
        
        ModernButton(btn_frame, text="➕ Προσθήκη", style="success", 
                    command=self._add_driver).pack(pady=2)
        ModernButton(btn_frame, text="✏️ Ενημέρωση", style="primary", 
                    command=self._update_driver).pack(pady=2)
        ModernButton(btn_frame, text="🗑️ Διαγραφή", style="danger", 
                    command=self._delete_driver).pack(pady=2)
        ModernButton(btn_frame, text="🧹 Εκκαθάριση", style="warning", 
                    command=self._clear_driver_form).pack(pady=2)

        # Right column - Drivers list
        drivers_frame = ModernFrame(content_section, bg=THEMES[self.current_theme]["frame_bg"])
        drivers_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)  # Reduced padding
        
        # List title
        drivers_title = tk.Label(drivers_frame, text="📋 Λίστα Οδηγών", 
                                font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                                bg=THEMES[self.current_theme]["frame_bg"])
        drivers_title.pack(pady=(10, 8))  # Reduced padding

        # Search frame
        search_frame_d = tk.Frame(drivers_frame, bg=THEMES[self.current_theme]["frame_bg"])
        search_frame_d.pack(fill="x", pady=(0, 8), padx=10)  # Reduced padding
        
        tk.Label(search_frame_d, text="🔍 Αναζήτηση:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.drivers_search_var = tk.StringVar()
        self.drivers_search_entry = tk.Entry(search_frame_d, textvariable=self.drivers_search_var, 
                                           font=FONT_NORMAL, relief="flat", borderwidth=1, highlightthickness=1,
                                           highlightbackground=THEMES[self.current_theme]["border"],
                                           highlightcolor=THEMES[self.current_theme]["accent"])
        self.drivers_search_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)
        self.drivers_search_var.trace("w", lambda *args: self._load_drivers())

        # Tree container
        tree_container = tk.Frame(drivers_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))  # Reduced padding
        
        self.tree_drivers = ttk.Treeview(tree_container, 
                                       columns=("name", "surname", "notes"), 
                                       show="headings", height=15)  # Increased height
        
        # Configure columns
        columns_config = [
            ("name", "👤 Όνομα", 120),
            ("surname", "👤 Επώνυμο", 120),
            ("notes", "📝 Σημειώσεις", 200)
        ]
        
        for col, text, width in columns_config:
            self.tree_drivers.heading(col, text=text)
            self.tree_drivers.column(col, width=width, anchor="center")
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_drivers.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_drivers.xview)
        self.tree_drivers.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree_drivers.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Bind events
        self.tree_drivers.bind("<Double-1>", self._select_driver_from_tree)

        # Pack canvas and scrollbar
        main_canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10))

        # Load initial data
        self._load_drivers()
    
    def _build_driver_analytics_tab(self):
        """Build driver analytics tab"""
        # Main container
        main_frame = tk.Frame(self.tab_driver_analytics, bg=THEMES[self.current_theme]["bg"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text="📈 Αναλυτικά Στοιχεία Οδηγών", 
                              font=FONT_BIG, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack(pady=(0, 15))
        
        # Controls frame
        controls_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        controls_frame.pack(fill="x", pady=(0, 15))
        
        # Driver selection
        tk.Label(controls_frame, text="🧑 Επιλογή Οδηγού:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left", padx=(0, 10))
        
        self.analytics_driver_combo = SearchableCombobox(
            controls_frame, 
            font=FONT_NORMAL, width=25
        )
        self.analytics_driver_combo.pack(side="left", padx=(0, 20))
        
        # Date range
        tk.Label(controls_frame, text="📅 Από:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left", padx=(0, 5))
        
        self.analytics_start_date = tk.Entry(controls_frame, font=FONT_NORMAL, width=12)
        self.analytics_start_date.pack(side="left", padx=(0, 10))
        
        tk.Label(controls_frame, text="📅 Έως:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left", padx=(0, 5))
        
        self.analytics_end_date = tk.Entry(controls_frame, font=FONT_NORMAL, width=12)
        self.analytics_end_date.pack(side="left", padx=(0, 15))
        
        # Buttons
        ModernButton(controls_frame, text="📊 Ανάλυση", style="primary",
                    command=self._show_driver_analytics).pack(side="left", padx=(0, 10))
        
        ModernButton(controls_frame, text="👥 Όλοι Οδηγοί", style="info",
                    command=self._show_all_drivers_summary).pack(side="left")
        
        # Results area with notebook for different views
        results_notebook = ttk.Notebook(main_frame)
        results_notebook.pack(fill="both", expand=True)
        
        # Summary tab
        self.summary_frame = tk.Frame(results_notebook, bg=THEMES[self.current_theme]["frame_bg"])
        results_notebook.add(self.summary_frame, text="📋 Σύνοψη")
        
        # Details tab
        self.details_frame = tk.Frame(results_notebook, bg=THEMES[self.current_theme]["frame_bg"])
        results_notebook.add(self.details_frame, text="📈 Λεπτομέρειες")
        
        # Comparison tab
        self.comparison_frame = tk.Frame(results_notebook, bg=THEMES[self.current_theme]["frame_bg"])
        results_notebook.add(self.comparison_frame, text="⚖️ Σύγκριση")
        
        # Load drivers for selection
        self._load_analytics_drivers()
    
    def _build_fuel_tab(self):
        """Build improved fuel tab"""
        # Main container with scrollable frame
        main_canvas = tk.Canvas(self.tab_fuel, bg=THEMES[self.current_theme]["bg"], 
                               highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_fuel, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        # Top section with tank and pump side by side
        top_section = tk.Frame(scrollable_frame, bg=THEMES[self.current_theme]["bg"])
        top_section.pack(fill="x", padx=20, pady=20)
        
        # Configure grid weights for equal columns
        top_section.grid_columnconfigure(0, weight=1)
        top_section.grid_columnconfigure(1, weight=1)

        # Tank display (left column)
        tank_frame = ModernFrame(top_section, bg=THEMES[self.current_theme]["frame_bg"])
        tank_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        tank_title = tk.Label(tank_frame, text="⛽ Κατάσταση Δεξαμενής", 
                             font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                             bg=THEMES[self.current_theme]["frame_bg"])
        tank_title.pack(pady=(15, 10))
        
        # Tank info container
        tank_info_frame = tk.Frame(tank_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tank_info_frame.pack(fill="x", padx=20, pady=10)
        
        self.tank_level_label = tk.Label(tank_info_frame, text="Φόρτωση...", 
                                        font=FONT_BIG, fg=THEMES[self.current_theme]["success"],
                                        bg=THEMES[self.current_theme]["frame_bg"])
        self.tank_level_label.pack(pady=10)
        
        # Tank capacity info
        capacity_label = tk.Label(tank_info_frame, 
                                 text=f"🛢️ Συνολική Χωρητικότητα: {TANK_CAPACITY:,.0f} Λίτρα", 
                                 font=FONT_NORMAL, fg=THEMES[self.current_theme]["text_muted"],
                                 bg=THEMES[self.current_theme]["frame_bg"])
        capacity_label.pack(pady=(0, 5))
        
        # Progress bar for tank level
        progress_frame = tk.Frame(tank_info_frame, bg=THEMES[self.current_theme]["frame_bg"])
        progress_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(progress_frame, text="Επίπεδο Πλήρωσης:", 
                font=FONT_SMALL, fg=THEMES[self.current_theme]["text_muted"],
                bg=THEMES[self.current_theme]["frame_bg"]).pack(anchor="w")
        
        self.tank_progress = ttk.Progressbar(progress_frame, length=300, mode='determinate')
        self.tank_progress.pack(fill="x", pady=(5, 10))
        
        # Tank management buttons
        tank_btn_frame = tk.Frame(tank_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tank_btn_frame.pack(pady=15)
        
        ModernButton(tank_btn_frame, text="⛽ Ανεφοδιασμός", style="primary", 
                    command=self._refill_tank).pack(side="top", pady=2)
        ModernButton(tank_btn_frame, text="📋 Ιστορικό", style="info", 
                    command=self._show_tank_history).pack(side="top", pady=2)

        # Pump display (right column)
        pump_frame = ModernFrame(top_section, bg=THEMES[self.current_theme]["frame_bg"])
        pump_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        
        pump_title = tk.Label(pump_frame, text="⛽ Κατάσταση Αντλίας", 
                             font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                             bg=THEMES[self.current_theme]["frame_bg"])
        pump_title.pack(pady=(15, 10))
        
        # Pump info container
        pump_info_frame = tk.Frame(pump_frame, bg=THEMES[self.current_theme]["frame_bg"])
        pump_info_frame.pack(fill="x", padx=20, pady=10)
        
        self.pump_reading_label = tk.Label(pump_info_frame, text="Φόρτωση...", 
                                          font=FONT_BIG, fg=THEMES[self.current_theme]["info"],
                                          bg=THEMES[self.current_theme]["frame_bg"])
        self.pump_reading_label.pack(pady=10)
        
        # Pump info
        pump_info_label = tk.Label(pump_info_frame, 
                                  text="📊 Συνολικά λίτρα που διανεμήθηκαν από την αντλία", 
                                  font=FONT_NORMAL, fg=THEMES[self.current_theme]["text_muted"],
                                  bg=THEMES[self.current_theme]["frame_bg"])
        pump_info_label.pack(pady=(0, 5))
        
        # Spacer for visual balance
        spacer_frame = tk.Frame(pump_info_frame, bg=THEMES[self.current_theme]["frame_bg"], height=45)
        spacer_frame.pack(fill="x")
        
        # Pump management buttons
        pump_btn_frame = tk.Frame(pump_frame, bg=THEMES[self.current_theme]["frame_bg"])
        pump_btn_frame.pack(pady=15)
        
        ModernButton(pump_btn_frame, text="📊 Ενημέρωση", style="success", 
                    command=self._update_pump_reading).pack(side="top", pady=2)
        ModernButton(pump_btn_frame, text="📋 Ιστορικό", style="info", 
                    command=self._show_pump_history).pack(side="top", pady=2)

        # Form for fuel addition with modern styling - horizontal layout
        content_section = tk.Frame(scrollable_frame, bg=THEMES[self.current_theme]["bg"])
        content_section.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configure grid weights for two columns
        content_section.grid_columnconfigure(0, weight=1)  # Form column
        content_section.grid_columnconfigure(1, weight=2)  # History column (wider)

        # Left side - Form
        form_frame = ModernFrame(content_section, bg=THEMES[self.current_theme]["frame_bg"])
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        # Title with modern styling
        title_label = tk.Label(form_frame, text="⛽ Καταχώρηση Καυσίμων", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["frame_bg"])
        title_label.pack(pady=(15, 20))

        # Create compact form container
        form_container = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        form_container.pack(fill="x", padx=15, pady=10)
        
        # Date field - compact layout
        date_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        date_frame.pack(fill="x", pady=5)
        
        tk.Label(date_frame, text="📅 Ημερομηνία:", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.fuel_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.fuel_date_entry = tk.Entry(
            date_frame, 
            textvariable=self.fuel_date_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"],
            width=12
        )
        self.fuel_date_entry.pack(side="right", fill="x", expand=True)
        
        # Driver field - compact layout
        driver_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        driver_frame.pack(fill="x", pady=5)
        
        tk.Label(driver_frame, text="👤 Οδηγός:", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.fuel_driver_combo = SearchableCombobox(
            driver_frame, 
            font=FONT_NORMAL, 
            placeholder="Αναζήτηση οδηγού...",
            width=12
        )
        self.fuel_driver_combo.pack(side="right", fill="x", expand=True)
        
        # Vehicle field - compact layout
        vehicle_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        vehicle_frame.pack(fill="x", pady=5)
        
        tk.Label(vehicle_frame, text="🚗 Όχημα:", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.fuel_vehicle_combo = SearchableCombobox(
            vehicle_frame, 
            font=FONT_NORMAL,
            placeholder="Αναζήτηση οχήματος...",
            width=12
        )
        self.fuel_vehicle_combo.pack(side="right", fill="x", expand=True)
        
        # Liters field - compact layout
        liters_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        liters_frame.pack(fill="x", pady=5)
        
        tk.Label(liters_frame, text="⛽ Λίτρα:", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.fuel_liters_var = tk.StringVar()
        self.fuel_liters_entry = tk.Entry(
            liters_frame, 
            textvariable=self.fuel_liters_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"],
            width=12
        )
        self.fuel_liters_entry.pack(side="right", fill="x", expand=True)
        
        # Mileage field - compact layout
        mileage_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        mileage_frame.pack(fill="x", pady=5)
        
        tk.Label(mileage_frame, text="🛣️ Χιλιόμετρα:", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.fuel_mileage_var = tk.StringVar()
        self.fuel_mileage_entry = tk.Entry(
            mileage_frame, 
            textvariable=self.fuel_mileage_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"],
            width=12
        )
        self.fuel_mileage_entry.pack(side="right", fill="x", expand=True)
        
        # Cost field - compact layout
        cost_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        cost_frame.pack(fill="x", pady=5)
        
        tk.Label(cost_frame, text="💰 Κόστος (€):", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.fuel_cost_var = tk.StringVar()
        self.fuel_cost_entry = tk.Entry(
            cost_frame, 
            textvariable=self.fuel_cost_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"],
            width=12
        )
        self.fuel_cost_entry.pack(side="right", fill="x", expand=True)

        # Pump reading field - compact layout
        pump_frame = tk.Frame(form_container, bg=THEMES[self.current_theme]["frame_bg"])
        pump_frame.pack(fill="x", pady=5)
        
        tk.Label(pump_frame, text="📊 Μέτρηση:", font=FONT_NORMAL, width=12, anchor="w",
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        pump_input_frame = tk.Frame(pump_frame, bg=THEMES[self.current_theme]["frame_bg"])
        pump_input_frame.pack(side="right", fill="x", expand=True)
        
        self.fuel_pump_reading_var = tk.StringVar()
        self.fuel_pump_reading_entry = tk.Entry(
            pump_input_frame, 
            textvariable=self.fuel_pump_reading_var, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"],
            width=10
        )
        self.fuel_pump_reading_entry.pack(side="left", fill="x", expand=True)
        
        # Button to get current pump reading
        ModernButton(pump_input_frame, text="📊", style="info", 
                    command=self._get_current_pump_reading).pack(side="right", padx=(5, 0))

        # Buttons with modern styling
        btn_frame = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        btn_frame.pack(pady=20)
        
        ModernButton(btn_frame, text="➕ Προσθήκη", style="success", 
                    command=self._add_fuel).pack(pady=5, fill="x")
        ModernButton(btn_frame, text="🧹 Εκκαθάριση", style="warning", 
                    command=self._clear_fuel_form).pack(pady=5, fill="x")

        # Right side - Fuel records with modern styling
        fuel_frame = ModernFrame(content_section, bg=THEMES[self.current_theme]["frame_bg"])
        fuel_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        
        # Title for fuel records
        fuel_title = tk.Label(fuel_frame, text="📋 Ιστορικό Καυσίμων", 
                             font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                             bg=THEMES[self.current_theme]["frame_bg"])
        fuel_title.pack(pady=(15, 10))

        # Tree with modern styling
        tree_container = tk.Frame(fuel_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tree_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.tree_fuel = ttk.Treeview(tree_container, 
                                    columns=("date", "driver", "vehicle", "liters", "mileage", "cost"), 
                                    show="headings", height=8)
        
        # Configure columns
        columns_config = [
            ("date", "📅 Ημερομηνία", 120),
            ("driver", "👤 Οδηγός", 150),
            ("vehicle", "🚗 Όχημα", 120),
            ("liters", "⛽ Λίτρα", 100),
            ("mileage", "🛣️ Χιλιόμετρα", 120),
            ("cost", "💰 Κόστος", 100)
        ]
        
        for col, text, width in columns_config:
            self.tree_fuel.heading(col, text=text)
            self.tree_fuel.column(col, width=width, anchor="center")
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_fuel.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_fuel.xview)
        self.tree_fuel.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree_fuel.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # Pack canvas and scrollbar
        main_canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10))

        # Load initial data
        self._load_fuel()
        self._load_fuel_combos()
    
    def _build_purposes_tab(self):
        """Build purposes management tab with two-column layout"""
        # Main container with scrollable frame
        main_canvas = tk.Canvas(self.tab_purposes, bg=THEMES[self.current_theme]["bg"], 
                               highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_purposes, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        # Title section
        title_frame = tk.Frame(scrollable_frame, bg=THEMES[self.current_theme]["bg"])
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_label = tk.Label(title_frame, text="🎯 Διαχείριση Σκοπών", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack()

        # Main content section with two columns
        content_section = tk.Frame(scrollable_frame, bg=THEMES[self.current_theme]["bg"])
        content_section.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configure grid weights for equal columns
        content_section.grid_columnconfigure(0, weight=1)
        content_section.grid_columnconfigure(1, weight=2)  # Give more space to the list

        # Left column - Purpose form
        form_frame = ModernFrame(content_section, bg=THEMES[self.current_theme]["frame_bg"])
        form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        
        # Form title
        form_title = tk.Label(form_frame, text="➕ Καταχώρηση Σκοπού", 
                             font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                             bg=THEMES[self.current_theme]["frame_bg"])
        form_title.pack(pady=(15, 20))

        # Form fields container
        form_container = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        form_container.pack(fill="x", padx=15, pady=10)
        
        # Name field
        tk.Label(form_container, text="🎯 Όνομα Σκοπού:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        self.ent_purpose_name = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_purpose_name.pack(fill="x", pady=(0, 15))
        
        # Description field
        tk.Label(form_container, text="📝 Περιγραφή:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        self.ent_purpose_description = tk.Entry(
            form_container, 
            font=FONT_NORMAL,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground=THEMES[self.current_theme]["border"],
            highlightcolor=THEMES[self.current_theme]["accent"]
        )
        self.ent_purpose_description.pack(fill="x", pady=(0, 15))
        
        # Category field
        tk.Label(form_container, text="📂 Κατηγορία:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        self.purpose_categories = ["general", "operation", "transport", "maintenance", "cleaning", "repair", "inspection"]
        self.purpose_category_var = tk.StringVar(value="general")
        self.purpose_category_combo = ttk.Combobox(
            form_container,
            textvariable=self.purpose_category_var,
            values=self.purpose_categories,
            state="readonly",
            font=FONT_NORMAL
        )
        self.purpose_category_combo.pack(fill="x", pady=(0, 20))

        # Buttons
        btn_frame = tk.Frame(form_frame, bg=THEMES[self.current_theme]["frame_bg"])
        btn_frame.pack(pady=15)
        
        ModernButton(btn_frame, text="➕ Προσθήκη", style="success", 
                    command=self._add_purpose).pack(pady=2)
        ModernButton(btn_frame, text="✏️ Ενημέρωση", style="primary", 
                    command=self._update_purpose).pack(pady=2)
        ModernButton(btn_frame, text="🗑️ Απενεργοποίηση", style="danger", 
                    command=self._delete_purpose).pack(pady=2)
        ModernButton(btn_frame, text="♻️ Επαναφορά", style="warning", 
                    command=self._restore_purpose).pack(pady=2)
        ModernButton(btn_frame, text="🧹 Εκκαθάριση", style="warning", 
                    command=self._clear_purpose_form).pack(pady=2)

        # Right column - Purposes list
        purposes_frame = ModernFrame(content_section, bg=THEMES[self.current_theme]["frame_bg"])
        purposes_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        
        # List title
        purposes_title = tk.Label(purposes_frame, text="📋 Λίστα Σκοπών", 
                                font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                                bg=THEMES[self.current_theme]["frame_bg"])
        purposes_title.pack(pady=(15, 10))

        # Search and filter frame
        search_frame = tk.Frame(purposes_frame, bg=THEMES[self.current_theme]["frame_bg"])
        search_frame.pack(fill="x", pady=(0, 10), padx=15)
        
        # Search field
        tk.Label(search_frame, text="🔍 Αναζήτηση:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.purposes_search_var = tk.StringVar()
        self.purposes_search_entry = tk.Entry(search_frame, textvariable=self.purposes_search_var, 
                                           font=FONT_NORMAL, relief="flat", borderwidth=1, highlightthickness=1,
                                           highlightbackground=THEMES[self.current_theme]["border"],
                                           highlightcolor=THEMES[self.current_theme]["accent"])
        self.purposes_search_entry.pack(side="left", padx=(10, 15), fill="x", expand=True)
        self.purposes_search_var.trace("w", lambda *args: self._load_purposes())
        
        # Filter by category
        tk.Label(search_frame, text="📂 Κατηγορία:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(side="left")
        
        self.purpose_filter_var = tk.StringVar(value="all")
        filter_options = ["all"] + self.purpose_categories
        self.purpose_filter_combo = ttk.Combobox(
            search_frame,
            textvariable=self.purpose_filter_var,
            values=filter_options,
            state="readonly",
            font=FONT_NORMAL,
            width=12
        )
        self.purpose_filter_combo.pack(side="left", padx=(5, 0))
        self.purpose_filter_var.trace("w", lambda *args: self._load_purposes())

        # Show inactive checkbox
        self.show_inactive_var = tk.BooleanVar()
        show_inactive_cb = tk.Checkbutton(
            search_frame,
            text="Εμφάνιση απενεργοποιημένων",
            variable=self.show_inactive_var,
            font=FONT_SMALL,
            bg=THEMES[self.current_theme]["frame_bg"],
            fg=THEMES[self.current_theme]["fg"],
            command=self._load_purposes
        )
        show_inactive_cb.pack(side="right", padx=(15, 0))

        # Tree container
        tree_container = tk.Frame(purposes_frame, bg=THEMES[self.current_theme]["frame_bg"])
        tree_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        self.tree_purposes = ttk.Treeview(tree_container, 
                                       columns=("name", "description", "category", "active"), 
                                       show="headings", height=12)
        
        # Configure columns
        columns_config = [
            ("name", "🎯 Όνομα", 150),
            ("description", "📝 Περιγραφή", 200),
            ("category", "📂 Κατηγορία", 120),
            ("active", "✅ Ενεργός", 80)
        ]
        
        for col, text, width in columns_config:
            self.tree_purposes.heading(col, text=text)
            self.tree_purposes.column(col, width=width, anchor="center")
        
        # Add scrollbars
        v_scrollbar_p = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_purposes.yview)
        h_scrollbar_p = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_purposes.xview)
        self.tree_purposes.configure(yscrollcommand=v_scrollbar_p.set, xscrollcommand=h_scrollbar_p.set)
        
        self.tree_purposes.pack(side="left", fill="both", expand=True)
        v_scrollbar_p.pack(side="right", fill="y")
        h_scrollbar_p.pack(side="bottom", fill="x")
        
        # Bind events
        self.tree_purposes.bind("<Double-1>", self._select_purpose_from_tree)

        # Pack canvas and scrollbar
        main_canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10))

        # Load initial data
        self._load_purposes()
    
    def _build_reports_tab(self):
        """Build improved reports tab"""
        # Main container
        main_frame = tk.Frame(self.tab_reports, bg=THEMES[self.current_theme]["bg"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="📊 Αναφορές & Εξαγωγές", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack(pady=(0, 20))
        
        # Monthly Reports Section
        monthly_frame = ModernFrame(main_frame, bg=THEMES[self.current_theme]["frame_bg"])
        monthly_frame.pack(fill="x", pady=(0, 20))
        
        monthly_title = tk.Label(monthly_frame, text="📅 Μηνιαίες Αναφορές", 
                                font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                                bg=THEMES[self.current_theme]["frame_bg"])
        monthly_title.pack(pady=(15, 15))
        
        # Month/Year selection
        date_frame = tk.Frame(monthly_frame, bg=THEMES[self.current_theme]["frame_bg"])
        date_frame.pack(pady=10)
        
        tk.Label(date_frame, text="Μήνας:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0, padx=5)
        self.month_var = tk.StringVar(value=str(datetime.now().month))
        month_combo = ttk.Combobox(date_frame, textvariable=self.month_var, values=list(range(1, 13)), 
                                  width=10, state="readonly")
        month_combo.grid(row=0, column=1, padx=5)
        
        tk.Label(date_frame, text="Έτος:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=2, padx=5)
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        year_combo = ttk.Combobox(date_frame, textvariable=self.year_var, 
                                 values=list(range(2020, datetime.now().year + 5)), 
                                 width=10, state="readonly")
        year_combo.grid(row=0, column=3, padx=5)
        
        # Monthly export buttons
        btn_frame_monthly = tk.Frame(monthly_frame, bg=THEMES[self.current_theme]["frame_bg"])
        btn_frame_monthly.pack(pady=15)
        
        ModernButton(btn_frame_monthly, text="📄 Εξαγωγή CSV", style="primary", 
                    command=self._export_monthly_report_csv).pack(side="left", padx=5)
        
        if EXCEL_AVAILABLE:
            ModernButton(btn_frame_monthly, text="📊 Εξαγωγή Excel", style="success", 
                        command=self._export_monthly_report_excel).pack(side="left", padx=5)
        
        # General Reports Section
        general_frame = ModernFrame(main_frame, bg=THEMES[self.current_theme]["frame_bg"])
        general_frame.pack(fill="x", pady=(0, 20))
        
        general_title = tk.Label(general_frame, text="📋 Γενικές Εξαγωγές", 
                                font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                                bg=THEMES[self.current_theme]["frame_bg"])
        general_title.pack(pady=(15, 15))
        
        btn_frame_general = tk.Frame(general_frame, bg=THEMES[self.current_theme]["frame_bg"])
        btn_frame_general.pack(pady=10)
        
        ModernButton(btn_frame_general, text="🚗 Εξαγωγή Κινήσεων", style="primary", 
                    command=self._export_movements_csv).pack(side="left", padx=5)
        
        ModernButton(btn_frame_general, text="⛽ Εξαγωγή Καυσίμων", style="primary", 
                    command=self._export_fuel_csv).pack(side="left", padx=5)
        
        if EXCEL_AVAILABLE:
            ModernButton(btn_frame_general, text="📊 Γενική Αναφορά Excel", style="success", 
                        command=self._export_excel).pack(side="left", padx=5)
        
        # Statistics Section
        stats_frame = ModernFrame(main_frame, bg=THEMES[self.current_theme]["frame_bg"])
        stats_frame.pack(fill="both", expand=True)
        
        stats_title = tk.Label(stats_frame, text="📈 Στατιστικά", 
                              font=FONT_SUBTITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["frame_bg"])
        stats_title.pack(pady=(15, 15))
        
        # Text widget for statistics
        stats_container = tk.Frame(stats_frame, bg=THEMES[self.current_theme]["frame_bg"])
        stats_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.stats_text = tk.Text(stats_container, height=12, font=FONT_SMALL, wrap=tk.WORD,
                                 bg=THEMES[self.current_theme]["entry_bg"], 
                                 fg=THEMES[self.current_theme]["fg"],
                                 relief="flat", borderwidth=1)
        self.stats_text.pack(side="left", fill="both", expand=True)
        
        # Add scrollbar for stats
        stats_scrollbar = ttk.Scrollbar(stats_container, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        stats_scrollbar.pack(side="right", fill="y")
        
        # Refresh button
        refresh_btn_frame = tk.Frame(stats_frame, bg=THEMES[self.current_theme]["frame_bg"])
        refresh_btn_frame.pack(pady=10)
        ModernButton(refresh_btn_frame, text="🔄 Ανανέωση Στατιστικών", style="info", 
                    command=self._update_statistics).pack()
        
        self._update_statistics()
    
    # Vehicle management methods
    def _add_vehicle(self):
        """Add a new vehicle with improved validation"""
        try:
            plate = normalize_plate(self.ent_plate.get())
            brand = self.ent_brand.get().strip()
            vtype = self.ent_vtype.get().strip()
            purpose = self.ent_vpurpose.get().strip() if hasattr(self, 'ent_vpurpose') else ""
            photo_path = self.photo_path_var.get()
            
            # Validate required fields
            required_fields = {
                "Πινακίδα": plate
            }
            
            is_valid, error_msg = self.validate_required_fields(required_fields)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα Επικύρωσης", error_msg)
                return
            
            # Validate plate format
            is_valid, validated_plate = DataValidator.is_valid_plate(plate)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", validated_plate)
                return
            
            self.db.cursor.execute("""
                INSERT INTO vehicles (plate, brand, vtype, purpose, photo_path)
                VALUES (?, ?, ?, ?, ?)
            """, (validated_plate, brand, vtype, purpose, photo_path))
            
            self.db.conn.commit()
            self._clear_vehicle_form()
            self._load_vehicles()
            self._refresh_movement_combos()
            self._load_fuel_combos()  # Update fuel combos
            
            self.status_bar.set_status(f"Όχημα {validated_plate} προστέθηκε επιτυχώς")
            log_user_action("Vehicle added", f"Plate: {validated_plate}")
            messagebox.showinfo("✅ Επιτυχία", "Το όχημα προστέθηκε επιτυχώς!")
            
        except sqlite3.IntegrityError:
            messagebox.showerror("❌ Σφάλμα", "Η πινακίδα υπάρχει ήδη!")
        except Exception as e:
            logging.error(f"Error adding vehicle: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την προσθήκη: {str(e)}")

    def _update_vehicle(self):
        """Update selected vehicle"""
        selection = self.tree_vehicles.selection()
        if not selection:
            messagebox.showerror("❌ Σφάλμα", "Παρακαλώ επιλέξτε όχημα!")
            return
        
        try:
            item = selection[0]
            old_plate = self.tree_vehicles.item(item, "values")[0]
            
            plate = normalize_plate(self.ent_plate.get())
            brand = self.ent_brand.get().strip()
            vtype = self.ent_vtype.get().strip()
            purpose = self.ent_vpurpose.get().strip() if hasattr(self, 'ent_vpurpose') else ""
            photo_path = self.photo_path_var.get()
            
            # Validate plate
            is_valid, validated_plate = DataValidator.is_valid_plate(plate)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", validated_plate)
                return
            
            self.db.cursor.execute("""
                UPDATE vehicles 
                SET plate = ?, brand = ?, vtype = ?, purpose = ?, photo_path = ?
                WHERE plate = ?
            """, (validated_plate, brand, vtype, purpose, photo_path, old_plate))
            
            self.db.conn.commit()
            self._clear_vehicle_form()
            self._load_vehicles()
            self._refresh_movement_combos()
            
            self.status_bar.set_status(f"Όχημα {validated_plate} ενημερώθηκε επιτυχώς")
            log_user_action("Vehicle updated", f"Plate: {validated_plate}")
            messagebox.showinfo("✅ Επιτυχία", "Το όχημα ενημερώθηκε επιτυχώς!")
            
        except sqlite3.IntegrityError:
            messagebox.showerror("❌ Σφάλμα", "Η πινακίδα υπάρχει ήδη!")
        except Exception as e:
            logging.error(f"Error updating vehicle: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την ενημέρωση: {str(e)}")

    def _delete_vehicle(self):
        """Delete selected vehicle"""
        selection = self.tree_vehicles.selection()
        if not selection:
            messagebox.showerror("❌ Σφάλμα", "Παρακαλώ επιλέξτε όχημα!")
            return
        
        item = selection[0]
        plate = self.tree_vehicles.item(item, "values")[0]
        
        if ConfirmDialog(
            self.root,
            "🗑️ Επιβεβαίωση Διαγραφής",
            f"Είστε σίγουρος ότι θέλετε να διαγράψετε το όχημα {plate};\n\nΑυτή η ενέργεια θα διαγράψει και όλες τις σχετικές κινήσεις και καύσιμα!"
        ).show():
            try:
                self.db.cursor.execute("DELETE FROM vehicles WHERE plate = ?", (plate,))
                self.db.conn.commit()
                self._clear_vehicle_form()
                self._load_vehicles()
                self._refresh_movement_combos()
                
                self.status_bar.set_status(f"Όχημα {plate} διαγράφηκε επιτυχώς")
                log_user_action("Vehicle deleted", f"Plate: {plate}")
                messagebox.showinfo("✅ Επιτυχία", "Το όχημα διαγράφηκε επιτυχώς!")
                
            except Exception as e:
                logging.error(f"Error deleting vehicle: {e}")
                messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την διαγραφή: {str(e)}")

    def _clear_vehicle_form(self):
        """Clear vehicle form"""
        self.ent_plate.delete(0, tk.END)
        self.ent_brand.delete(0, tk.END)
        self.ent_vtype.delete(0, tk.END)
        if hasattr(self, 'ent_vpurpose'):
            self.ent_vpurpose.set("")
        self.photo_path_var.set("")
        self.photo_label.config(text="Δεν έχει επιλεγεί φωτογραφία")

    def _select_vehicle_from_tree(self, event=None):
        """Select vehicle from tree"""
        selection = self.tree_vehicles.selection()
        if selection:
            item = selection[0]
            values = self.tree_vehicles.item(item, "values")
            
            self.ent_plate.delete(0, tk.END)
            self.ent_plate.insert(0, values[0])
            self.ent_brand.delete(0, tk.END)
            self.ent_brand.insert(0, values[1])
            self.ent_vtype.delete(0, tk.END)
            self.ent_vtype.insert(0, values[2])
            if hasattr(self, 'ent_vpurpose'):
                self.ent_vpurpose.set(values[3])
            
            # Get photo path
            try:
                self.db.cursor.execute("SELECT photo_path FROM vehicles WHERE plate = ?", (values[0],))
                result = self.db.cursor.fetchone()
                if result and result[0]:
                    self.photo_path_var.set(result[0])
                    self.photo_label.config(text=os.path.basename(result[0]))
                else:
                    self.photo_path_var.set("")
                    self.photo_label.config(text="Δεν έχει επιλεγεί φωτογραφία")
            except Exception as e:
                logging.error(f"Error getting photo path: {e}")

    def _load_vehicles(self):
        """Load vehicles into tree with search filtering"""
        for item in self.tree_vehicles.get_children():
            self.tree_vehicles.delete(item)
        
        search_term = self.vehicles_search_var.get().upper() if hasattr(self, 'vehicles_search_var') else ""
        
        try:
            query = "SELECT plate, brand, vtype, purpose FROM vehicles"
            params = ()
            
            if search_term:
                query += " WHERE UPPER(plate) LIKE ?"
                params = (f"%{search_term}%",)
            
            query += " ORDER BY plate"
            
            self.db.cursor.execute(query, params)
            for row in self.db.cursor.fetchall():
                self.tree_vehicles.insert("", "end", values=row)
                
        except Exception as e:
            logging.error(f"Error loading vehicles: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη φόρτωση οχημάτων: {str(e)}")

    def _select_photo(self):
        """Select photo for vehicle"""
        file_path = filedialog.askopenfilename(
            title="Επιλογή Φωτογραφίας",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        
        if file_path:
            # Copy file to images directory
            ensure_dir(IMAGES_DIR)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(IMAGES_DIR, filename)
            
            try:
                import shutil
                shutil.copy2(file_path, dest_path)
                self.photo_path_var.set(dest_path)
                self.photo_label.config(text=filename)
                self.status_bar.set_status("Φωτογραφία επιλέχθηκε επιτυχώς")
            except Exception as e:
                logging.error(f"Error copying photo: {e}")
                messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την αντιγραφή: {str(e)}")

    def _view_photo(self):
        """View selected photo"""
        photo_path = self.photo_path_var.get()
        if not photo_path or not os.path.exists(photo_path):
            messagebox.showerror("❌ Σφάλμα", "Δεν υπάρχει φωτογραφία!")
            return
        
        try:
            if PIL_AVAILABLE:
                # Create photo viewer window
                photo_window = tk.Toplevel(self.root)
                photo_window.title("Προβολή Φωτογραφίας")
                photo_window.configure(bg=THEMES[self.current_theme]["bg"])
                
                # Load and resize image
                from PIL import Image, ImageTk
                pil_image = Image.open(photo_path)
                pil_image.thumbnail((600, 400), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(pil_image)
                
                label = tk.Label(photo_window, image=photo, bg=THEMES[self.current_theme]["bg"])
                label.image = photo  # Keep a reference
                label.pack(padx=10, pady=10)
            else:
                messagebox.showinfo("📷 Φωτογραφία", f"Φωτογραφία: {photo_path}")
        except Exception as e:
            logging.error(f"Error viewing photo: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την προβολή: {str(e)}")
    
    # Driver management methods
    def _add_driver(self):
        """Add a new driver with improved validation"""
        try:
            name = normalize_name(self.ent_name.get())
            surname = normalize_name(self.ent_surname.get())
            notes = self.ent_dnotes.get().strip()
            
            # Validate required fields
            required_fields = {
                "Όνομα": name,
                "Επώνυμο": surname
            }
            
            is_valid, error_msg = self.validate_required_fields(required_fields)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα Επικύρωσης", error_msg)
                return
            
            # Validate names
            is_valid, validated_name = DataValidator.is_valid_name(name)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", f"Όνομα: {validated_name}")
                return
                
            is_valid, validated_surname = DataValidator.is_valid_name(surname)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", f"Επώνυμο: {validated_surname}")
                return
            
            self.db.cursor.execute("""
                INSERT INTO drivers (name, surname, notes)
                VALUES (?, ?, ?)
            """, (validated_name, validated_surname, notes))
            
            self.db.conn.commit()
            self._clear_driver_form()
            self._load_drivers()
            self._refresh_movement_combos()
            self._load_fuel_combos()  # Update fuel combos
            
            self.status_bar.set_status(f"Οδηγός {validated_name} {validated_surname} προστέθηκε επιτυχώς")
            log_user_action("Driver added", f"Name: {validated_name} {validated_surname}")
            messagebox.showinfo("✅ Επιτυχία", "Ο οδηγός προστέθηκε επιτυχώς!")
            
        except Exception as e:
            logging.error(f"Error adding driver: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την προσθήκη: {str(e)}")

    def _update_driver(self):
        """Update selected driver"""
        selection = self.tree_drivers.selection()
        if not selection:
            messagebox.showerror("❌ Σφάλμα", "Παρακαλώ επιλέξτε οδηγό!")
            return
        
        try:
            item = selection[0]
            old_values = self.tree_drivers.item(item, "values")
            
            name = normalize_name(self.ent_name.get())
            surname = normalize_name(self.ent_surname.get())
            notes = self.ent_dnotes.get().strip()
            
            # Validate names
            is_valid, validated_name = DataValidator.is_valid_name(name)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", f"Όνομα: {validated_name}")
                return
                
            is_valid, validated_surname = DataValidator.is_valid_name(surname)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", f"Επώνυμο: {validated_surname}")
                return
            
            self.db.cursor.execute("""
                UPDATE drivers 
                SET name = ?, surname = ?, notes = ?
                WHERE name = ? AND surname = ?
            """, (validated_name, validated_surname, notes, old_values[0], old_values[1]))
            
            self.db.conn.commit()
            self._clear_driver_form()
            self._load_drivers()
            self._refresh_movement_combos()
            
            self.status_bar.set_status(f"Οδηγός {validated_name} {validated_surname} ενημερώθηκε επιτυχώς")
            log_user_action("Driver updated", f"Name: {validated_name} {validated_surname}")
            messagebox.showinfo("✅ Επιτυχία", "Ο οδηγός ενημερώθηκε επιτυχώς!")
            
        except Exception as e:
            logging.error(f"Error updating driver: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την ενημέρωση: {str(e)}")

    def _delete_driver(self):
        """Delete selected driver"""
        selection = self.tree_drivers.selection()
        if not selection:
            messagebox.showerror("❌ Σφάλμα", "Παρακαλώ επιλέξτε οδηγό!")
            return
        
        item = selection[0]
        values = self.tree_drivers.item(item, "values")
        driver_name = f"{values[0]} {values[1]}"
        
        if ConfirmDialog(
            self.root,
            "🗑️ Επιβεβαίωση Διαγραφής",
            f"Είστε σίγουρος ότι θέλετε να διαγράψετε τον οδηγό {driver_name};\n\nΑυτή η ενέργεια θα διαγράψει και όλες τις σχετικές κινήσεις και καύσιμα!"
        ).show():
            try:
                self.db.cursor.execute("DELETE FROM drivers WHERE name = ? AND surname = ?", (values[0], values[1]))
                self.db.conn.commit()
                self._clear_driver_form()
                self._load_drivers()
                self._refresh_movement_combos()
                
                self.status_bar.set_status(f"Οδηγός {driver_name} διαγράφηκε επιτυχώς")
                log_user_action("Driver deleted", f"Name: {driver_name}")
                messagebox.showinfo("✅ Επιτυχία", "Ο οδηγός διαγράφηκε επιτυχώς!")
                
            except Exception as e:
                logging.error(f"Error deleting driver: {e}")
                messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την διαγραφή: {str(e)}")

    def _clear_driver_form(self):
        """Clear driver form"""
        self.ent_name.delete(0, tk.END)
        self.ent_surname.delete(0, tk.END)
        self.ent_dnotes.delete(0, tk.END)

    def _select_driver_from_tree(self, event=None):
        """Select driver from tree"""
        selection = self.tree_drivers.selection()
        if selection:
            item = selection[0]
            values = self.tree_drivers.item(item, "values")
            
            self.ent_name.delete(0, tk.END)
            self.ent_name.insert(0, values[0])
            self.ent_surname.delete(0, tk.END)
            self.ent_surname.insert(0, values[1])
            self.ent_dnotes.delete(0, tk.END)
            self.ent_dnotes.insert(0, values[2])

    def _load_drivers(self):
        """Load drivers into tree with search filtering"""
        for item in self.tree_drivers.get_children():
            self.tree_drivers.delete(item)
        
        search_term = self.drivers_search_var.get().upper() if hasattr(self, 'drivers_search_var') else ""
        
        try:
            query = "SELECT name, surname, notes FROM drivers"
            params = ()
            
            if search_term:
                query += " WHERE UPPER(name || ' ' || surname) LIKE ?"
                params = (f"%{search_term}%",)
            
            query += " ORDER BY name, surname"
            
            self.db.cursor.execute(query, params)
            for row in self.db.cursor.fetchall():
                self.tree_drivers.insert("", "end", values=row)
                
        except Exception as e:
            logging.error(f"Error loading drivers: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη φόρτωση οδηγών: {str(e)}")
    
    # Fuel management methods
    def _add_fuel(self):
        """Add fuel record with improved validation"""
        try:
            date = self.fuel_date_var.get()
            driver = self.fuel_driver_combo.get()
            vehicle = self.fuel_vehicle_combo.get()
            liters_str = self.fuel_liters_var.get()
            mileage_str = self.fuel_mileage_var.get()
            cost_str = self.fuel_cost_var.get()
            pump_reading_str = self.fuel_pump_reading_var.get()
            
            # Validate required fields
            required_fields = {
                "Ημερομηνία": date,
                "Οδηγός": driver,
                "Όχημα": vehicle,
                "Λίτρα": liters_str
            }
            
            is_valid, error_msg = self.validate_required_fields(required_fields)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα Επικύρωσης", error_msg)
                return
            
            # Validate date
            if not validate_date(date):
                messagebox.showerror("❌ Σφάλμα", "Μη έγκυρη ημερομηνία! Χρησιμοποιήστε τη μορφή YYYY-MM-DD")
                return
            
            # Validate fuel amount
            is_valid, liters = DataValidator.is_valid_fuel(liters_str)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", liters)
                return
            
            # Validate mileage if provided
            mileage = None
            if mileage_str:
                is_valid, mileage = DataValidator.is_valid_km(mileage_str)
                if not is_valid:
                    messagebox.showerror("❌ Σφάλμα", mileage)
                    return
            
            # Validate cost if provided
            cost = 0.0
            if cost_str:
                try:
                    cost = float(cost_str)
                    if cost < 0:
                        messagebox.showerror("❌ Σφάλμα", "Το κόστος δεν μπορεί να είναι αρνητικό!")
                        return
                except ValueError:
                    messagebox.showerror("❌ Σφάλμα", "Το κόστος πρέπει να είναι έγκυρος αριθμός!")
                    return
            
            # Get IDs
            driver_id = self._get_driver_id(driver)
            vehicle_id = self._get_vehicle_id(vehicle)
            
            if not driver_id:
                messagebox.showerror("❌ Σφάλμα", "Μη έγκυρος οδηγός!")
                return
            
            if not vehicle_id:
                messagebox.showerror("❌ Σφάλμα", "Μη έγκυρο όχημα!")
                return
            
            # Check tank level
            self.db.cursor.execute("SELECT SUM(CASE WHEN type = 'fill' THEN liters ELSE -liters END) FROM tank")
            current_level = self.db.cursor.fetchone()[0] or 0
            
            if current_level < liters:
                if not ConfirmDialog(
                    self.root,
                    "⚠️ Προειδοποίηση Δεξαμενής",
                    f"Δεν υπάρχουν αρκετά καύσιμα στη δεξαμενή!\n\nΔιαθέσιμα: {current_level:.1f}L\nΑπαιτούνται: {liters:.1f}L\n\nΘέλετε να συνεχίσετε;"
                ).show():
                    return
            
            # Add fuel record
            self.db.cursor.execute("""
                INSERT INTO fuel (vehicle_id, driver_id, date, liters, mileage, cost)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vehicle_id, driver_id, date, liters, mileage, cost))
            
            # Update tank
            self.db.cursor.execute("""
                INSERT INTO tank (date, liters, type, notes)
                VALUES (?, ?, 'consume', ?)
            """, (date, liters, f"Ανεφοδιασμός {vehicle}"))
            
            # Update pump reading if provided
            if pump_reading_str:
                try:
                    new_pump_reading = float(pump_reading_str)
                    current_pump_reading = self.db.get_pump_reading()
                    
                    if new_pump_reading >= current_pump_reading:
                        calculated_liters = new_pump_reading - current_pump_reading
                        
                        # Check if pump liters match fuel liters (with small tolerance)
                        if abs(calculated_liters - liters) <= 1.0:  # 1L tolerance
                            self.db.update_pump_reading(
                                new_pump_reading, 
                                calculated_liters,
                                vehicle, 
                                driver,
                                f"Ανεφοδιασμός {vehicle} - {liters:.1f}L"
                            )
                        else:
                            logging.warning(f"Pump reading mismatch: pump={calculated_liters:.1f}L, fuel={liters:.1f}L")
                    else:
                        logging.warning(f"New pump reading ({new_pump_reading}) is less than current ({current_pump_reading})")
                        
                except ValueError:
                    logging.warning(f"Invalid pump reading: {pump_reading_str}")
            
            self.db.conn.commit()
            self._clear_fuel_form()
            self._load_fuel()
            self._update_tank_level()
            
            self.status_bar.set_status(f"Καύσιμο καταχωρήθηκε: {liters:.1f}L για {vehicle}")
            log_user_action("Fuel added", f"Vehicle: {vehicle}, Liters: {liters:.1f}")
            messagebox.showinfo("✅ Επιτυχία", "Το καύσιμο καταχωρήθηκε επιτυχώς!")
            
        except Exception as e:
            logging.error(f"Error adding fuel: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την καταχώρηση: {str(e)}")

    def _clear_fuel_form(self):
        """Clear fuel form"""
        self.fuel_driver_combo.set("")
        self.fuel_vehicle_combo.set("")
        self.fuel_liters_var.set("")
        self.fuel_mileage_var.set("")
        self.fuel_cost_var.set("")
        self.fuel_pump_reading_var.set("")

    def _refill_tank(self):
        """Refill tank dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("⛽ Ανεφοδιασμός Δεξαμενής")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg=THEMES[self.current_theme]["bg"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="⛽ Ανεφοδιασμός Δεξαμενής", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack(pady=(0, 20))
        
        # Current level info
        try:
            self.db.cursor.execute(
                "SELECT SUM(CASE WHEN type = 'fill' THEN liters ELSE -liters END) FROM tank"
            )
            current_level = self.db.cursor.fetchone()[0] or 0
            remaining_capacity = TANK_CAPACITY - current_level
            
            info_text = f"🔵 Τρέχον Επίπεδο: {current_level:.1f}L\n🛢️ Συνολική Χωρητικότητα: {TANK_CAPACITY:,.0f}L\n✨ Διαθέσιμος Χώρος: {remaining_capacity:.1f}L"
            info_label = tk.Label(main_frame, text=info_text, font=FONT_NORMAL,
                                 fg=THEMES[self.current_theme]["fg"],
                                 bg=THEMES[self.current_theme]["bg"], justify="left")
            info_label.pack(pady=(0, 20))
        except:
            current_level = 0
            remaining_capacity = TANK_CAPACITY
        
        # Input frame
        input_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="⛽ Λίτρα Ανεφοδιασμού:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        liters_var = tk.StringVar()
        liters_entry = tk.Entry(input_frame, textvariable=liters_var, font=FONT_NORMAL,
                               width=20, relief="flat", borderwidth=1, highlightthickness=1)
        liters_entry.pack(pady=(0, 10))
        liters_entry.focus()
        
        tk.Label(input_frame, text="📝 Σημειώσεις:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(10, 5))
        
        notes_var = tk.StringVar(value="Ανεφοδιασμός κεντρικής δεξαμενής")
        notes_entry = tk.Entry(input_frame, textvariable=notes_var, font=FONT_NORMAL,
                              width=20, relief="flat", borderwidth=1, highlightthickness=1)
        notes_entry.pack(pady=(0, 20))
        
        def confirm_refill():
            try:
                liters_str = liters_var.get()
                notes = notes_var.get() or "Ανεφοδιασμός δεξαμενής"
                
                if not liters_str:
                    messagebox.showerror("❌ Σφάλμα", "Παρακαλώ εισάγετε τα λίτρα!")
                    return
                
                liters = float(liters_str)
                if liters <= 0:
                    messagebox.showerror("❌ Σφάλμα", "Τα λίτρα πρέπει να είναι θετικός αριθμός!")
                    return
                
                if liters > remaining_capacity:
                    messagebox.showerror("❌ Σφάλμα", 
                                       f"Δεν χωράνε {liters:.1f}L!\nΜέγιστα διαθέσιμα: {remaining_capacity:.1f}L")
                    return
                
                # Add refill to tank
                self.db.cursor.execute("""
                    INSERT INTO tank (date, liters, type, notes)
                    VALUES (?, ?, 'fill', ?)
                """, (datetime.now().strftime("%Y-%m-%d"), liters, notes))
                
                self.db.conn.commit()
                self._update_tank_level()
                
                messagebox.showinfo("✅ Επιτυχία", f"Η δεξαμενή ανεφοδιάστηκε με {liters:.1f}L!")
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("❌ Σφάλμα", "Παρακαλώ εισάγετε έγκυρο αριθμό λίτρων!")
            except Exception as e:
                logging.error(f"Error refilling tank: {e}")
                messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τον ανεφοδιασμό: {str(e)}")
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        btn_frame.pack(pady=20)
        
        ModernButton(btn_frame, text="✅ Ανεφοδιασμός", style="success", 
                    command=confirm_refill).pack(side="left", padx=5)
        ModernButton(btn_frame, text="❌ Ακύρωση", style="danger", 
                    command=dialog.destroy).pack(side="left", padx=5)
        
        # Enter key binding
        dialog.bind('<Return>', lambda e: confirm_refill())

    def _show_tank_history(self):
        """Show tank history"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📋 Ιστορικό Δεξαμενής")
        dialog.geometry("700x500")
        dialog.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg=THEMES[self.current_theme]["bg"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="📋 Ιστορικό Κινήσεων Δεξαμενής", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack(pady=(0, 20))
        
        # Tree for history
        tree_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=("date", "type", "liters", "notes"), 
                           show="headings", height=15)
        
        # Configure columns
        tree.heading("date", text="📅 Ημερομηνία")
        tree.heading("type", text="🔄 Τύπος")
        tree.heading("liters", text="⛽ Λίτρα")
        tree.heading("notes", text="📝 Σημειώσεις")
        
        tree.column("date", width=120, anchor="center")
        tree.column("type", width=100, anchor="center")
        tree.column("liters", width=100, anchor="center")
        tree.column("notes", width=300, anchor="w")
        
        # Load data
        try:
            self.db.cursor.execute("""
                SELECT date, type, liters, notes 
                FROM tank 
                ORDER BY date DESC, id DESC
            """)
            
            for row in self.db.cursor.fetchall():
                type_display = "📈 Ανεφοδιασμός" if row[1] == 'fill' else "📉 Κατανάλωση"
                tree.insert("", "end", values=(
                    row[0],  # date
                    type_display,  # type
                    f"{row[2]:.1f}L",  # liters
                    row[3] or ""  # notes
                ))
        except Exception as e:
            logging.error(f"Error loading tank history: {e}")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        
        # Close button
        ModernButton(main_frame, text="❌ Κλείσιμο", style="secondary", 
                    command=dialog.destroy).pack(pady=20)

    def _get_current_pump_reading(self):
        """Get current pump reading and populate field"""
        try:
            current_reading = self.db.get_pump_reading()
            self.fuel_pump_reading_var.set(str(current_reading))
        except Exception as e:
            logging.error(f"Error getting pump reading: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την ανάκτηση μέτρησης: {str(e)}")

    def _update_pump_reading(self):
        """Update pump reading dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📊 Ενημέρωση Μετρητή Αντλίας")
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg=THEMES[self.current_theme]["bg"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="📊 Ενημέρωση Μετρητή Αντλίας", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack(pady=(0, 20))
        
        # Current reading info
        try:
            current_reading = self.db.get_pump_reading()
            info_text = f"🔵 Τρέχουσα Μέτρηση: {current_reading:,.0f} λίτρα"
            info_label = tk.Label(main_frame, text=info_text, font=FONT_NORMAL,
                                 fg=THEMES[self.current_theme]["fg"],
                                 bg=THEMES[self.current_theme]["bg"])
            info_label.pack(pady=(0, 20))
        except:
            current_reading = 0
        
        # Input frame
        input_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="📊 Νέα Μέτρηση:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(0, 5))
        
        new_reading_var = tk.StringVar()
        new_reading_entry = tk.Entry(input_frame, textvariable=new_reading_var, font=FONT_NORMAL,
                                    width=20, relief="flat", borderwidth=1, highlightthickness=1)
        new_reading_entry.pack(pady=(0, 10))
        new_reading_entry.focus()
        
        tk.Label(input_frame, text="📝 Σημειώσεις:", font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"], 
                fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", pady=(10, 5))
        
        notes_var = tk.StringVar(value="Ενημέρωση μετρητή αντλίας")
        notes_entry = tk.Entry(input_frame, textvariable=notes_var, font=FONT_NORMAL,
                              width=20, relief="flat", borderwidth=1, highlightthickness=1)
        notes_entry.pack(pady=(0, 20))
        
        def confirm_update():
            try:
                new_reading_str = new_reading_var.get()
                notes = notes_var.get() or "Ενημέρωση μετρητή"
                
                if not new_reading_str:
                    messagebox.showerror("❌ Σφάλμα", "Παρακαλώ εισάγετε τη νέα μέτρηση!")
                    return
                
                new_reading = float(new_reading_str)
                
                if new_reading < current_reading:
                    messagebox.showerror("❌ Σφάλμα", 
                                       f"Η νέα μέτρηση ({new_reading:,.0f}) δεν μπορεί να είναι μικρότερη από την τρέχουσα ({current_reading:,.0f})!")
                    return
                
                liters_dispensed = new_reading - current_reading
                
                if liters_dispensed > 0:
                    # Update pump reading
                    if self.db.update_pump_reading(new_reading, liters_dispensed, notes=notes):
                        self._update_pump_display()
                        messagebox.showinfo("✅ Επιτυχία", 
                                          f"Ο μετρητής ενημερώθηκε!\nΔιανομή: {liters_dispensed:,.1f}L")
                        dialog.destroy()
                    else:
                        messagebox.showerror("❌ Σφάλμα", "Σφάλμα κατά την ενημέρωση!")
                else:
                    messagebox.showwarning("⚠️ Προειδοποίηση", "Δεν υπάρχει αλλαγή στη μέτρηση!")
                
            except ValueError:
                messagebox.showerror("❌ Σφάλμα", "Παρακαλώ εισάγετε έγκυρο αριθμό!")
            except Exception as e:
                logging.error(f"Error updating pump reading: {e}")
                messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την ενημέρωση: {str(e)}")
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        btn_frame.pack(pady=20)
        
        ModernButton(btn_frame, text="✅ Ενημέρωση", style="success", 
                    command=confirm_update).pack(side="left", padx=5)
        ModernButton(btn_frame, text="❌ Ακύρωση", style="danger", 
                    command=dialog.destroy).pack(side="left", padx=5)
        
        # Enter key binding
        dialog.bind('<Return>', lambda e: confirm_update())

    def _show_pump_history(self):
        """Show pump history"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📋 Ιστορικό Αντλίας")
        dialog.geometry("800x500")
        dialog.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Center the dialog
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, bg=THEMES[self.current_theme]["bg"])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="📋 Ιστορικό Κινήσεων Αντλίας", 
                              font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                              bg=THEMES[self.current_theme]["bg"])
        title_label.pack(pady=(0, 20))
        
        # Tree for history
        tree_frame = tk.Frame(main_frame, bg=THEMES[self.current_theme]["bg"])
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=("date", "reading", "dispensed", "vehicle", "driver", "notes"), 
                           show="headings", height=15)
        
        # Configure columns
        tree.heading("date", text="📅 Ημερομηνία")
        tree.heading("reading", text="📊 Μέτρηση")
        tree.heading("dispensed", text="⛽ Διανομή")
        tree.heading("vehicle", text="🚗 Όχημα")
        tree.heading("driver", text="👤 Οδηγός")
        tree.heading("notes", text="📝 Σημειώσεις")
        
        tree.column("date", width=120, anchor="center")
        tree.column("reading", width=100, anchor="center")
        tree.column("dispensed", width=100, anchor="center")
        tree.column("vehicle", width=100, anchor="center")
        tree.column("driver", width=120, anchor="center")
        tree.column("notes", width=200, anchor="w")
        
        # Load data
        try:
            history = self.db.get_pump_history()
            for row in history:
                tree.insert("", "end", values=(
                    row[0],  # date
                    f"{row[1]:,.0f}",  # reading
                    f"{row[2]:.1f}L",  # liters_dispensed
                    row[3] or "",  # vehicle_plate
                    row[4] or "",  # driver_name
                    row[5] or ""  # notes
                ))
        except Exception as e:
            logging.error(f"Error loading pump history: {e}")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=v_scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        
        # Close button
        ModernButton(main_frame, text="❌ Κλείσιμο", style="secondary", 
                    command=dialog.destroy).pack(pady=20)

    def _update_pump_display(self):
        """Update pump reading display"""
        try:
            current_reading = self.db.get_pump_reading()
            self.pump_reading_label.config(
                text=f"📊 Τρέχουσα Μέτρηση: {current_reading:,.0f} λίτρα"
            )
        except Exception as e:
            logging.error(f"Error updating pump display: {e}")
            self.pump_reading_label.config(text="⚠️ Σφάλμα φόρτωσης μέτρησης")

    def _load_fuel(self):
        """Load fuel records with cost information"""
        for item in self.tree_fuel.get_children():
            self.tree_fuel.delete(item)
        
        try:
            self.db.cursor.execute("""
                SELECT f.date, d.name || ' ' || d.surname, v.plate, f.liters, f.mileage, f.cost
                FROM fuel f
                JOIN drivers d ON f.driver_id = d.id
                JOIN vehicles v ON f.vehicle_id = v.id
                ORDER BY f.date DESC, f.id DESC
            """)
            
            for row in self.db.cursor.fetchall():
                # Format the display values
                display_row = (
                    row[0],  # date
                    row[1],  # driver
                    row[2],  # vehicle
                    f"{row[3]:.1f}",  # liters
                    f"{row[4]:.0f}" if row[4] else "",  # mileage
                    format_currency(row[5]) if row[5] else "0.00 €"  # cost
                )
                self.tree_fuel.insert("", "end", values=display_row)
            
            # Update tank level display
            self._update_tank_level()
            # Update pump display
            self._update_pump_display()
                
        except Exception as e:
            logging.error(f"Error loading fuel: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη φόρτωση καυσίμων: {str(e)}")

    def _load_fuel_combos(self):
        """Load drivers and vehicles into fuel comboboxes"""
        try:
            # Load drivers
            self.db.cursor.execute("SELECT name, surname FROM drivers ORDER BY name, surname")
            drivers = [f"{row[0]} {row[1]}" for row in self.db.cursor.fetchall()]
            
            if hasattr(self, 'fuel_driver_combo'):
                self.fuel_driver_combo.set_values(drivers)
            
            # Load vehicles  
            self.db.cursor.execute("SELECT plate FROM vehicles ORDER BY plate")
            vehicles = [row[0] for row in self.db.cursor.fetchall()]
            
            if hasattr(self, 'fuel_vehicle_combo'):
                self.fuel_vehicle_combo.set_values(vehicles)
                
        except Exception as e:
            logging.error(f"Error loading fuel combos: {e}")
    
    # ===== PURPOSE MANAGEMENT METHODS =====
    
    def _load_purposes(self):
        """Load purposes into the tree"""
        try:
            # Clear existing items
            for item in self.tree_purposes.get_children():
                self.tree_purposes.delete(item)
            
            # Get search and filter criteria
            search_term = self.purposes_search_var.get().lower()
            category_filter = self.purpose_filter_var.get()
            show_inactive = self.show_inactive_var.get()
            
            # Get purposes from database
            category = None if category_filter == "all" else category_filter
            purposes = self.db.get_purposes(category=category, active_only=not show_inactive)
            
            for purpose in purposes:
                purpose_id, name, description, category, active = purpose
                
                # Apply search filter
                if search_term and search_term not in name.lower() and search_term not in (description or "").lower():
                    continue
                
                # Format data for display
                active_text = "✅ Ναι" if active else "❌ Όχι"
                
                self.tree_purposes.insert("", "end", iid=purpose_id, values=(
                    name, description or "", category, active_text
                ))
                
        except Exception as e:
            logging.error(f"Error loading purposes: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα κατά τη φόρτωση σκοπών: {e}")
    
    def _add_purpose(self):
        """Add a new purpose"""
        try:
            name = self.ent_purpose_name.get().strip()
            description = self.ent_purpose_description.get().strip()
            category = self.purpose_category_var.get()
            
            if not name:
                messagebox.showwarning("Προειδοποίηση", "Παρακαλώ εισάγετε όνομα σκοπού")
                return
            
            # Add to database
            purpose_id = self.db.add_purpose(name, description, category)
            
            if purpose_id:
                messagebox.showinfo("Επιτυχία", f"Ο σκοπός '{name}' προστέθηκε επιτυχώς")
                self._clear_purpose_form()
                self._load_purposes()
                self._update_purpose_combos()  # Update comboboxes in other tabs
            else:
                messagebox.showerror("Σφάλμα", f"Ο σκοπός '{name}' υπάρχει ήδη")
                
        except Exception as e:
            logging.error(f"Error adding purpose: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα κατά την προσθήκη σκοπού: {e}")
    
    def _update_purpose(self):
        """Update selected purpose"""
        try:
            selected_items = self.tree_purposes.selection()
            if not selected_items:
                messagebox.showwarning("Προειδοποίηση", "Παρακαλώ επιλέξτε έναν σκοπό για ενημέρωση")
                return
            
            purpose_id = selected_items[0]
            name = self.ent_purpose_name.get().strip()
            description = self.ent_purpose_description.get().strip()
            category = self.purpose_category_var.get()
            
            if not name:
                messagebox.showwarning("Προειδοποίηση", "Παρακαλώ εισάγετε όνομα σκοπού")
                return
            
            # Update in database
            if self.db.update_purpose(purpose_id, name=name, description=description, category=category):
                messagebox.showinfo("Επιτυχία", f"Ο σκοπός '{name}' ενημερώθηκε επιτυχώς")
                self._clear_purpose_form()
                self._load_purposes()
                self._update_purpose_combos()  # Update comboboxes in other tabs
            else:
                messagebox.showerror("Σφάλμα", "Σφάλμα κατά την ενημέρωση του σκοπού")
                
        except Exception as e:
            logging.error(f"Error updating purpose: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα κατά την ενημέρωση σκοπού: {e}")
    
    def _delete_purpose(self):
        """Deactivate selected purpose"""
        try:
            selected_items = self.tree_purposes.selection()
            if not selected_items:
                messagebox.showwarning("Προειδοποίηση", "Παρακαλώ επιλέξτε έναν σκοπό για απενεργοποίηση")
                return
            
            purpose_id = selected_items[0]
            purpose_data = self.tree_purposes.item(purpose_id)["values"]
            purpose_name = purpose_data[0]
            
            if messagebox.askyesno("Επιβεβαίωση", f"Θέλετε να απενεργοποιήσετε τον σκοπό '{purpose_name}';"):
                if self.db.delete_purpose(purpose_id):
                    messagebox.showinfo("Επιτυχία", f"Ο σκοπός '{purpose_name}' απενεργοποιήθηκε επιτυχώς")
                    self._clear_purpose_form()
                    self._load_purposes()
                    self._update_purpose_combos()  # Update comboboxes in other tabs
                else:
                    messagebox.showerror("Σφάλμα", "Σφάλμα κατά την απενεργοποίηση του σκοπού")
                    
        except Exception as e:
            logging.error(f"Error deleting purpose: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα κατά την απενεργοποίηση σκοπού: {e}")
    
    def _restore_purpose(self):
        """Restore selected purpose"""
        try:
            selected_items = self.tree_purposes.selection()
            if not selected_items:
                messagebox.showwarning("Προειδοποίηση", "Παρακαλώ επιλέξτε έναν σκοπό για επαναφορά")
                return
            
            purpose_id = selected_items[0]
            purpose_data = self.tree_purposes.item(purpose_id)["values"]
            purpose_name = purpose_data[0]
            
            if self.db.restore_purpose(purpose_id):
                messagebox.showinfo("Επιτυχία", f"Ο σκοπός '{purpose_name}' επαναφέρθηκε επιτυχώς")
                self._clear_purpose_form()
                self._load_purposes()
                self._update_purpose_combos()  # Update comboboxes in other tabs
            else:
                messagebox.showerror("Σφάλμα", "Σφάλμα κατά την επαναφορά του σκοπού")
                
        except Exception as e:
            logging.error(f"Error restoring purpose: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα κατά την επαναφορά σκοπού: {e}")
    
    def _clear_purpose_form(self):
        """Clear purpose form fields"""
        self.ent_purpose_name.delete(0, tk.END)
        self.ent_purpose_description.delete(0, tk.END)
        self.purpose_category_var.set("general")
        
        # Clear selection
        for item in self.tree_purposes.selection():
            self.tree_purposes.selection_remove(item)
    
    def _select_purpose_from_tree(self, event=None):
        """Select purpose from tree and populate form"""
        try:
            selected_items = self.tree_purposes.selection()
            if not selected_items:
                return
            
            purpose_id = selected_items[0]
            purpose_data = self.tree_purposes.item(purpose_id)["values"]
            
            # Clear form first
            self._clear_purpose_form()
            
            # Populate form
            self.ent_purpose_name.insert(0, purpose_data[0])  # name
            self.ent_purpose_description.insert(0, purpose_data[1])  # description
            self.purpose_category_var.set(purpose_data[2])  # category
            
        except Exception as e:
            logging.error(f"Error selecting purpose: {e}")
    
    def _update_purpose_combos(self):
        """Update purpose comboboxes in other tabs"""
        try:
            # Get active purposes
            purpose_names = self.db.get_purpose_names(active_only=True)
            
            # Update movement tab combobox
            if hasattr(self, 'mov_purpose_combobox'):
                self.mov_purpose_combobox.set_values(purpose_names)
            
            # Update vehicle tab combobox
            if hasattr(self, 'ent_vpurpose'):
                self.ent_vpurpose.set_values(purpose_names)
                
        except Exception as e:
            logging.error(f"Error updating purpose combos: {e}")
    
    # Export and reporting methods
    def _export_movements_csv(self):
        """Export movements to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=f"movements_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if filename:
                self.db.cursor.execute("""
              SELECT m.date, d.name || ' ' || d.surname as driver, v.plate, 
                  m.start_km, m.end_km, m.route, m.purpose,
                           (COALESCE(m.end_km, 0) - COALESCE(m.start_km, 0)) as total_km,
                           COALESCE(m.movement_number, 0) as movement_num
                    FROM movements m
                    JOIN drivers d ON m.driver_id = d.id
                    JOIN vehicles v ON m.vehicle_id = v.id
                    ORDER BY m.date DESC
                """)
                
                headers = ["Ημερομηνία", "Οδηγός", "Όχημα", "Χλμ Αναχ.", "Χλμ Επιστρ.", 
                          "Διαδρομή", "Σκοπός", "Σύνολο Χλμ", "Αρ. Κίνησης"]
                data = self.db.cursor.fetchall()
                
                if export_to_csv(data, headers, filename):
                    self.status_bar.set_status("Κινήσεις εξήχθησαν επιτυχώς")
                    
        except Exception as e:
            logging.error(f"Error exporting movements: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την εξαγωγή: {str(e)}")

    def _export_fuel_csv(self):
        """Export fuel to CSV"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=f"fuel_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if filename:
                self.db.cursor.execute("""
                    SELECT f.date, d.name || ' ' || d.surname, v.plate, f.liters, f.mileage, f.cost
                    FROM fuel f
                    JOIN drivers d ON f.driver_id = d.id
                    JOIN vehicles v ON f.vehicle_id = v.id
                    ORDER BY f.date DESC
                """)
                
                headers = ["Ημερομηνία", "Οδηγός", "Όχημα", "Λίτρα", "Χιλιόμετρα", "Κόστος"]
                data = self.db.cursor.fetchall()
                
                if export_to_csv(data, headers, filename):
                    self.status_bar.set_status("Καύσιμα εξήχθησαν επιτυχώς")
                    
        except Exception as e:
            logging.error(f"Error exporting fuel: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την εξαγωγή: {str(e)}")

    def _export_monthly_report_csv(self):
        """Export comprehensive monthly report to CSV"""
        try:
            month = int(self.month_var.get())
            year = int(self.year_var.get())
            
            data = self._get_monthly_data(month, year)
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialname=f"monthly_report_{year}_{month:02d}.csv"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Header
                    writer.writerow([f"ΜΗΝΙΑΙΑ ΑΝΑΦΟΡΑ - {month:02d}/{year}"])
                    writer.writerow([f"Δημιουργήθηκε: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
                    writer.writerow([])
                    
                    # Individual vehicle data
                    writer.writerow(["ΣΤΟΙΧΕΙΑ ΑΝΑ ΟΧΗΜΑ"])
                    writer.writerow([
                        "Πινακίδα", "Μάρκα", "Τύπος", "Κινήσεις", "Σύνολο Χλμ", 
                        "Ελάχιστα Χλμ", "Μέγιστα Χλμ", "Σύνολο Καυσίμων (L)", 
                        "Ανεφοδιασμοί", "Μέσος Όρος/Ανεφοδιασμό", "Απόδοση (χλμ/L)"
                    ])
                    
                    total_km = 0
                    total_fuel = 0
                    total_movements = 0
                    
                    for vehicle in data:
                        writer.writerow([
                            vehicle['plate'],
                            vehicle['brand'],
                            vehicle['type'],
                            vehicle['total_movements'],
                            f"{vehicle['total_km']:.1f}",
                            f"{vehicle['min_km']:.0f}",
                            f"{vehicle['max_km']:.0f}",
                            f"{vehicle['total_fuel']:.1f}",
                            vehicle['fuel_refills'],
                            f"{vehicle['avg_fuel_per_refill']:.1f}",
                            f"{vehicle['efficiency_km_per_liter']:.2f}"
                        ])
                        
                        total_km += vehicle['total_km']
                        total_fuel += vehicle['total_fuel']
                        total_movements += vehicle['total_movements']
                    
                    # Summary
                    writer.writerow([])
                    writer.writerow(["ΣΥΝΟΛΙΚΑ ΣΤΟΙΧΕΙΑ"])
                    writer.writerow(["Συνολικές Κινήσεις", total_movements])
                    writer.writerow(["Συνολικά Χιλιόμετρα", f"{total_km:.1f}"])
                    writer.writerow(["Συνολικά Καύσιμα", f"{total_fuel:.1f}"])
                    if total_fuel > 0:
                        writer.writerow(["Μέση Απόδοση", f"{total_km/total_fuel:.2f} χλμ/L"])
                
                messagebox.showinfo("✅ Επιτυχία", f"Η μηνιαία αναφορά εξήχθη σε: {filename}")
                self.status_bar.set_status("Μηνιαία αναφορά εξήχθη επιτυχώς")
                
        except Exception as e:
            logging.error(f"Error exporting monthly report: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την εξαγωγή: {str(e)}")

    def _export_monthly_report_excel(self):
        """Export comprehensive monthly report to Excel"""
        if not EXCEL_AVAILABLE:
            messagebox.showerror("❌ Σφάλμα", "Το Excel δεν είναι διαθέσιμο!")
            return
        
        try:
            from openpyxl import Workbook
            
            month = int(self.month_var.get())
            year = int(self.year_var.get())
            
            data = self._get_monthly_data(month, year)
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialname=f"monthly_report_{year}_{month:02d}.xlsx"
            )
            
            if filename:
                wb = Workbook()
                ws = wb.active
                ws.title = f"Αναφορά {month:02d}-{year}"
                
                # Header
                ws.append([f"ΜΗΝΙΑΙΑ ΑΝΑΦΟΡΑ - {month:02d}/{year}"])
                ws.append([f"Δημιουργήθηκε: {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
                ws.append([])
                
                # Individual vehicle data
                ws.append(["ΣΤΟΙΧΕΙΑ ΑΝΑ ΟΧΗΜΑ"])
                ws.append([
                    "Πινακίδα", "Μάρκα", "Τύπος", "Κινήσεις", "Σύνολο Χλμ", 
                    "Ελάχιστα Χλμ", "Μέγιστα Χλμ", "Σύνολο Καυσίμων (L)", 
                    "Ανεφοδιασμοί", "Μέσος Όρος/Ανεφοδιασμό", "Απόδοση (χλμ/L)"
                ])
                
                total_km = 0
                total_fuel = 0
                total_movements = 0
                
                for vehicle in data:
                    ws.append([
                        vehicle['plate'],
                        vehicle['brand'],
                        vehicle['type'],
                        vehicle['total_movements'],
                        vehicle['total_km'],
                        vehicle['min_km'],
                        vehicle['max_km'],
                        vehicle['total_fuel'],
                        vehicle['fuel_refills'],
                        vehicle['avg_fuel_per_refill'],
                        vehicle['efficiency_km_per_liter']
                    ])
                    
                    total_km += vehicle['total_km']
                    total_fuel += vehicle['total_fuel']
                    total_movements += vehicle['total_movements']
                
                # Summary
                ws.append([])
                ws.append(["ΣΥΝΟΛΙΚΑ ΣΤΟΙΧΕΙΑ"])
                ws.append(["Συνολικές Κινήσεις", total_movements])
                ws.append(["Συνολικά Χιλιόμετρα", total_km])
                ws.append(["Συνολικά Καύσιμα", total_fuel])
                if total_fuel > 0:
                    ws.append(["Μέση Απόδοση", f"{total_km/total_fuel:.2f} χλμ/L"])
                
                wb.save(filename)
                messagebox.showinfo("✅ Επιτυχία", f"Η μηνιαία αναφορά εξήχθη σε: {filename}")
                self.status_bar.set_status("Μηνιαία αναφορά Excel εξήχθη επιτυχώς")
                
        except Exception as e:
            logging.error(f"Error exporting monthly Excel report: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την εξαγωγή: {str(e)}")

    def _export_excel(self):
        """Export comprehensive data to Excel"""
        if not EXCEL_AVAILABLE:
            messagebox.showerror("❌ Σφάλμα", "Το Excel δεν είναι διαθέσιμο!")
            return
        
        try:
            from openpyxl import Workbook
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialname=f"fleet_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            
            if filename:
                wb = Workbook()
                
                # Movements sheet
                ws1 = wb.active
                ws1.title = "Κινήσεις"
                ws1.append(["Ημερομηνία", "Οδηγός", "Όχημα", "Χλμ Αναχ.", "Χλμ Επιστρ.", "Διαδρομή", "Σκοπός", "Σύνολο Χλμ", "Αρ. Κίνησης"])
                
                self.db.cursor.execute("""
                    SELECT m.date, d.name || ' ' || d.surname, v.plate, 
                           m.start_km, m.end_km, m.route, m.purpose,
                           (COALESCE(m.end_km, 0) - COALESCE(m.start_km, 0)),
                           COALESCE(m.movement_number, 0)
                    FROM movements m
                    JOIN drivers d ON m.driver_id = d.id
                    JOIN vehicles v ON m.vehicle_id = v.id
                    ORDER BY m.date DESC
                """)
                
                for row in self.db.cursor.fetchall():
                    ws1.append(row)
                
                # Fuel sheet
                ws2 = wb.create_sheet("Καύσιμα")
                ws2.append(["Ημερομηνία", "Οδηγός", "Όχημα", "Λίτρα", "Χιλιόμετρα", "Κόστος"])
                
                self.db.cursor.execute("""
                    SELECT f.date, d.name || ' ' || d.surname, v.plate, f.liters, f.mileage, f.cost
                    FROM fuel f
                    JOIN drivers d ON f.driver_id = d.id
                    JOIN vehicles v ON f.vehicle_id = v.id
                    ORDER BY f.date DESC
                """)
                
                for row in self.db.cursor.fetchall():
                    ws2.append(row)
                
                # Vehicles sheet
                ws3 = wb.create_sheet("Οχήματα")
                ws3.append(["Πινακίδα", "Μάρκα", "Τύπος", "Σημειώσεις"])
                
                self.db.cursor.execute("SELECT plate, brand, vtype, purpose FROM vehicles ORDER BY plate")
                for row in self.db.cursor.fetchall():
                    ws3.append(row)
                
                # Drivers sheet
                ws4 = wb.create_sheet("Οδηγοί")
                ws4.append(["Όνομα", "Επώνυμο", "Σημειώσεις"])
                
                self.db.cursor.execute("SELECT name, surname, notes FROM drivers ORDER BY name, surname")
                for row in self.db.cursor.fetchall():
                    ws4.append(row)
                
                wb.save(filename)
                messagebox.showinfo("✅ Επιτυχία", f"Τα δεδομένα εξήχθησαν σε: {filename}")
                self.status_bar.set_status("Γενική αναφορά Excel εξήχθη επιτυχώς")
                
        except Exception as e:
            logging.error(f"Error exporting Excel: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την εξαγωγή: {str(e)}")

    def _get_monthly_data(self, month, year):
        """Get comprehensive monthly data for vehicles"""
        month_str = f"{year}-{month:02d}"
        
        # Get movements data for the month
        movements_query = """
            SELECT v.plate, v.brand, v.vtype,
                   COUNT(m.id) as total_movements,
                   SUM(COALESCE(m.end_km, 0) - COALESCE(m.start_km, 0)) as total_km,
                   MIN(m.start_km) as min_km,
                   MAX(COALESCE(m.end_km, m.start_km)) as max_km
            FROM vehicles v
            LEFT JOIN movements m ON v.id = m.vehicle_id 
                AND m.date LIKE ?
                AND m.end_km IS NOT NULL
            GROUP BY v.id, v.plate, v.brand, v.vtype
            ORDER BY v.plate
        """
        
        # Get fuel data for the month
        fuel_query = """
            SELECT v.plate,
                   SUM(f.liters) as total_fuel,
                   COUNT(f.id) as fuel_refills,
                   AVG(f.liters) as avg_fuel_per_refill
            FROM vehicles v
            LEFT JOIN fuel f ON v.id = f.vehicle_id 
                AND f.date LIKE ?
            GROUP BY v.id, v.plate
            ORDER BY v.plate
        """
        
        self.db.cursor.execute(movements_query, (f"{month_str}%",))
        movements_data = {row[0]: row for row in self.db.cursor.fetchall()}
        
        self.db.cursor.execute(fuel_query, (f"{month_str}%",))
        fuel_data = {row[0]: row for row in self.db.cursor.fetchall()}
        
        # Combine data
        combined_data = []
        for plate in movements_data:
            movement_row = movements_data[plate]
            fuel_row = fuel_data.get(plate, (plate, 0, 0, 0))
            
            # Calculate efficiency (km per liter)
            efficiency = 0
            if fuel_row[1] > 0 and movement_row[4] > 0:
                efficiency = movement_row[4] / fuel_row[1]
            
            combined_row = {
                'plate': plate,
                'brand': movement_row[1],
                'type': movement_row[2],
                'total_movements': movement_row[3],
                'total_km': movement_row[4] or 0,
                'min_km': movement_row[5] or 0,
                'max_km': movement_row[6] or 0,
                'total_fuel': fuel_row[1] or 0,
                'fuel_refills': fuel_row[2] or 0,
                'avg_fuel_per_refill': fuel_row[3] or 0,
                'efficiency_km_per_liter': efficiency
            }
            combined_data.append(combined_row)
        
        return combined_data

    def _update_statistics(self):
        """Update the statistics display"""
        try:
            self.stats_text.delete(1.0, tk.END)
            
            # Current month data
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            stats_content = f"ΣΤΑΤΙΣΤΙΚΑ ΣΤΟΙΧΕΙΑ - {current_month:02d}/{current_year}\n"
            stats_content += "=" * 50 + "\n\n"
            
            # Total vehicles
            self.db.cursor.execute("SELECT COUNT(*) FROM vehicles")
            total_vehicles = self.db.cursor.fetchone()[0]
            stats_content += f"Συνολικά Οχήματα: {total_vehicles}\n"
            
            # Total drivers
            self.db.cursor.execute("SELECT COUNT(*) FROM drivers")
            total_drivers = self.db.cursor.fetchone()[0]
            stats_content += f"Συνολικοί Οδηγοί: {total_drivers}\n\n"
            
            # Current month movements
            month_str = f"{current_year}-{current_month:02d}"
            self.db.cursor.execute("""
                SELECT COUNT(*) FROM movements 
                WHERE date LIKE ? AND end_km IS NOT NULL
            """, (f"{month_str}%",))
            month_movements = self.db.cursor.fetchone()[0]
            stats_content += f"Κινήσεις τρέχοντος μήνα: {month_movements}\n"
            
            # Current month kilometers
            self.db.cursor.execute("""
                SELECT SUM(COALESCE(end_km, 0) - COALESCE(start_km, 0)) 
                FROM movements 
                WHERE date LIKE ? AND end_km IS NOT NULL
            """, (f"{month_str}%",))
            month_km = self.db.cursor.fetchone()[0] or 0
            stats_content += f"Χιλιόμετρα τρέχοντος μήνα: {month_km:.1f} χλμ\n"
            
            # Current month fuel
            self.db.cursor.execute("""
                SELECT SUM(liters) FROM fuel 
                WHERE date LIKE ?
            """, (f"{month_str}%",))
            month_fuel = self.db.cursor.fetchone()[0] or 0
            stats_content += f"Καύσιμα τρέχοντος μήνα: {month_fuel:.1f} L\n\n"
            
            # Active movements (not returned)
            self.db.cursor.execute("SELECT COUNT(*) FROM movements WHERE end_km IS NULL")
            active_movements = self.db.cursor.fetchone()[0]
            stats_content += f"Ενεργές κινήσεις (δεν έχουν επιστρέψει): {active_movements}\n"
            
            # Tank level
            self.db.cursor.execute("SELECT SUM(CASE WHEN type = 'fill' THEN liters ELSE -liters END) FROM tank")
            tank_level = self.db.cursor.fetchone()[0] or 0
            stats_content += f"Επίπεδο δεξαμενής: {tank_level:.1f} L\n\n"
            
            # Top 5 vehicles by distance this month
            stats_content += "ΤΟΠ 5 ΟΧΗΜΑΤΑ (ΧΙΛΙΟΜΕΤΡΑ ΜΗΝΑ):\n"
            stats_content += "-" * 30 + "\n"
            
            self.db.cursor.execute("""
                SELECT v.plate, COALESCE(SUM(m.end_km - m.start_km), 0) as total_km
                FROM vehicles v
                LEFT JOIN movements m ON v.id = m.vehicle_id 
                    AND m.date LIKE ? AND m.end_km IS NOT NULL
                GROUP BY v.id, v.plate
                ORDER BY total_km DESC
                LIMIT 5
            """, (f"{month_str}%",))
            
            for i, (plate, km) in enumerate(self.db.cursor.fetchall(), 1):
                stats_content += f"{i}. {plate}: {(km or 0):.1f} χλμ\n"
            
            self.stats_text.insert(tk.END, stats_content)
            
        except Exception as e:
            logging.error(f"Error updating statistics: {e}")
            self.stats_text.insert(tk.END, f"Σφάλμα στην ανάκτηση στατιστικών: {str(e)}")
    
    # Context menu methods for vehicles
    def _show_vehicle_context_menu(self, event):
        """Show context menu for vehicle right-click"""
        item = self.tree_vehicles.identify_row(event.y)
        if item:
            self.tree_vehicles.selection_set(item)
            self.vehicle_context_menu.post(event.x_root, event.y_root)

    def _get_selected_vehicle_plate(self):
        """Get the plate of the currently selected vehicle"""
        selection = self.tree_vehicles.selection()
        if not selection:
            messagebox.showwarning("⚠️ Προσοχή", "Παρακαλώ επιλέξτε ένα όχημα!")
            return None
        
        item = selection[0]
        values = self.tree_vehicles.item(item, 'values')
        return values[0] if values else None

    def _show_vehicle_history(self):
        """Show movement history for selected vehicle"""
        plate = self._get_selected_vehicle_plate()
        if not plate:
            return

        history_window = tk.Toplevel(self.root)
        history_window.title(f"Ιστορικό Κινήσεων - {plate}")
        history_window.geometry("900x600")
        history_window.configure(bg=THEMES[self.current_theme]["bg"])

        title_frame = tk.Frame(history_window, bg=THEMES[self.current_theme]["bg"])
        title_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(
            title_frame,
            text=f"📋 Ιστορικό Κινήσεων: {plate}",
            font=FONT_TITLE,
            fg=THEMES[self.current_theme]["accent"],
            bg=THEMES[self.current_theme]["bg"],
        ).pack()

        tree_frame = tk.Frame(history_window, bg=THEMES[self.current_theme]["bg"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tree = ttk.Treeview(
            tree_frame,
            columns=("date", "driver", "movement_num", "start_km", "end_km", "total_km", "route", "purpose"),
            show="headings",
        )

        for col, text in [
            ("date", "Ημερομηνία"),
            ("driver", "Οδηγός"),
            ("movement_num", "Αρ. Κίνησης"),
            ("start_km", "Χλμ Αναχ."),
            ("end_km", "Χλμ Επιστρ."),
            ("total_km", "Σύνολο Χλμ"),
            ("route", "Διαδρομή"),
            ("purpose", "Σκοπός"),
        ]:
            tree.heading(col, text=text)
            tree.column(col, width=100, anchor="center")

        tree.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        try:
            self.db.cursor.execute(
                """
                SELECT m.date, d.name || ' ' || d.surname, COALESCE(m.movement_number, 0),
                       m.start_km, m.end_km,
                       (COALESCE(m.end_km, 0) - COALESCE(m.start_km, 0)) as total_km,
                       m.route, m.purpose
                FROM movements m
                JOIN drivers d ON m.driver_id = d.id
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE v.plate = ?
                ORDER BY m.date DESC, m.id DESC
                """,
                (plate,),
            )
            for row in self.db.cursor.fetchall():
                formatted_row = (
                    row[0],
                    row[1],
                    f"{row[2]:04d}" if row[2] > 0 else "---",
                    f"{row[3]:.0f}" if row[3] else "",
                    f"{row[4]:.0f}" if row[4] else "Δεν επέστρεψε",
                    f"{row[5]:.1f}" if row[5] > 0 else "",
                    row[6] or "",
                    row[7] or "",
                )
                tree.insert("", "end", values=formatted_row)
        except Exception as e:
            logging.error(f"Error loading vehicle history: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα στην ανάκτηση δεδομένων: {str(e)}")

        stats_frame = tk.Frame(history_window, bg=THEMES[self.current_theme]["bg"])
        stats_frame.pack(fill="x", padx=10, pady=5)

        try:
            self.db.cursor.execute(
                """
                SELECT COUNT(*) as total_movements,
                       SUM(COALESCE(end_km, 0) - COALESCE(start_km, 0)) as total_km,
                       AVG(COALESCE(end_km, 0) - COALESCE(start_km, 0)) as avg_km
                FROM movements m
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE v.plate = ? AND m.end_km IS NOT NULL
                """,
                (plate,),
            )
            result = self.db.cursor.fetchone()
            total_movements = result[0] or 0
            total_km = result[1] or 0
            avg_km = result[2] or 0

            stats_text = (
                f"📊 Σύνολο Κινήσεων: {total_movements} | Σύνολο Χιλιόμετρα: {total_km:.1f} χλμ | "
                f"Μέσος Όρος: {avg_km:.1f} χλμ/κίνηση"
            )
            tk.Label(
                stats_frame,
                text=stats_text,
                font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"],
                fg=THEMES[self.current_theme]["fg"],
            ).pack()
        except Exception as e:
            logging.error(f"Error calculating vehicle statistics: {e}")
            tk.Label(
                stats_frame,
                text="Σφάλμα στον υπολογισμό στατιστικών",
                fg=THEMES[self.current_theme]["danger"],
                bg=THEMES[self.current_theme]["bg"],
            ).pack()

    def _show_vehicle_fuel_history(self):
        """Show fuel history for selected vehicle"""
        plate = self._get_selected_vehicle_plate()
        if not plate:
            return
        
        # Create fuel history window
        fuel_window = tk.Toplevel(self.root)
        fuel_window.title(f"Ιστορικό Καυσίμων - {plate}")
        fuel_window.geometry("800x500")
        fuel_window.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Title
        title_frame = tk.Frame(fuel_window, bg=THEMES[self.current_theme]["bg"])
        title_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(title_frame, text=f"⛽ Ιστορικό Καυσίμων: {plate}", 
                font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                bg=THEMES[self.current_theme]["bg"]).pack()
        
        # Create treeview for fuel records
        tree_frame = tk.Frame(fuel_window, bg=THEMES[self.current_theme]["bg"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        fuel_tree = ttk.Treeview(tree_frame, columns=("date", "driver", "liters", "mileage", "cost"), show="headings")
        
        fuel_tree.heading("date", text="Ημερομηνία")
        fuel_tree.heading("driver", text="Οδηγός")
        fuel_tree.heading("liters", text="Λίτρα")
        fuel_tree.heading("mileage", text="Χιλιόμετρα")
        fuel_tree.heading("cost", text="Κόστος")
        
        for col in fuel_tree["columns"]:
            fuel_tree.column(col, width=150, anchor="center")
        
        fuel_tree.pack(fill="both", expand=True)
        
        # Add scrollbar
        fuel_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=fuel_tree.yview)
        fuel_tree.configure(yscrollcommand=fuel_scrollbar.set)
        fuel_scrollbar.pack(side="right", fill="y")
        
        # Load fuel data
        try:
            self.db.cursor.execute("""
                SELECT f.date, d.name || ' ' || d.surname, f.liters, f.mileage, f.cost
                FROM fuel f
                JOIN drivers d ON f.driver_id = d.id
                JOIN vehicles v ON f.vehicle_id = v.id
                WHERE v.plate = ?
                ORDER BY f.date DESC
            """, (plate,))
            
            total_fuel = 0
            total_cost = 0
            for row in self.db.cursor.fetchall():
                display_row = (
                    row[0], row[1], f"{row[2]:.1f}", 
                    f"{row[3]:.0f}" if row[3] else "",
                    format_currency(row[4]) if row[4] else "0.00 €"
                )
                fuel_tree.insert("", "end", values=display_row)
                total_fuel += row[2]
                total_cost += row[4] if row[4] else 0
                
            # Statistics
            stats_frame = tk.Frame(fuel_window, bg=THEMES[self.current_theme]["bg"])
            stats_frame.pack(fill="x", padx=10, pady=5)
            stats_text = f"📊 Συνολικά Καύσιμα: {total_fuel:.1f} λίτρα | Συνολικό Κόστος: {format_currency(total_cost)}"
            tk.Label(stats_frame, text=stats_text, font=FONT_NORMAL,
                    bg=THEMES[self.current_theme]["bg"], 
                    fg=THEMES[self.current_theme]["fg"]).pack()
                    
        except Exception as e:
            logging.error(f"Error loading vehicle fuel history: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα στην ανάκτηση δεδομένων: {str(e)}")

    def _show_vehicle_statistics(self):
        """Show comprehensive statistics for selected vehicle"""
        plate = self._get_selected_vehicle_plate()
        if not plate:
            return
        
        # Create statistics window
        stats_window = tk.Toplevel(self.root)
        stats_window.title(f"Στατιστικά Οχήματος - {plate}")
        stats_window.geometry("600x500")
        stats_window.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Title
        title_frame = tk.Frame(stats_window, bg=THEMES[self.current_theme]["bg"])
        title_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(title_frame, text=f"📈 Στατιστικά: {plate}", 
                font=FONT_TITLE, fg=THEMES[self.current_theme]["accent"],
                bg=THEMES[self.current_theme]["bg"]).pack()
        
        # Text widget for statistics
        text_frame = tk.Frame(stats_window, bg=THEMES[self.current_theme]["bg"])
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        stats_text = tk.Text(text_frame, font=("Courier", 10), wrap=tk.WORD,
                            bg=THEMES[self.current_theme]["entry_bg"], 
                            fg=THEMES[self.current_theme]["fg"],
                            relief="flat", borderwidth=1)
        stats_text.pack(fill="both", expand=True)
        
        # Add scrollbar
        text_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=stats_text.yview)
        stats_text.configure(yscrollcommand=text_scrollbar.set)
        text_scrollbar.pack(side="right", fill="y")
        
        try:
            # Get vehicle info
            self.db.cursor.execute("SELECT brand, vtype, purpose FROM vehicles WHERE plate = ?", (plate,))
            vehicle_info = self.db.cursor.fetchone()
            
            stats_content = f"ΣΤΑΤΙΣΤΙΚΑ ΟΧΗΜΑΤΟΣ: {plate}\n"
            stats_content += "=" * 50 + "\n\n"
            
            if vehicle_info:
                stats_content += f"Μάρκα: {vehicle_info[0] or 'Δεν έχει οριστεί'}\n"
                stats_content += f"Τύπος: {vehicle_info[1] or 'Δεν έχει οριστεί'}\n"
                stats_content += f"Σκοπός: {vehicle_info[2] or 'Δεν έχει οριστεί'}\n\n"
            
            # Movement statistics
            self.db.cursor.execute("""
                SELECT COUNT(*) as total_movements,
                       SUM(COALESCE(end_km, 0) - COALESCE(start_km, 0)) as total_km,
                       AVG(COALESCE(end_km, 0) - COALESCE(start_km, 0)) as avg_km,
                       MIN(start_km) as min_km,
                       MAX(COALESCE(end_km, start_km)) as max_km
                FROM movements m
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE v.plate = ? AND m.end_km IS NOT NULL
            """, (plate,))
            movement_stats = self.db.cursor.fetchone()
            if movement_stats:
                total_movements = movement_stats[0] or 0
                total_km = movement_stats[1] or 0
                avg_km = movement_stats[2] or 0
                min_km = movement_stats[3] or 0
                max_km = movement_stats[4] or 0
                stats_content += f"Συνολικές Κινήσεις (ολοκληρωμένες): {total_movements}\n"
                stats_content += f"Συνολικά Χιλιόμετρα: {total_km:.1f} χλμ\n"
                stats_content += f"Μέσος Όρος Χλμ/Κίνηση: {avg_km:.1f} χλμ\n"
                stats_content += f"Από Χλμ: {min_km:.0f} έως {max_km:.0f}\n\n"
            # Active movements (not returned)
            self.db.cursor.execute("""
                SELECT COUNT(*) FROM movements m
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE v.plate = ? AND m.end_km IS NULL
            """, (plate,))
            active_movements = self.db.cursor.fetchone()[0] or 0
            stats_content += f"Ενεργές κινήσεις: {active_movements}\n\n"

            stats_text.insert(tk.END, stats_content)
        except Exception as e:
            logging.error(f"Error calculating vehicle statistics: {e}")
            stats_text.insert(tk.END, f"Σφάλμα στατιστικών: {e}")

        # End of statistics window creation

    def _view_vehicle_photo_from_tree(self):
        """View photo of selected vehicle from tree"""
        plate = self._get_selected_vehicle_plate()
        if not plate:
            return
        
        try:
            # Get vehicle photo path from database
            self.db.cursor.execute("SELECT photo_path FROM vehicles WHERE plate = ?", (plate,))
            result = self.db.cursor.fetchone()
            
            if not result or not result[0]:
                messagebox.showinfo("📷 Φωτογραφία", f"Δεν υπάρχει φωτογραφία για το όχημα {plate}")
                return
            
            photo_path = result[0]
            if not os.path.exists(photo_path):
                messagebox.showerror("❌ Σφάλμα", f"Η φωτογραφία δεν βρέθηκε στο δίσκο: {photo_path}")
                return
            
            # Create photo viewer window
            if PIL_AVAILABLE:
                photo_window = tk.Toplevel(self.root)
                photo_window.title(f"Φωτογραφία Οχήματος - {plate}")
                photo_window.configure(bg=THEMES[self.current_theme]["bg"])
                
                # Load and resize image
                from PIL import Image, ImageTk
                pil_image = Image.open(photo_path)
                pil_image.thumbnail((600, 400), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(pil_image)
                
                label = tk.Label(photo_window, image=photo, bg=THEMES[self.current_theme]["bg"])
                label.image = photo  # Keep a reference
                label.pack(padx=10, pady=10)
                
                # Add vehicle info
                info_label = tk.Label(
                    photo_window, 
                    text=f"Όχημα: {plate}",
                    font=FONT_NORMAL,
                    bg=THEMES[self.current_theme]["bg"],
                    fg=THEMES[self.current_theme]["fg"]
                )
                info_label.pack(pady=5)
            else:
                messagebox.showinfo("📷 Φωτογραφία", f"Φωτογραφία οχήματος {plate}: {photo_path}")
                
        except Exception as e:
            logging.error(f"Error viewing vehicle photo: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την προβολή φωτογραφίας: {str(e)}")

    def _add_movement(self):
        """Add new movement with improved validation"""
        try:
            # Get form data
            date = self.mov_date_var.get()
            driver = self.mov_driver_combo.get()
            vehicle = self.mov_vehicle_combo.get()
            start_km = self.mov_start_km_var.get()
            route = self.mov_route_entry.get()
            purpose = self.mov_purpose_combobox.get() if hasattr(self, 'mov_purpose_combobox') else ""
            
            # Validate required fields
            required_fields = {
                "Ημερομηνία": date,
                "Οδηγός": driver,
                "Όχημα": vehicle,
                "Χιλιόμετρα Αναχώρησης": start_km,
                "Σκοπός": purpose
            }
            
            is_valid, error_msg = self.validate_required_fields(required_fields)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα Επικύρωσης", error_msg)
                return
            
            # Validate date format
            if not validate_date(date):
                messagebox.showerror("❌ Σφάλμα", "Μη έγκυρη ημερομηνία! Χρησιμοποιήστε τη μορφή YYYY-MM-DD")
                return
            
            # Validate kilometers
            is_valid, km_value = DataValidator.is_valid_km(start_km)
            if not is_valid:
                messagebox.showerror("❌ Σφάλμα", km_value)
                return
            
            # Get IDs
            driver_id = self._get_driver_id(driver)
            vehicle_id = self._get_vehicle_id(vehicle)
            
            if not driver_id:
                messagebox.showerror("❌ Σφάλμα", "Μη έγκυρος οδηγός!")
                return
            
            if not vehicle_id:
                messagebox.showerror("❌ Σφάλμα", "Μη έγκυρο όχημα!")
                return

            last_vehicle_km = self._get_last_vehicle_km(vehicle_id)
            if last_vehicle_km is not None and km_value < last_vehicle_km:
                messagebox.showerror(
                    "❌ Σφάλμα Χιλιομέτρων",
                    f"Τα χλμ αναχώρησης ({km_value}) δεν μπορεί να είναι μικρότερα "
                    f"από τα τελευταία χλμ του οχήματος ({last_vehicle_km})."
                )
                return
            
            # Check if vehicle is already active
            if self._is_vehicle_active(vehicle_id):
                if not ConfirmDialog(
                    self.root,
                    "⚠️ Προειδοποίηση",
                    f"Το όχημα {vehicle} έχει ήδη ενεργή κίνηση!\nΘέλετε να συνεχίσετε;"
                ).show():
                    return
            
            # Get movement number
            movement_number = self.db.get_next_movement_number()
            
            # Insert movement
            self.db.cursor.execute("""
                INSERT INTO movements (movement_number, vehicle_id, driver_id, date, start_km, route, purpose)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (movement_number, vehicle_id, driver_id, date, km_value, route, purpose))
            
            self.db.conn.commit()
            
            # Clear form
            self._clear_movement_form()
            
            # Refresh data immediately
            self._load_movements()
            
            # Update status
            self.status_bar.set_status(f"Κίνηση #{movement_number:04d} δημιουργήθηκε επιτυχώς")
            
            log_user_action("Movement created", f"Movement #{movement_number:04d} for vehicle {vehicle}")
            
            # Ask user if they want to print the document
            if ConfirmDialog(
                self.root,
                "️ Εκτύπωση Εγγράφου",
                f"Η κίνηση #{movement_number:04d} καταχωρήθηκε επιτυχώς!\n\n"
                f"Θέλετε να εκτυπώσετε το έγγραφο κίνησης;"
            ).show():
                self._generate_and_print_movement_document(movement_number)
            
        except Exception as e:
            logging.error(f"Error adding movement: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την καταχώρηση κίνησης:\n{str(e)}")

    def _generate_and_print_movement_document(self, movement_number):
        """Generate and open a PDF movement order for printing."""
        try:
            if not REPORTLAB_AVAILABLE:
                messagebox.showerror(
                    "❌ Σφάλμα",
                    "Δεν είναι εγκατεστημένο το reportlab.\n\n"
                    "Τρέξτε: pip install -r requirements.txt"
                )
                return

            movement = self._get_movement_document_data(movement_number)
            if not movement:
                messagebox.showerror("❌ Σφάλμα", f"Δεν βρέθηκε κίνηση με αριθμό {movement_number}.")
                return
            
            # Extract year and month from date (format: YYYY-MM-DD)
            date_parts = movement["date"].split('-')
            year = date_parts[0]
            month = date_parts[1]
            
            # Create year and month directories
            year_dir = os.path.join(MOVEMENTS_DIR, year)
            month_dir = os.path.join(year_dir, month)
            
            # Ensure directories exist
            os.makedirs(month_dir, exist_ok=True)
            
            # Save to organized file structure
            safe_plate = "".join(ch if ch.isalnum() else "_" for ch in movement["vehicle"])
            filename = f"entoli_kinisis_{movement_number:04d}_{safe_plate}_{movement['date']}.pdf"
            filepath = os.path.join(month_dir, filename)
            
            self._create_movement_order_pdf(filepath, movement)
            
            # Show success message with file location
            messagebox.showinfo(
                "✅ PDF Δημιουργήθηκε",
                f"Η εντολή κίνησης αποθηκεύθηκε:\n{filepath}\n\n"
                f"Το PDF θα ανοίξει για εκτύπωση."
            )
            
            # Open file for printing
            try:
                os.startfile(filepath)  # Windows
            except AttributeError:
                try:
                    import subprocess
                    subprocess.run(['xdg-open', filepath])  # Linux
                except:
                    try:
                        subprocess.run(['open', filepath])  # macOS
                    except:
                        pass
            
            log_user_action("Movement document generated", f"File: {filename}")
            
        except Exception as e:
            logging.error(f"Error generating movement document: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη δημιουργία εγγράφου:\n{str(e)}")

    def _reprint_movement_document(self):
        """Ask for a movement number and regenerate its PDF order."""
        movement_number = simpledialog.askinteger(
            "Επανεκτύπωση Εντολής",
            "Δώστε τον αριθμό κίνησης:",
            parent=self.root,
            minvalue=1
        )
        if movement_number:
            self._generate_and_print_movement_document(movement_number)

    def _get_movement_document_data(self, movement_number):
        """Load all data needed for a movement order PDF."""
        try:
            self.db.cursor.execute("""
                SELECT
                    COALESCE(m.movement_number, m.id) AS movement_number,
                    m.date,
                    m.start_km,
                    m.end_km,
                    m.route,
                    m.purpose,
                    m.created_at,
                    d.name || ' ' || d.surname AS driver,
                    v.plate,
                    COALESCE(v.brand, '') AS brand,
                    COALESCE(v.vtype, '') AS vtype
                FROM movements m
                JOIN drivers d ON m.driver_id = d.id
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE m.movement_number = ?
            """, (movement_number,))
            row = self.db.cursor.fetchone()
            if not row:
                return None

            total_km = None
            if row[3] is not None:
                total_km = row[3] - row[2]

            return {
                "movement_number": row[0],
                "date": row[1],
                "start_km": row[2],
                "end_km": row[3],
                "total_km": total_km,
                "route": row[4] or "",
                "purpose": row[5] or "",
                "created_at": row[6] or "",
                "driver": row[7],
                "vehicle": row[8],
                "brand": row[9],
                "vtype": row[10],
            }
        except Exception as e:
            logging.error(f"Error loading movement document data: {e}")
            return None

    def _get_pdf_font_name(self):
        """Register and return a Unicode font suitable for Greek text."""
        if self._pdf_font_name:
            return self._pdf_font_name

        font_candidates = [
            (r"C:\Windows\Fonts\arial.ttf", "OximataArial"),
            (r"C:\Windows\Fonts\calibri.ttf", "OximataCalibri"),
            (r"C:\Windows\Fonts\DejaVuSans.ttf", "OximataDejaVu"),
        ]

        for font_path, font_name in font_candidates:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                self._pdf_font_name = font_name
                return font_name

        self._pdf_font_name = "Helvetica"
        return self._pdf_font_name

    def _create_movement_order_pdf(self, filepath, movement):
        """Create a printable A4 PDF for a movement order."""
        font_name = self._get_pdf_font_name()
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=14 * mm,
            bottomMargin=14 * mm
        )

        normal = ParagraphStyle("NormalGreek", fontName=font_name, fontSize=10, leading=13)
        title = ParagraphStyle("TitleGreek", fontName=font_name, fontSize=16, leading=20, alignment=1)
        subtitle = ParagraphStyle("SubtitleGreek", fontName=font_name, fontSize=11, leading=14, alignment=1)

        def p(text):
            return Paragraph(html.escape(str(text)) if text is not None else "", normal)

        try:
            date_obj = datetime.strptime(movement["date"], "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d/%m/%Y")
        except Exception:
            formatted_date = movement["date"]

        vehicle_description = movement["vehicle"]
        details = " / ".join(item for item in [movement["brand"], movement["vtype"]] if item)
        if details:
            vehicle_description = f"{vehicle_description} ({details})"

        order_rows = [
            [p("Αριθμός εντολής"), p(f"{movement['movement_number']:04d}")],
            [p("Ημερομηνία έκδοσης"), p(formatted_date)],
            [p("Οδηγός"), p(movement["driver"])],
            [p("Όχημα / Πινακίδα"), p(vehicle_description)],
            [p("Χιλιόμετρα αναχώρησης"), p(f"{movement['start_km']:,} χλμ")],
            [p("Διαδρομή / Προορισμός"), p(movement["route"] or "Δεν έχει καθοριστεί")],
            [p("Σκοπός κίνησης"), p(movement["purpose"] or "Δεν ορίστηκε")],
        ]

        return_rows = [
            [p("Ημερομηνία επιστροφής"), p("")],
            [p("Ώρα επιστροφής"), p("")],
            [p("Χιλιόμετρα επιστροφής"), p("" if movement["end_km"] is None else f"{movement['end_km']:,} χλμ")],
            [p("Συνολικά χιλιόμετρα"), p("" if movement["total_km"] is None else f"{movement['total_km']:,} χλμ")],
            [p("Παρατηρήσεις"), p("")],
        ]

        elements = [
            Paragraph("ΕΝΤΟΛΗ ΚΙΝΗΣΗΣ ΟΧΗΜΑΤΟΣ", title),
            Spacer(1, 4 * mm),
            Paragraph("Οχήματα - Διαχείριση Στόλου", subtitle),
            Spacer(1, 8 * mm),
        ]

        table_style = TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f3f5")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9099a1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])

        elements.append(Table(order_rows, colWidths=[55 * mm, 123 * mm], style=table_style))
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("ΣΤΟΙΧΕΙΑ ΕΠΙΣΤΡΟΦΗΣ", subtitle))
        elements.append(Spacer(1, 3 * mm))
        elements.append(Table(return_rows, colWidths=[55 * mm, 123 * mm], style=table_style))
        elements.append(Spacer(1, 12 * mm))

        signature_rows = [
            [p("Υπογραφή Οδηγού"), p("Υπογραφή Υπευθύνου")],
            [p("\n\n____________________________"), p("\n\n____________________________")],
        ]
        elements.append(Table(signature_rows, colWidths=[89 * mm, 89 * mm], style=TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9099a1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])))

        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph(
            f"Δημιουργήθηκε: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            normal
        ))

        doc.build(elements)

    def _create_movement_document_content(self, movement_number, date, driver, vehicle, start_km, route, purpose):
        """Create the content for movement document"""
        # Format date
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d/%m/%Y")
        except:
            formatted_date = date
        
        # Create document content
        content = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ΕΓΓΡΑΦΟ ΚΙΝΗΣΗΣ ΟΧΗΜΑΤΟΣ                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

 ΑΡΙΘΜΟΣ ΚΙΝΗΣΗΣ: {movement_number:04d}
📅 ΗΜΕΡΟΜΗΝΙΑ: {formatted_date}
👤 ΟΔΗΓΟΣ: {driver}
🚗 ΟΧΗΜΑ: {vehicle}
️ ΧΙΛΙΟΜΕΤΡΑ ΑΝΑΧΩΡΗΣΗΣ: {start_km:,} χλμ
🗺️ ΔΙΑΔΡΟΜΗ: {route or 'Δεν έχει καθοριστεί'}
 ΣΚΟΠΟΣ: {purpose or 'Δεν ορίστηκε'}

╔══════════════════════════════════════════════════════════════════════════════╗
║                              ΥΠΟΓΡΑΦΕΣ                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

👤 Υπογραφή Οδηγού: _________________    📅 Ημερομηνία: _________________

 Υπογραφή Υπευθύνου: _________________    📅 Ημερομηνία: _________________

══════════════════════════════════════════════════════════════════════════════════

📋 ΣΗΜΕΙΩΣΕΙΣ:
• Το παρόν έγγραφο πρέπει να συμπληρωθεί κατά την επιστροφή του οχήματος
• Χιλιόμετρα επιστροφής: _________________ χλμ
• Συνολικά χιλιόμετρα: _________________ χλμ
• Καύσιμα που καταναλώθηκε: _________________ L

══════════════════════════════════════════════════════════════════════════════════

📅 Δημιουργήθηκε: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Εφαρμογή: Οχήματα
"""
        
        return content

    def _clear_movement_form(self):
        """Clear movement form"""
        self.mov_date_var.set(datetime.now().strftime("%Y-%m-%d"))
        self.mov_driver_combo.clear()
        self.mov_vehicle_combo.clear()
        self.mov_start_km_var.set("")
        self.mov_route_entry.delete(0, tk.END)
        if hasattr(self, 'mov_purpose_combobox'):
            # Επαναφόρτωση όλων των σκοπών
            self.mov_purpose_combobox.set_values(self.db.get_purpose_names(active_only=True))
            self.mov_purpose_combobox.clear()
        self.mov_driver_combo.entry.focus_set()
    
    def _auto_fill_last_km(self, *args):
        """Auto-fill last recorded kilometers for selected vehicle"""
        vehicle = self.mov_vehicle_combo.get()
        if not vehicle:
            return
        
        vehicle_id = self._get_vehicle_id(vehicle)
        if not vehicle_id:
            return
        
        last_km = self._get_last_vehicle_km(vehicle_id)
        if last_km is not None:
            self.mov_start_km_var.set(str(last_km))
            self.status_bar.set_status(f"Αυτόματη συμπλήρωση χιλιομέτρων για {vehicle}")

    def _get_last_vehicle_km(self, vehicle_id):
        """Return the last known kilometers for a vehicle.

        Prefer the most recently closed movement's return kilometers. If the
        vehicle has never returned, fall back to the latest start kilometers.
        """
        try:
            self.db.cursor.execute("""
                SELECT end_km
                FROM movements
                WHERE vehicle_id = ? AND end_km IS NOT NULL
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
            """, (vehicle_id,))
            result = self.db.cursor.fetchone()
            if result and result[0] is not None:
                return int(result[0])

            self.db.cursor.execute("""
                SELECT start_km
                FROM movements
                WHERE vehicle_id = ? AND start_km IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
            """, (vehicle_id,))
            result = self.db.cursor.fetchone()
            if result and result[0] is not None:
                return int(result[0])
        except Exception as e:
            logging.error(f"Error getting last vehicle km: {e}")
        return None
    
    def _browse_movement_documents(self):
        """Browse and view movement documents organized by year/month"""
        movements_dir = MOVEMENTS_DIR
        
        # Check if movements directory exists
        if not os.path.exists(movements_dir):
            messagebox.showinfo("📁 Φάκελος Κινήσεων", 
                               "Δεν υπάρχουν ακόμη αποθηκευμένες κινήσεις.\n"
                               "Ο φάκελος 'Κινήσεις' θα δημιουργηθεί όταν δημιουργήσετε την πρώτη κίνηση.")
            return
        
        # Create browse window
        browse_window = tk.Toplevel(self.root)
        browse_window.title("📁 Περιήγηση Κινήσεων")
        browse_window.geometry("800x600")
        browse_window.configure(bg=THEMES[self.current_theme]["bg"])
        
        # Title
        title_frame = tk.Frame(browse_window, bg=THEMES[self.current_theme]["bg"])
        title_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(
            title_frame,
            text="📁 Περιήγηση Αποθηκευμένων Κινήσεων",
            font=FONT_TITLE,
            fg=THEMES[self.current_theme]["accent"],
            bg=THEMES[self.current_theme]["bg"],
        ).pack()
        
        # Create treeview for folder structure
        tree_frame = tk.Frame(browse_window, bg=THEMES[self.current_theme]["bg"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        tree = ttk.Treeview(tree_frame, columns=("type", "count"), show="tree headings")
        tree.heading("#0", text="Φάκελος/Αρχείο")
        tree.heading("type", text="Τύπος")
        tree.heading("count", text="Στοιχεία")
        
        tree.column("#0", width=400)
        tree.column("type", width=100, anchor="center")
        tree.column("count", width=80, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load folder structure
        try:
            # Root folder
            root_id = tree.insert("", "end", text="📁 Κινήσεις", values=("Φάκελος", ""), open=True)
            
            # Get years
            years = sorted([d for d in os.listdir(movements_dir) 
                           if os.path.isdir(os.path.join(movements_dir, d))], reverse=True)
            
            total_files = 0
            for year in years:
                year_path = os.path.join(movements_dir, year)
                months = sorted([d for d in os.listdir(year_path) 
                               if os.path.isdir(os.path.join(year_path, d))])
                
                year_count = 0
                year_id = tree.insert(root_id, "end", text=f"📅 {year}", values=("Έτος", ""), open=True)
                
                for month in months:
                    month_path = os.path.join(year_path, month)
                    files = [f for f in os.listdir(month_path) if f.endswith('.txt')]
                    month_count = len(files)
                    year_count += month_count
                    total_files += month_count
                    
                    # Greek month names
                    month_names = {
                        "01": "Ιανουάριος", "02": "Φεβρουάριος", "03": "Μάρτιος",
                        "04": "Απρίλιος", "05": "Μάιος", "06": "Ιούνιος",
                        "07": "Ιούλιος", "08": "Αύγουστος", "09": "Σεπτέμβριος",
                        "10": "Οκτώβριος", "11": "Νοέμβριος", "12": "Δεκέμβριος"
                    }
                    month_name = month_names.get(month, month)
                    
                    month_id = tree.insert(year_id, "end", 
                                         text=f"📂 {month_name} ({month})", 
                                         values=("Μήνας", f"{month_count} κινήσεις"))
                    
                    # Add files
                    for file in sorted(files):
                        file_path = os.path.join(month_path, file)
                        tree.insert(month_id, "end", 
                                   text=f"📄 {file}", 
                                   values=("Κίνηση", ""),
                                   tags=(file_path,))
                
                # Update year count
                tree.set(year_id, "count", f"{year_count} κινήσεις")
            
            # Update root count
            tree.set(root_id, "count", f"{total_files} κινήσεις")
            
        except Exception as e:
            logging.error(f"Error loading movement folders: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη φόρτωση φακέλων: {str(e)}")
        
        # Double-click to open file
        def on_double_click(event):
            item = tree.selection()[0]
            tags = tree.item(item, 'tags')
            if tags and os.path.isfile(tags[0]):
                try:
                    os.startfile(tags[0])  # Windows
                except:
                    try:
                        import subprocess
                        subprocess.run(['xdg-open', tags[0]])  # Linux
                    except:
                        try:
                            subprocess.run(['open', tags[0]])  # macOS
                        except:
                            messagebox.showinfo("📄 Αρχείο", f"Αρχείο: {tags[0]}")
        
        tree.bind("<Double-1>", on_double_click)
        
        # Buttons frame
        buttons_frame = tk.Frame(browse_window, bg=THEMES[self.current_theme]["bg"])
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        ModernButton(
            buttons_frame,
            text="📂 Άνοιγμα Φακέλου Κινήσεων",
            style="info",
            command=lambda: os.startfile(movements_dir) if os.path.exists(movements_dir) else None
        ).pack(side="left", padx=5)
        
        ModernButton(
            buttons_frame,
            text="❌ Κλείσιμο",
            style="secondary",
            command=browse_window.destroy
        ).pack(side="right", padx=5)

    def _load_movements(self):
        """Load movements with improved filtering and performance"""
        try:
            # Clear trees
            for item in self.tree_active.get_children():
                self.tree_active.delete(item)
            for item in self.tree_completed.get_children():
                self.tree_completed.delete(item)
            
            # Get search terms
            active_search = self.active_search_var.get().lower() if hasattr(self, 'active_search_var') else ""
            completed_search = self.completed_search_var.get().lower() if hasattr(self, 'completed_search_var') else ""
            
            # Load active movements (not returned)
            self.db.cursor.execute("""
                SELECT m.id, COALESCE(m.movement_number, 0), m.date, 
                       d.name || ' ' || d.surname as driver, v.plate, 
                       m.start_km, m.route, m.purpose
                FROM movements m
                JOIN drivers d ON m.driver_id = d.id
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE m.end_km IS NULL
                ORDER BY m.date DESC, m.id DESC
            """)
            
            for row in self.db.cursor.fetchall():
                # Apply search filter
                if active_search:
                    searchable_text = f"{row[2]} {row[3]} {row[4]} {row[6]} {row[7]}".lower()
                    if active_search not in searchable_text:
                        continue
                
                mov_num_display = f"{row[1]:04d}" if row[1] > 0 else "---"
                display_values = (mov_num_display,) + row[2:]
                self.tree_active.insert("", "end", values=display_values, tags=(row[0],))
            
            # Load completed movements (today only)
            today = datetime.now().strftime("%Y-%m-%d")
            self.db.cursor.execute("""
                SELECT m.id, COALESCE(m.movement_number, 0), m.date, 
                       d.name || ' ' || d.surname as driver, v.plate, 
                       m.start_km, m.end_km, m.route, m.purpose,
                       (COALESCE(m.end_km, 0) - COALESCE(m.start_km, 0)) as total_km
                FROM movements m
                JOIN drivers d ON m.driver_id = d.id
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE m.end_km IS NOT NULL AND m.date = ?
                ORDER BY m.id DESC
            """, (today,))
            
            for row in self.db.cursor.fetchall():
                # Apply search filter
                if completed_search:
                    searchable_text = f"{row[2]} {row[3]} {row[4]} {row[7]} {row[8]}".lower()
                    if completed_search not in searchable_text:
                        continue
                
                mov_num_display = f"{row[1]:04d}" if row[1] > 0 else "---"
                display_values = (mov_num_display,) + row[2:]
                self.tree_completed.insert("", "end", values=display_values, tags=(row[0],))
            
            self.status_bar.set_status("Κινήσεις ενημερώθηκαν")
            
        except Exception as e:
            logging.error(f"Error loading movements: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά τη φόρτωση κινήσεων: {str(e)}")
    
    # Utility methods
    def _get_driver_id(self, driver_name):
        """Get driver ID from name"""
        try:
            parts = driver_name.split(' ', 1)
            if len(parts) == 2:
                name, surname = parts
                self.db.cursor.execute(
                    "SELECT id FROM drivers WHERE name = ? AND surname = ?",
                    (name, surname)
                )
                result = self.db.cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logging.error(f"Error getting driver ID: {e}")
        return None
    
    def _get_vehicle_id(self, plate):
        """Get vehicle ID from plate"""
        try:
            self.db.cursor.execute("SELECT id FROM vehicles WHERE plate = ?", (plate,))
            result = self.db.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"Error getting vehicle ID: {e}")
        return None
    
    def _is_vehicle_active(self, vehicle_id):
        """Check if vehicle has active movement"""
        try:
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM movements WHERE vehicle_id = ? AND end_km IS NULL",
                (vehicle_id,)
            )
            return self.db.cursor.fetchone()[0] > 0
        except Exception as e:
            logging.error(f"Error checking vehicle status: {e}")
        return False
    
    def _refresh_all_data(self):
        """Refresh all data in the application"""
        try:
            progress = ProgressDialog(self.root, "Ανανέωση Δεδομένων", "Φόρτωση δεδομένων...")
            
            progress.update_message("Φόρτωση κινήσεων...")
            self._load_movements()
            
            progress.update_message("Φόρτωση οχημάτων...")
            self._refresh_movement_combos()
            
            progress.update_message("Ενημέρωση δεξαμενής...")
            self._update_tank_level()
            
            progress.close()
            self.status_bar.set_status("Όλα τα δεδομένα ανανεώθηκαν")
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            logging.error(f"Error refreshing data: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την ανανέωση: {str(e)}")
    
    def _refresh_movement_combos(self):
        """Refresh movement combo boxes"""
        try:
            # Get drivers
            self.db.cursor.execute("SELECT id, name, surname FROM drivers ORDER BY name, surname")
            drivers = []
            self.driver_ids = {}
            
            for row in self.db.cursor.fetchall():
                driver_text = f"{row[1]} {row[2]}"
                drivers.append(driver_text)
                self.driver_ids[driver_text] = row[0]
            
            # Get vehicles
            self.db.cursor.execute("SELECT id, plate FROM vehicles ORDER BY plate")
            vehicles = []
            self.vehicle_ids = {}
            
            for row in self.db.cursor.fetchall():
                vehicles.append(row[1])
                self.vehicle_ids[row[1]] = row[0]
            
            # Update combo boxes
            self.mov_driver_combo.set_values(drivers)
            self.mov_vehicle_combo.set_values(vehicles)
            
        except Exception as e:
            logging.error(f"Error refreshing combos: {e}")
    
    def _update_tank_level(self):
        """Update tank level display"""
        try:
            self.db.cursor.execute(
                "SELECT SUM(CASE WHEN type = 'fill' THEN liters ELSE -liters END) FROM tank"
            )
            level = self.db.cursor.fetchone()[0] or 0
            
            # Calculate percentage
            percentage = (level / TANK_CAPACITY) * 100 if TANK_CAPACITY > 0 else 0
            
            # Determine status
            if level < TANK_MIN_LEVEL:
                color = THEMES[self.current_theme]["danger"]
                icon = "🔴"
                status = "ΧΑΜΗΛΟ"
            else:
                color = THEMES[self.current_theme]["success"]
                icon = "🟢"
                status = "ΚΑΛΟ"
            
            # Update status bar indicator if it exists
            if hasattr(self, 'tank_indicator'):
                self.tank_indicator.config(
                    text=f"{icon} Δεξαμενή: {level:.1f}L ({status})",
                    fg=color
                )
            
            # Update tank level label in fuel tab if it exists
            if hasattr(self, 'tank_level_label'):
                tank_text = f"📊 Τρέχον Επίπεδο: {level:.1f}L / {TANK_CAPACITY:,.0f}L ({percentage:.1f}%)"
                self.tank_level_label.config(
                    text=tank_text,
                    fg=color
                )
            
            # Update progress bar if it exists
            if hasattr(self, 'tank_progress'):
                self.tank_progress['value'] = percentage
                
                # Style progress bar based on level
                style = ttk.Style()
                if level < TANK_MIN_LEVEL:
                    style.configure("Tank.Horizontal.TProgressbar",
                                  background=THEMES[self.current_theme]["danger"])
                elif percentage < 30:
                    style.configure("Tank.Horizontal.TProgressbar",
                                  background=THEMES[self.current_theme]["warning"])
                else:
                    style.configure("Tank.Horizontal.TProgressbar",
                                  background=THEMES[self.current_theme]["success"])
                
                self.tank_progress.configure(style="Tank.Horizontal.TProgressbar")
            
        except Exception as e:
            logging.error(f"Error updating tank level: {e}")
            if hasattr(self, 'tank_indicator'):
                self.tank_indicator.config(text="⛽ Σφάλμα δεξαμενής", fg="red")
            if hasattr(self, 'tank_level_label'):
                self.tank_level_label.config(text="⚠️ Σφάλμα φόρτωσης δεδομένων", fg="red")
            if hasattr(self, 'tank_progress'):
                self.tank_progress['value'] = 0
    
    # Theme and UI methods
    def _change_theme(self, theme_name):
        """Change application theme"""
        try:
            if theme_name not in THEMES:
                self.status_bar.set_status(f"Άγνωστο θέμα: {theme_name}", "error")
                return
                
            self.current_theme = theme_name
            theme = THEMES[theme_name]
            
            # Save theme preference
            from config import save_user_setting
            save_user_setting("theme", theme_name)
            
            # Update root window
            self.root.configure(bg=theme["bg"])
            
            # Update all widgets recursively
            self._update_widget_theme(self.root, theme)
            
            # Update menu bar to reflect new theme
            self._create_menu_bar()
            
            theme_names = {
                "light": "Φωτεινό",
                "dark": "Σκοτεινό", 
                "blue": "Μπλε",
                "green": "Πράσινο",
                "purple": "Μωβ"
            }
            
            self.status_bar.set_status(f"Θέμα άλλαξε σε: {theme_names.get(theme_name, theme_name)}")
            log_user_action("Theme changed", theme_name)
            
        except Exception as e:
            logging.error(f"Error changing theme: {e}")
            self.status_bar.set_status("Σφάλμα αλλαγής θέματος", "error")
    
    def _update_widget_theme(self, widget, theme):
        """Recursively update widget themes"""
        try:
            widget_class = widget.winfo_class()
            
            if widget_class in ["Frame", "Toplevel"]:
                widget.configure(bg=theme["bg"])
            elif widget_class == "Label":
                widget.configure(bg=theme["bg"], fg=theme["fg"])
            elif widget_class == "Button":
                widget.configure(bg=theme["button_bg"], fg=theme["button_fg"])
            elif widget_class == "Entry":
                widget.configure(bg=theme["entry_bg"], fg=theme["fg"])
            
            # Update children
            for child in widget.winfo_children():
                self._update_widget_theme(child, theme)
                
        except Exception as e:
            logging.error(f"Error updating widget theme: {e}")
    
    # System methods
    def _backup_database(self):
        """Create database backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"oximata_backup_{timestamp}.db"
            
            backup_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")],
                initialdir=BACKUPS_DIR,
                initialname=backup_filename
            )
            
            if backup_path:
                if self.db.backup_database(backup_path):
                    messagebox.showinfo("✅ Επιτυχία", f"Backup δημιουργήθηκε επιτυχώς:\n{backup_path}")
                    self.status_bar.set_status("Backup ολοκληρώθηκε")
                else:
                    messagebox.showerror("❌ Σφάλμα", "Αποτυχία δημιουργίας backup!")
        except Exception as e:
            logging.error(f"Backup error: {e}")
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα backup: {str(e)}")
    
    def _show_system_stats(self):
        """Show comprehensive system statistics"""
        # Implementation for system statistics
        pass
    
    def _cleanup_old_data(self):
        """Cleanup old data with user confirmation"""
        # Implementation for data cleanup
        pass
    
    def _show_help(self):
        """Show help dialog"""
        help_text = """
🚗 ΟΔΗΓΙΕΣ ΧΡΗΣΗΣ ΣΥΣΤΗΜΑΤΟΣ ΔΙΑΧΕΙΡΙΣΗΣ ΣΤΟΛΟΥ

📋 ΒΑΣΙΚΕΣ ΛΕΙΤΟΥΡΓΙΕΣ:
• Κινήσεις: Δημιουργία και παρακολούθηση κινήσεων οχημάτων
• Οχήματα: Διαχείριση στόλου οχημάτων
• Οδηγοί: Διαχείριση προσωπικού οδηγών
• Καύσιμα: Παρακολούθηση κατανάλωσης καυσίμων
• Αναφορές: Εξαγωγή δεδομένων και στατιστικών

⌨️ ΣΥΝΤΟΜΕΥΣΕΙΣ ΠΛΗΚΤΡΟΛΟΓΙΟΥ:
• F5: Ανανέωση δεδομένων
• Ctrl+S: Backup βάσης δεδομένων
• Ctrl+Q: Έξοδος από την εφαρμογή

💡 ΣΥΜΒΟΥΛΕΣ:
• Χρησιμοποιήστε τη λειτουργία αναζήτησης για γρήγορη εύρεση
• Κάντε τακτικά backup της βάσης δεδομένων
• Ελέγχετε το επίπεδο της δεξαμενής καυσίμων
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("📖 Οδηγίες Χρήσης")
        help_window.geometry("600x500")
        
        text_widget = tk.Text(help_window, font=FONT_NORMAL, wrap=tk.WORD, padx=20, pady=20)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
    
    def _show_about(self):
        """Show about dialog"""
        about_text = f"""
🚗 Σύστημα Διαχείρισης Στόλου
Έκδοση 2.0 - Βελτιωμένη

Δημιουργήθηκε για τη διαχείριση στόλου οχημάτων
με σύγχρονη διεπαφή και βελτιωμένες λειτουργίες.

📅 Ημερομηνία: {datetime.now().strftime('%d/%m/%Y')}
🐍 Python Version: {sys.version.split()[0]}
💾 Βάση Δεδομένων: SQLite3

Βασισμένο στο Fleet Management System
        """
        
        messagebox.showinfo("ℹ️ Σχετικά με την Εφαρμογή", about_text)
    
    def _edit_movement_return(self, event):
        """Edit movement return with improved UX"""
        selection = self.tree_active.selection()
        if not selection:
            messagebox.showerror("❌ Σφάλμα", "Παρακαλώ επιλέξτε κίνηση!")
            return

        item = selection[0]
        values = self.tree_active.item(item, "values")
        movement_num = values[0]
        start_km = values[4]

        # Παράθυρο για καταχώρηση χλμ επιστροφής
        def submit():
            end_km = entry_end_km.get().strip()
            try:
                end_km_value = int(end_km)
                start_km_value = int(start_km)
            except (TypeError, ValueError):
                messagebox.showerror("❌ Σφάλμα", "Τα χλμ επιστροφής πρέπει να είναι ακέραιος αριθμός!")
                return

            if end_km_value < start_km_value:
                messagebox.showerror(
                    "❌ Σφάλμα Χιλιομέτρων",
                    f"Τα χλμ επιστροφής ({end_km_value}) δεν μπορεί να είναι μικρότερα "
                    f"από τα χλμ αναχώρησης ({start_km_value})."
                )
                return
            try:
                self.db.cursor.execute(
                    "UPDATE movements SET end_km=?, updated_at=CURRENT_TIMESTAMP WHERE movement_number=?",
                    (end_km_value, movement_num)
                )
                self.db.conn.commit()
                top.destroy()
                self._load_movements()
                self._update_statistics()
                self.status_bar.set_status(f"Η κίνηση {movement_num} έκλεισε επιτυχώς.")
                messagebox.showinfo("✅ Επιτυχία", "Η κίνηση έκλεισε επιτυχώς!")
            except Exception as e:
                messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την ενημέρωση: {str(e)}")

        top = tk.Toplevel(self.root)
        top.title("Κλείσιμο Κίνησης")
        top.geometry("300x180")
        top.configure(bg=THEMES[self.current_theme]["bg"])
        top.grab_set()
        
        # Center the window
        top.transient(self.root)
        top.focus_set()
        
        # Title label
        title_label = tk.Label(top, 
                              text=f"📝 Κλείσιμο Κίνησης #{movement_num}", 
                              font=FONT_SUBTITLE,
                              bg=THEMES[self.current_theme]["bg"],
                              fg=THEMES[self.current_theme]["accent"])
        title_label.pack(padx=10, pady=(10, 5))
        
        # Start km info
        tk.Label(top, 
                text=f"🛣️ Χλμ Αναχώρησης: {start_km}", 
                font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"],
                fg=THEMES[self.current_theme]["fg"]).pack(padx=10, pady=(2, 2))
        
        # End km input
        tk.Label(top, 
                text="🏁 Χλμ Επιστροφής:", 
                font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["bg"],
                fg=THEMES[self.current_theme]["fg"]).pack(padx=10, pady=(2, 2))
        
        entry_end_km = tk.Entry(top, 
                               font=FONT_NORMAL,
                               bg=THEMES[self.current_theme]["entry_bg"],
                               fg=THEMES[self.current_theme]["fg"],
                               relief="flat",
                               borderwidth=1,
                               highlightthickness=1,
                               highlightcolor=THEMES[self.current_theme]["accent"])
        entry_end_km.pack(padx=10, pady=(2, 10), fill="x")
        entry_end_km.focus_set()
        
        # Add tooltip
        if hasattr(self, 'tooltip_manager'):
            self.tooltip_manager.add_tooltip(entry_end_km, "Πληκτρολογήστε τα χιλιόμετρα επιστροφής και πατήστε Enter")
        
        # Bind Enter key to submit
        entry_end_km.bind('<Return>', lambda event: submit())
        entry_end_km.bind('<KP_Enter>', lambda event: submit())  # Numeric keypad Enter
        
        # Buttons frame
        buttons_frame = tk.Frame(top, bg=THEMES[self.current_theme]["bg"])
        buttons_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        btn_submit = ModernButton(buttons_frame, 
                                 text="✅ Καταχώρηση", 
                                 style="success", 
                                 command=submit)
        btn_submit.pack(side="left", padx=(0, 5))
        
        btn_cancel = ModernButton(buttons_frame, 
                                 text="❌ Ακύρωση", 
                                 style="secondary", 
                                 command=top.destroy)
        btn_cancel.pack(side="right", padx=(5, 0))
    
    def _edit_completed_movement(self, event):
        """Edit completed movement"""
        # Implementation for editing completed movements
        pass
    
    # Driver Analytics Methods
    def _load_analytics_drivers(self):
        """Load drivers for analytics selection"""
        try:
            drivers = self.db.get_all_drivers()
            driver_names = [f"{driver[1]} (ID: {driver[0]})" for driver in drivers]
            self.analytics_driver_combo.set_values(driver_names)
            if driver_names:
                self.analytics_driver_combo.set(driver_names[0])
        except Exception as e:
            logging.error(f"Error loading analytics drivers: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα φόρτωσης οδηγών: {e}")
    
    def _show_driver_analytics(self):
        """Show analytics for selected driver"""
        try:
            # Get selected driver ID
            selected_driver = self.analytics_driver_combo.get()
            if not selected_driver:
                messagebox.showwarning("Προειδοποίηση", "Παρακαλώ επιλέξτε οδηγό")
                return
            
            driver_id = int(selected_driver.split("ID: ")[1].split(")")[0])
            
            # Get date range
            start_date = self.analytics_start_date.get() if self.analytics_start_date.get() else None
            end_date = self.analytics_end_date.get() if self.analytics_end_date.get() else None
            
            # Get analytics data
            analytics = self.db.get_driver_analytics(driver_id, start_date, end_date)
            if not analytics:
                messagebox.showinfo("Πληροφορία", "Δεν βρέθηκαν δεδομένα για τον επιλεγμένο οδηγό")
                return
            
            # Display analytics
            self._display_driver_analytics(analytics)
            
        except Exception as e:
            logging.error(f"Error showing driver analytics: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα εμφάνισης αναλυτικών: {e}")
    
    def _display_driver_analytics(self, analytics):
        """Display driver analytics in the UI"""
        # Clear previous results
        for widget in self.summary_frame.winfo_children():
            widget.destroy()
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        
        # Summary Tab
        summary_canvas = tk.Canvas(self.summary_frame, bg=THEMES[self.current_theme]["frame_bg"])
        summary_scrollbar = ttk.Scrollbar(self.summary_frame, orient="vertical", command=summary_canvas.yview)
        summary_canvas.configure(yscrollcommand=summary_scrollbar.set)
        
        summary_content = tk.Frame(summary_canvas, bg=THEMES[self.current_theme]["frame_bg"])
        summary_canvas.create_window((0, 0), window=summary_content, anchor="nw")
        
        # Driver info
        info_frame = tk.LabelFrame(summary_content, text=f"👤 {analytics['driver_name']}", 
                                  font=FONT_SUBTITLE, bg=THEMES[self.current_theme]["frame_bg"],
                                  fg=THEMES[self.current_theme]["accent"])
        info_frame.pack(fill="x", padx=10, pady=10)
        
        # Key metrics in a grid
        metrics_frame = tk.Frame(info_frame, bg=THEMES[self.current_theme]["frame_bg"])
        metrics_frame.pack(fill="x", padx=10, pady=10)
        
        # Row 1
        self._create_metric_label(metrics_frame, "🚗 Συνολικές Κινήσεις", 
                                 str(analytics['total_movements']), 0, 0)
        self._create_metric_label(metrics_frame, "📏 Συνολικά Χιλιόμετρα", 
                                 f"{analytics['total_kilometers']:,.0f} km", 0, 1)
        
        # Row 2
        self._create_metric_label(metrics_frame, "⛽ Συνολικά Καύσιμα", 
                                 f"{analytics['total_fuel_liters']:.1f} L", 1, 0)
        self._create_metric_label(metrics_frame, "💰 Συνολικό Κόστος", 
                                 f"{analytics['total_fuel_cost']:.2f} €", 1, 1)
        
        # Row 3
        self._create_metric_label(metrics_frame, "📊 Μέση Κατανάλωση", 
                                 f"{analytics['avg_consumption_km_per_liter']:.2f} km/L", 2, 0)
        self._create_metric_label(metrics_frame, "💸 Κόστος/km", 
                                 f"{analytics['avg_cost_per_km']:.3f} €/km", 2, 1)
        
        # Most used vehicles
        if analytics['most_used_vehicles']:
            vehicles_frame = tk.LabelFrame(summary_content, text="🚙 Πιο Συχνά Χρησιμοποιούμενα Οχήματα", 
                                          font=FONT_SUBTITLE, bg=THEMES[self.current_theme]["frame_bg"],
                                          fg=THEMES[self.current_theme]["accent"])
            vehicles_frame.pack(fill="x", padx=10, pady=10)
            
            for i, vehicle in enumerate(analytics['most_used_vehicles'][:3]):
                vehicle_info = f"🚗 {vehicle['plate']} - {vehicle['usage_count']} κινήσεις - {vehicle['total_km']:,.0f} km"
                tk.Label(vehicles_frame, text=vehicle_info, font=FONT_NORMAL,
                        bg=THEMES[self.current_theme]["frame_bg"],
                        fg=THEMES[self.current_theme]["fg"]).pack(anchor="w", padx=10, pady=2)
        
        # Monthly breakdown
        if analytics['monthly_breakdown']:
            monthly_frame = tk.LabelFrame(summary_content, text="📅 Μηνιαία Στοιχεία", 
                                         font=FONT_SUBTITLE, bg=THEMES[self.current_theme]["frame_bg"],
                                         fg=THEMES[self.current_theme]["accent"])
            monthly_frame.pack(fill="x", padx=10, pady=10)
            
            # Headers
            headers_frame = tk.Frame(monthly_frame, bg=THEMES[self.current_theme]["frame_bg"])
            headers_frame.pack(fill="x", padx=10, pady=5)
            
            tk.Label(headers_frame, text="Μήνας", font=FONT_NORMAL, width=10,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0)
            tk.Label(headers_frame, text="Κινήσεις", font=FONT_NORMAL, width=10,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=1)
            tk.Label(headers_frame, text="Χιλιόμετρα", font=FONT_NORMAL, width=12,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=2)
            tk.Label(headers_frame, text="Καύσιμα (L)", font=FONT_NORMAL, width=12,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=3)
            
            # Data rows
            for i, month_data in enumerate(analytics['monthly_breakdown'][:6]):
                row_frame = tk.Frame(monthly_frame, bg=THEMES[self.current_theme]["frame_bg"])
                row_frame.pack(fill="x", padx=10, pady=1)
                
                tk.Label(row_frame, text=month_data['month'], font=FONT_SMALL, width=10,
                        bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0)
                tk.Label(row_frame, text=str(month_data['movements']), font=FONT_SMALL, width=10,
                        bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=1)
                tk.Label(row_frame, text=f"{month_data['kilometers']:,.0f}", font=FONT_SMALL, width=12,
                        bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=2)
                tk.Label(row_frame, text=f"{month_data['fuel_liters']:.1f}", font=FONT_SMALL, width=12,
                        bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=3)
        
        # Update scroll region
        summary_content.update_idletasks()
        summary_canvas.configure(scrollregion=summary_canvas.bbox("all"))
        
        # Pack canvas and scrollbar
        summary_canvas.pack(side="left", fill="both", expand=True)
        summary_scrollbar.pack(side="right", fill="y")
        
        # Details Tab - Purpose breakdown
        self._display_purpose_breakdown(analytics['purpose_breakdown'])
    
    def _create_metric_label(self, parent, title, value, row, col):
        """Create a metric display label"""
        metric_frame = tk.Frame(parent, bg=THEMES[self.current_theme]["frame_bg"], relief="ridge", bd=1)
        metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        parent.grid_columnconfigure(col, weight=1)
        
        tk.Label(metric_frame, text=title, font=FONT_SMALL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["text_muted"]).pack(pady=(5, 0))
        tk.Label(metric_frame, text=value, font=FONT_NORMAL,
                bg=THEMES[self.current_theme]["frame_bg"], 
                fg=THEMES[self.current_theme]["accent"]).pack(pady=(0, 5))
    
    def _display_purpose_breakdown(self, purpose_data):
        """Display purpose breakdown in details tab"""
        # Clear details frame
        for widget in self.details_frame.winfo_children():
            widget.destroy()
        
        if not purpose_data:
            tk.Label(self.details_frame, text="Δεν υπάρχουν δεδομένα σκοπών", 
                    font=FONT_NORMAL, bg=THEMES[self.current_theme]["frame_bg"],
                    fg=THEMES[self.current_theme]["text_muted"]).pack(pady=20)
            return
        
        # Purpose breakdown
        purpose_frame = tk.LabelFrame(self.details_frame, text="🎯 Ανάλυση ανά Σκοπό", 
                                     font=FONT_SUBTITLE, bg=THEMES[self.current_theme]["frame_bg"],
                                     fg=THEMES[self.current_theme]["accent"])
        purpose_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Headers
        headers_frame = tk.Frame(purpose_frame, bg=THEMES[self.current_theme]["frame_bg"])
        headers_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(headers_frame, text="Σκοπός", font=FONT_NORMAL, width=20,
                bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0)
        tk.Label(headers_frame, text="Κινήσεις", font=FONT_NORMAL, width=10,
                bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=1)
        tk.Label(headers_frame, text="Χιλιόμετρα", font=FONT_NORMAL, width=12,
                bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=2)
        tk.Label(headers_frame, text="Ποσοστό", font=FONT_NORMAL, width=10,
                bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=3)
        
        # Calculate total for percentages
        total_movements = sum(p['count'] for p in purpose_data)
        
        # Data rows
        for i, purpose in enumerate(purpose_data):
            row_frame = tk.Frame(purpose_frame, bg=THEMES[self.current_theme]["frame_bg"])
            row_frame.pack(fill="x", padx=10, pady=1)
            
            percentage = (purpose['count'] / total_movements * 100) if total_movements > 0 else 0
            
            tk.Label(row_frame, text=purpose['purpose'], font=FONT_SMALL, width=20,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=0, sticky="w")
            tk.Label(row_frame, text=str(purpose['count']), font=FONT_SMALL, width=10,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=1)
            tk.Label(row_frame, text=f"{purpose['total_km']:,.0f}", font=FONT_SMALL, width=12,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=2)
            tk.Label(row_frame, text=f"{percentage:.1f}%", font=FONT_SMALL, width=10,
                    bg=THEMES[self.current_theme]["frame_bg"], fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=3)
    
    def _show_all_drivers_summary(self):
        """Show summary for all drivers"""
        try:
            # Get date range
            start_date = self.analytics_start_date.get() if self.analytics_start_date.get() else None
            end_date = self.analytics_end_date.get() if self.analytics_end_date.get() else None
            
            # Get summary data
            summary = self.db.get_all_drivers_summary(start_date, end_date)
            if not summary:
                messagebox.showinfo("Πληροφορία", "Δεν βρέθηκαν δεδομένα")
                return
            
            # Display in comparison tab
            self._display_drivers_comparison(summary)
            
        except Exception as e:
            logging.error(f"Error showing drivers summary: {e}")
            messagebox.showerror("Σφάλμα", f"Σφάλμα εμφάνισης σύνοψης: {e}")
    
    def _display_drivers_comparison(self, summary):
        """Display comparison of all drivers"""
        # Clear comparison frame
        for widget in self.comparison_frame.winfo_children():
            widget.destroy()
        
        if not summary:
            tk.Label(self.comparison_frame, text="Δεν υπάρχουν δεδομένα", 
                    font=FONT_NORMAL, bg=THEMES[self.current_theme]["frame_bg"],
                    fg=THEMES[self.current_theme]["text_muted"]).pack(pady=20)
            return
        
        # Create scrollable frame
        canvas = tk.Canvas(self.comparison_frame, bg=THEMES[self.current_theme]["frame_bg"])
        scrollbar = ttk.Scrollbar(self.comparison_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame = tk.Frame(canvas, bg=THEMES[self.current_theme]["frame_bg"])
        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        
        # Title
        title_label = tk.Label(content_frame, text="👥 Σύγκριση Όλων των Οδηγών", 
                              font=FONT_SUBTITLE, bg=THEMES[self.current_theme]["frame_bg"],
                              fg=THEMES[self.current_theme]["accent"])
        title_label.pack(pady=10)
        
        # Headers
        headers_frame = tk.Frame(content_frame, bg=THEMES[self.current_theme]["frame_bg"])
        headers_frame.pack(fill="x", padx=10, pady=5)
        
        headers = ["Όνομα", "Κινήσεις", "Χιλιόμετρα", "Καύσιμα (L)", "Κόστος (€)", "Κατανάλωση"]
        widths = [20, 10, 12, 12, 12, 12]
        
        for i, (header, width) in enumerate(zip(headers, widths)):
            tk.Label(headers_frame, text=header, font=FONT_NORMAL, width=width,
                    bg=THEMES[self.current_theme]["frame_bg"], 
                    fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=i, padx=2)
        
        # Data rows
        for i, driver in enumerate(summary):
            row_frame = tk.Frame(content_frame, bg=THEMES[self.current_theme]["frame_bg"])
            row_frame.pack(fill="x", padx=10, pady=1)
            
            values = [
                driver['driver_name'],
                str(driver['total_movements']),
                f"{driver['total_kilometers']:,.0f}",
                f"{driver['total_fuel_liters']:.1f}",
                f"{driver['total_fuel_cost']:.2f}",
                f"{driver['avg_consumption']:.2f}"
            ]
            
            for j, (value, width) in enumerate(zip(values, widths)):
                tk.Label(row_frame, text=value, font=FONT_SMALL, width=width,
                        bg=THEMES[self.current_theme]["frame_bg"], 
                        fg=THEMES[self.current_theme]["fg"]).grid(row=0, column=j, padx=2, sticky="w")
        
        # Update scroll region
        content_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _on_close(self):
        """Handle application close with cleanup"""
        try:
            # Ask for confirmation
            if ConfirmDialog(
                self.root,
                "🚪 Έξοδος από την Εφαρμογή",
                "Είστε σίγουρος ότι θέλετε να κλείσετε την εφαρμογή;"
            ).show():
                
                log_user_action("Application closing")
                
                # Close database connection
                if self.db:
                    self.db.close()
                
                # Destroy window
                self.root.destroy()
                
        except Exception as e:
            logging.error(f"Error during application close: {e}")
            self.root.destroy()

    def _update_font_sizes(self, screen_width, screen_height):
        """Update font sizes based on screen dimensions"""
        from config import get_adaptive_font_sizes
        
        # Get adaptive font sizes
        font_sizes = get_adaptive_font_sizes(screen_width, screen_height)
        
        # Update global font variables
        global FONT_BIG, FONT_NORMAL, FONT_SMALL, FONT_TITLE, FONT_SUBTITLE
        FONT_BIG = font_sizes['FONT_BIG']
        FONT_NORMAL = font_sizes['FONT_NORMAL']
        FONT_SMALL = font_sizes['FONT_SMALL']
        FONT_TITLE = font_sizes['FONT_TITLE']
        FONT_SUBTITLE = font_sizes['FONT_SUBTITLE']
        
        # Update button styles with new font sizes
        for style in BUTTON_STYLES.values():
            style['font'] = FONT_NORMAL
        
        logging.info(f"Font sizes updated for {screen_width}x{screen_height} screen")

    def _get_adaptive_column_widths(self, base_widths):
        """Get adaptive column widths based on window size"""
        if not hasattr(self, 'window_width'):
            return base_widths
        
        # Scale factor based on window width
        if self.window_width < 1200:
            scale_factor = 0.8
        elif self.window_width < 1600:
            scale_factor = 0.9
        else:
            scale_factor = 1.0
        
        return {col: int(width * scale_factor) for col, width in base_widths.items()}

def main():
    """Main application entry point"""
    try:
        # Create root window
        root = tk.Tk()
        
        # Initialize application
        app = FleetManagerImproved(root)
        
        # Start main loop
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"Critical error in main: {e}")
        if 'root' in locals():
            messagebox.showerror("❌ Κρίσιμο Σφάλμα", 
                               f"Κρίσιμο σφάλμα εφαρμογής:\n{str(e)}")
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
