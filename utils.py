"""
Utility functions for Fleet Management System
"""
import os
import logging
import hashlib
from datetime import datetime
import csv
import shutil
from tkinter import messagebox, filedialog

def normalize_plate(plate):
    """Normalize vehicle plate"""
    return plate.strip().upper() if plate else ""

def normalize_name(name):
    """Normalize person name"""
    return name.strip().title() if name else ""

def ensure_dir(path):
    """Ensure directory exists"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Error creating directory {path}: {e}")
        return False

def validate_date(date_string):
    """Validate date format"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def format_currency(amount):
    """Format currency amount"""
    return f"{amount:.2f} €" if amount else "0.00 €"

def format_distance(km):
    """Format distance in kilometers"""
    return f"{km:.1f} χλμ" if km else "0.0 χλμ"

def format_fuel(liters):
    """Format fuel amount"""
    return f"{liters:.1f} L" if liters else "0.0 L"

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def export_to_csv(data, headers, filename=None):
    """Generic CSV export function"""
    if not filename:
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialname=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
    
    if filename:
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(data)
            
            messagebox.showinfo("✅ Επιτυχία", f"Τα δεδομένα εξήχθησαν επιτυχώς:\n{filename}")
            return True
        except Exception as e:
            messagebox.showerror("❌ Σφάλμα", f"Σφάλμα κατά την εξαγωγή: {str(e)}")
            return False
    
    return False

def backup_file(source_path, backup_dir=None):
    """Create backup of a file"""
    try:
        if backup_dir is None:
            from config import BACKUPS_DIR
            backup_dir = BACKUPS_DIR

        ensure_dir(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(source_path)
        backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
        
        import shutil
        shutil.copy2(source_path, backup_path)
        
        logging.info(f"File backed up: {source_path} -> {backup_path}")
        return backup_path
    except Exception as e:
        logging.error(f"Backup error: {e}")
        return None

def calculate_fuel_efficiency(total_km, total_fuel):
    """Calculate fuel efficiency"""
    if total_fuel > 0:
        return total_km / total_fuel
    return 0

def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except:
        return 0

class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def is_valid_plate(plate):
        """Validate vehicle plate"""
        if not plate or len(plate.strip()) < 3:
            return False, "Η πινακίδα πρέπει να έχει τουλάχιστον 3 χαρακτήρες"
        
        # Greek plate format validation (optional)
        plate = plate.strip().upper()
        if len(plate) > 10:
            return False, "Η πινακίδα δεν μπορεί να έχει περισσότερους από 10 χαρακτήρες"
        
        return True, plate
    
    @staticmethod
    def is_valid_km(km_value, min_km=0):
        """Validate kilometer value"""
        try:
            km = int(km_value)
            if km < min_km:
                return False, f"Τα χιλιόμετρα πρέπει να είναι >= {min_km}"
            if km > 9999999:  # Reasonable upper limit
                return False, "Τα χιλιόμετρα είναι πολύ μεγάλα"
            return True, km
        except ValueError:
            return False, "Τα χιλιόμετρα πρέπει να είναι έγκυρος αριθμός"
    
    @staticmethod
    def is_valid_fuel(fuel_value):
        """Validate fuel amount"""
        try:
            fuel = float(fuel_value)
            if fuel <= 0:
                return False, "Τα λίτρα πρέπει να είναι θετικός αριθμός"
            if fuel > 1000:  # Reasonable upper limit
                return False, "Τα λίτρα είναι πολύ μεγάλα"
            return True, fuel
        except ValueError:
            return False, "Τα λίτρα πρέπει να είναι έγκυρος αριθμός"
    
    @staticmethod
    def is_valid_name(name):
        """Validate person name"""
        if not name or len(name.strip()) < 2:
            return False, "Το όνομα πρέπει να έχει τουλάχιστον 2 χαρακτήρες"
        
        name = name.strip()
        if len(name) > 50:
            return False, "Το όνομα δεν μπορεί να έχει περισσότερους από 50 χαρακτήρες"
        
        return True, name.title()

def log_user_action(action, details=""):
    """Log user actions for audit trail"""
    try:
        logging.info(f"USER ACTION: {action} - {details}")
    except Exception as e:
        print(f"Logging error: {e}")
