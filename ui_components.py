"""
Custom UI components for Fleet Management System
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config import THEMES, BUTTON_STYLES, FONT_NORMAL

class ModernButton(tk.Button):
    """Custom modern button with hover effects and improved styling"""
    
    def __init__(self, parent, style="primary", **kwargs):
        self.style_name = style
        button_style = BUTTON_STYLES.get(style, BUTTON_STYLES["primary"]).copy()
        
        # Merge custom kwargs
        button_style.update(kwargs)
        
        super().__init__(parent, **button_style)
        
        # Store original colors for hover effects
        self.original_bg = button_style["bg"]
        self.hover_bg = button_style["activebackground"]
        
        # Bind hover effects
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<ButtonRelease-1>", self.on_release)
    
    def on_enter(self, event):
        """Handle mouse enter with smooth transition"""
        self.configure(bg=self.hover_bg)
        self.configure(cursor="hand2")
    
    def on_leave(self, event):
        """Handle mouse leave"""
        self.configure(bg=self.original_bg)
        self.configure(cursor="")
    
    def on_click(self, event):
        """Handle button click"""
        self.configure(relief="sunken")
    
    def on_release(self, event):
        """Handle button release"""
        self.configure(relief="flat")

class ModernFrame(tk.Frame):
    """Custom modern frame with improved styling"""
    
    def __init__(self, parent, theme="light", **kwargs):
        self.theme = theme
        theme_colors = THEMES[theme]
        
        default_style = {
            "bg": theme_colors["frame_bg"],
            "relief": "flat",
            "borderwidth": 1,
            "highlightbackground": theme_colors["border"],
            "highlightthickness": 1
        }
        
        default_style.update(kwargs)
        super().__init__(parent, **default_style)

class SearchableCombobox(ttk.Frame):
    """Enhanced combobox with live search and better UX"""
    
    def __init__(self, parent, values=None, font=None, width=None, placeholder="", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.values = values or []
        self.filtered_values = self.values[:]
        self.selected_value = ""
        self.placeholder = placeholder
        self.var = tk.StringVar()
        
        # Create entry widget
        self.entry = tk.Entry(
            self, 
            textvariable=self.var, 
            font=font or FONT_NORMAL, 
            width=width,
            relief="flat", 
            borderwidth=1, 
            highlightthickness=1,
            highlightbackground="#dee2e6", 
            highlightcolor="#007bff"
        )
        self.entry.pack(fill="x", expand=True)
        
        # Create dropdown listbox
        self.listbox_frame = tk.Frame(
            self, 
            relief="flat", 
            borderwidth=1,
            highlightbackground="#dee2e6", 
            highlightthickness=1
        )
        
        self.listbox = tk.Listbox(
            self.listbox_frame, 
            height=6, 
            font=font or FONT_NORMAL,
            relief="flat", 
            borderwidth=0, 
            selectbackground="#007bff",
            selectforeground="#ffffff", 
            bg="#ffffff", 
            fg="#212529"
        )
        
        scrollbar = ttk.Scrollbar(self.listbox_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Initially hide dropdown
        self.dropdown_visible = False
        
        # Set placeholder
        if self.placeholder:
            self._set_placeholder()
        
        # Bind events
        self.var.trace("w", self.on_text_change)
        self.entry.bind("<KeyPress>", self.on_key_press)
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        self.listbox.bind("<Double-Button-1>", self.on_listbox_select)
        self.listbox.bind("<Return>", self.on_listbox_select)
        
        self.update_listbox()
    
    def _set_placeholder(self):
        """Set placeholder text"""
        if not self.var.get():
            self.entry.configure(fg="gray")
            self.var.set(self.placeholder)
    
    def _clear_placeholder(self):
        """Clear placeholder text"""
        if self.var.get() == self.placeholder:
            self.var.set("")
            self.entry.configure(fg="black")
    
    def set_values(self, values):
        """Update available values"""
        self.values = values[:]
        self.filtered_values = values[:]
        self.update_listbox()
    
    def get(self):
        """Get current value"""
        value = self.var.get()
        return "" if value == self.placeholder else value
    
    def set(self, value):
        """Set current value"""
        self.entry.configure(fg="black")
        self.var.set(value)
        self.selected_value = value

    def clear(self):
        """Clear the current value and restore the placeholder."""
        self.hide_dropdown()
        self.selected_value = ""
        self.entry.configure(fg="black")
        self.var.set("")
        self.filtered_values = self.values[:]
        self.update_listbox()
        if self.placeholder:
            self._set_placeholder()
    
    def on_text_change(self, *args):
        """Filter values based on current text"""
        current_text = self.get().lower()
        
        if current_text and current_text != self.placeholder.lower():
            self.filtered_values = [v for v in self.values if current_text in v.lower()]
            self.update_listbox()
            
            if self.filtered_values and not self.dropdown_visible:
                self.show_dropdown()
            elif not self.filtered_values and self.dropdown_visible:
                self.hide_dropdown()
    
    def on_key_press(self, event):
        """Handle key presses"""
        if event.keysym == "Down" and self.dropdown_visible:
            self.listbox.focus_set()
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)
            return "break"
        elif event.keysym == "Escape":
            self.hide_dropdown()
        elif event.keysym == "Return":
            if self.dropdown_visible and self.filtered_values:
                self.select_first_item()
            return "break"
    
    def on_focus_in(self, event):
        """Handle focus in"""
        self._clear_placeholder()
        if self.filtered_values:
            self.show_dropdown()
    
    def on_focus_out(self, event):
        """Handle focus out"""
        self.after(200, self.check_focus)
        if not self.get():
            self._set_placeholder()
    
    def check_focus(self):
        """Check if focus is still within widget"""
        try:
            focused = self.focus_get()
            if focused not in [self.entry, self.listbox]:
                self.hide_dropdown()
        except (KeyError, tk.TclError):
            self.hide_dropdown()
    
    def on_listbox_select(self, event):
        """Handle listbox selection"""
        selection = self.listbox.curselection()
        if selection:
            value = self.filtered_values[selection[0]]
            self.set(value)
            self.hide_dropdown()
            self.entry.focus_set()
    
    def select_first_item(self):
        """Select first item in filtered list"""
        if self.filtered_values:
            self.set(self.filtered_values[0])
            self.hide_dropdown()
    
    def update_listbox(self):
        """Update listbox contents"""
        self.listbox.delete(0, tk.END)
        for value in self.filtered_values:
            self.listbox.insert(tk.END, value)
    
    def show_dropdown(self):
        """Show dropdown listbox"""
        if not self.dropdown_visible:
            self.listbox_frame.pack(fill="x", pady=(2, 0))
            self.dropdown_visible = True
    
    def hide_dropdown(self):
        """Hide dropdown listbox"""
        if self.dropdown_visible:
            self.listbox_frame.pack_forget()
            self.dropdown_visible = False

class StatusBar(tk.Frame):
    """Status bar for showing application status"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Έτοιμο")
        
        # Status label
        self.status_label = tk.Label(
            self, 
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            font=("Arial", 9),
            padx=10
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        
        # Time label
        self.time_var = tk.StringVar()
        self.time_label = tk.Label(
            self,
            textvariable=self.time_var,
            relief="sunken",
            anchor="e",
            font=("Arial", 9),
            padx=10
        )
        self.time_label.pack(side="right")
        
        # Update time
        self.update_time()
    
    def set_status(self, message):
        """Set status message"""
        self.status_var.set(message)
        # Auto-clear after 5 seconds
        self.after(5000, lambda: self.status_var.set("Έτοιμο"))
    
    def update_time(self):
        """Update time display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_var.set(current_time)
        self.after(1000, self.update_time)

class ProgressDialog:
    """Progress dialog for long operations"""
    
    def __init__(self, parent, title="Παρακαλώ περιμένετε...", message="Επεξεργασία..."):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("400x150")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (150 // 2)
        self.window.geometry(f"400x150+{x}+{y}")
        
        # Message label
        self.message_var = tk.StringVar(value=message)
        message_label = tk.Label(
            self.window, 
            textvariable=self.message_var,
            font=("Arial", 12),
            pady=20
        )
        message_label.pack()
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.window, 
            mode='indeterminate',
            length=300
        )
        self.progress.pack(pady=10)
        self.progress.start()
    
    def update_message(self, message):
        """Update progress message"""
        self.message_var.set(message)
        self.window.update()
    
    def close(self):
        """Close progress dialog"""
        self.progress.stop()
        self.window.destroy()

class ConfirmDialog:
    """Custom confirmation dialog with better styling"""
    
    def __init__(self, parent, title, message, icon="question"):
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("400x200")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.window.winfo_screenheight() // 2) - (200 // 2)
        self.window.geometry(f"400x200+{x}+{y}")
        
        # Icon and message frame
        content_frame = tk.Frame(self.window)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Icon
        icon_map = {
            "question": "❓",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️"
        }
        
        icon_label = tk.Label(
            content_frame, 
            text=icon_map.get(icon, "❓"),
            font=("Arial", 24)
        )
        icon_label.pack(pady=(0, 10))
        
        # Message
        message_label = tk.Label(
            content_frame,
            text=message,
            font=("Arial", 11),
            wraplength=350,
            justify="center"
        )
        message_label.pack(pady=(0, 20))
        
        # Buttons
        button_frame = tk.Frame(content_frame)
        button_frame.pack()
        
        yes_btn = ModernButton(
            button_frame, 
            text="✅ Ναι", 
            style="success",
            command=self.yes_clicked
        )
        yes_btn.pack(side="left", padx=10)
        
        no_btn = ModernButton(
            button_frame, 
            text="❌ Όχι", 
            style="danger",
            command=self.no_clicked
        )
        no_btn.pack(side="left", padx=10)
        
        # Bind Enter and Escape keys
        self.window.bind("<Return>", lambda e: self.yes_clicked())
        self.window.bind("<Escape>", lambda e: self.no_clicked())
        
        # Focus on Yes button
        yes_btn.focus_set()
    
    def yes_clicked(self):
        """Handle Yes button click"""
        self.result = True
        self.window.destroy()
    
    def no_clicked(self):
        """Handle No button click"""
        self.result = False
        self.window.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.window.wait_window()
        return self.result

class ValidationMixin:
    """Mixin class for input validation"""
    
    @staticmethod
    def validate_required_fields(fields_dict):
        """Validate that required fields are not empty"""
        empty_fields = []
        for field_name, field_value in fields_dict.items():
            if not field_value or not field_value.strip():
                empty_fields.append(field_name)
        
        if empty_fields:
            return False, f"Τα ακόλουθα πεδία είναι υποχρεωτικά: {', '.join(empty_fields)}"
        return True, ""
    
    @staticmethod
    def validate_number(value, field_name, min_value=None, max_value=None):
        """Validate numeric input"""
        try:
            num_value = float(value)
            
            if min_value is not None and num_value < min_value:
                return False, f"{field_name} πρέπει να είναι >= {min_value}"
            
            if max_value is not None and num_value > max_value:
                return False, f"{field_name} πρέπει να είναι <= {max_value}"
            
            return True, num_value
        except ValueError:
            return False, f"{field_name} πρέπει να είναι έγκυρος αριθμός"
    
    @staticmethod
    def validate_plate(plate):
        """Validate vehicle plate format"""
        if not plate or len(plate.strip()) < 3:
            return False, "Η πινακίδα πρέπει να έχει τουλάχιστον 3 χαρακτήρες"
        
        # Add more specific validation if needed
        return True, plate.strip().upper()

class TooltipManager:
    """Tooltip manager for better user guidance"""
    
    def __init__(self):
        self.tooltips = {}
    
    def add_tooltip(self, widget, text):
        """Add tooltip to widget"""
        def on_enter(event):
            self.show_tooltip(event.widget, text)
        
        def on_leave(event):
            self.hide_tooltip()
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def show_tooltip(self, widget, text):
        """Show tooltip"""
        if hasattr(self, 'tooltip_window'):
            self.hide_tooltip()
        
        self.tooltip_window = tk.Toplevel()
        self.tooltip_window.wm_overrideredirect(True)
        
        label = tk.Label(
            self.tooltip_window,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Arial", 9)
        )
        label.pack()
        
        # Position tooltip
        x = widget.winfo_rootx() + 25
        y = widget.winfo_rooty() + 25
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
    
    def hide_tooltip(self):
        """Hide tooltip"""
        if hasattr(self, 'tooltip_window'):
            self.tooltip_window.destroy()
            del self.tooltip_window
