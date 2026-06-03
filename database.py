"""
Database management for Fleet Management System
"""
import sqlite3
import logging
from config import DB_PATH

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
            logging.info("Database connected successfully")
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables"""
        try:
            # Vehicles table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT UNIQUE NOT NULL,
                    brand TEXT,
                    vtype TEXT,
                    purpose TEXT,
                    photo_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Drivers table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    surname TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Movements table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movement_number INTEGER UNIQUE,
                    vehicle_id INTEGER NOT NULL,
                    driver_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    start_km INTEGER NOT NULL,
                    end_km INTEGER,
                    route TEXT,
                    purpose TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
                )
            """)
            
            # Fuel table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS fuel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    driver_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    liters REAL NOT NULL,
                    mileage INTEGER,
                    cost REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE,
                    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
                )
            """)
            
            # Tank table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS tank (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    liters REAL NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('fill', 'consume')),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Pump table - για τον μετρητή της αντλίας
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pump (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    reading REAL NOT NULL,
                    liters_dispensed REAL NOT NULL,
                    vehicle_plate TEXT,
                    driver_name TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Purposes table - για τη διαχείριση σκοπών
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS purposes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System settings table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_name TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize default settings
            self._initialize_settings()
            
            # Initialize default purposes
            self._initialize_purposes()
            
            # Add indexes for better performance
            self._create_indexes()
            
            self.conn.commit()
            logging.info("Database tables created/verified successfully")

            # Run lightweight migrations for new columns
            self._run_migrations()
            
        except Exception as e:
            logging.error(f"Error creating tables: {e}")
            raise
    
    def _initialize_settings(self):
        """Initialize default system settings"""
        default_settings = [
            ('theme', 'light', 'Θέμα εφαρμογής'),
            ('auto_backup', 'true', 'Αυτόματο backup'),
            ('backup_interval', '7', 'Διάστημα backup σε ημέρες'),
            ('app_version', '2.0', 'Έκδοση εφαρμογής'),
            ('last_backup', '', 'Τελευταίο backup'),
            ('pump_current_reading', '1768782', 'Τρέχουσα μέτρηση αντλίας'),
        ]
        
        for setting_name, setting_value, notes in default_settings:
            self.cursor.execute("""
                INSERT OR IGNORE INTO system_settings (setting_name, setting_value, notes)
                VALUES (?, ?, ?)
            """, (setting_name, setting_value, notes))
        
        # Do not create an automatic starting tank balance.
        # The first real user action must be the measured initial tank quantity.
    
    def _initialize_purposes(self):
        """Initialize default purposes"""
        default_purposes = [
            ('Αποκομιδή', 'Αποκομιδή απορριμμάτων', 'operation'),
            ('Απόφραξη', 'Απόφραξη αποχετεύσεων', 'operation'),
            ('Μεταφορά', 'Μεταφορά υλικών', 'transport'),
            ('Συντήρηση', 'Εργασίες συντήρησης', 'maintenance'),
            ('Καθαρισμός', 'Καθαρισμός δρόμων/χώρων', 'cleaning'),
            ('Επισκευή', 'Επισκευαστικές εργασίες', 'repair'),
            ('Ελέγχος', 'Έλεγχος εγκαταστάσεων', 'inspection'),
        ]
        
        for name, description, category in default_purposes:
            self.cursor.execute("""
                INSERT OR IGNORE INTO purposes (name, description, category)
                VALUES (?, ?, ?)
            """, (name, description, category))
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_movements_date ON movements(date)",
            "CREATE INDEX IF NOT EXISTS idx_movements_vehicle ON movements(vehicle_id)",
            "CREATE INDEX IF NOT EXISTS idx_movements_driver ON movements(driver_id)",
            "CREATE INDEX IF NOT EXISTS idx_fuel_date ON fuel(date)",
            "CREATE INDEX IF NOT EXISTS idx_fuel_vehicle ON fuel(vehicle_id)",
            "CREATE INDEX IF NOT EXISTS idx_tank_date ON tank(date)",
            "CREATE INDEX IF NOT EXISTS idx_pump_date ON pump(date)",
            "CREATE INDEX IF NOT EXISTS idx_pump_reading ON pump(reading)",
            "CREATE INDEX IF NOT EXISTS idx_purposes_name ON purposes(name)",
            "CREATE INDEX IF NOT EXISTS idx_purposes_category ON purposes(category)",
            "CREATE INDEX IF NOT EXISTS idx_purposes_active ON purposes(active)",
        ]
        
        for index_sql in indexes:
            try:
                self.cursor.execute(index_sql)
            except sqlite3.OperationalError:
                pass  # Index might already exist

    def _run_migrations(self):
        """Apply simple schema migrations (idempotent)"""
        try:
            # Vehicles: ensure purpose column exists (old name was notes)
            self.cursor.execute("PRAGMA table_info(vehicles)")
            vehicle_cols = [r[1] for r in self.cursor.fetchall()]
            if 'purpose' not in vehicle_cols:
                if 'notes' in vehicle_cols:
                    try:
                        self.cursor.execute("ALTER TABLE vehicles RENAME COLUMN notes TO purpose")
                    except Exception:
                        self.cursor.execute("ALTER TABLE vehicles ADD COLUMN purpose TEXT")
                        self.cursor.execute("UPDATE vehicles SET purpose = notes WHERE purpose IS NULL")
                else:
                    self.cursor.execute("ALTER TABLE vehicles ADD COLUMN purpose TEXT")

            # Movements: ensure purpose column exists (old name was notes)
            self.cursor.execute("PRAGMA table_info(movements)")
            mov_cols = [r[1] for r in self.cursor.fetchall()]
            if 'purpose' not in mov_cols:
                if 'notes' in mov_cols:
                    try:
                        self.cursor.execute("ALTER TABLE movements RENAME COLUMN notes TO purpose")
                    except Exception:
                        self.cursor.execute("ALTER TABLE movements ADD COLUMN purpose TEXT")
                        self.cursor.execute("UPDATE movements SET purpose = notes WHERE purpose IS NULL")
                else:
                    self.cursor.execute("ALTER TABLE movements ADD COLUMN purpose TEXT")

            self.conn.commit()
            logging.info("Migrations applied (purpose column ensured).")
        except Exception as e:
            logging.error(f"Migration error: {e}")
    
    def get_setting(self, setting_name, default_value=""):
        """Get a system setting value"""
        try:
            self.cursor.execute(
                "SELECT setting_value FROM system_settings WHERE setting_name = ?",
                (setting_name,)
            )
            result = self.cursor.fetchone()
            return result[0] if result else default_value
        except Exception as e:
            logging.error(f"Error getting setting {setting_name}: {e}")
            return default_value
    
    def set_setting(self, setting_name, setting_value, notes=""):
        """Set a system setting value"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO system_settings (setting_name, setting_value, notes, updated_at)
                VALUES (?, ?, ?, ?)
            """, (setting_name, setting_value, notes, datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Error setting {setting_name}: {e}")
            raise
    
    def get_next_movement_number(self):
        """Get the next unique movement number"""
        current_counter = int(self.get_setting('movement_counter', '0'))
        self.cursor.execute("SELECT COALESCE(MAX(movement_number), 0) FROM movements")
        max_existing = self.cursor.fetchone()[0] or 0
        next_number = max(current_counter, max_existing) + 1
        self.set_setting('movement_counter', str(next_number))
        return next_number
    
    def backup_database(self, backup_path):
        """Create a backup of the database"""
        try:
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            self.set_setting('last_backup', datetime.now().isoformat())
            logging.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logging.error(f"Backup error: {e}")
            return False

    def get_pump_reading(self):
        """Get current pump reading"""
        try:
            return float(self.get_setting('pump_current_reading', '0'))
        except:
            return 0.0

    def update_pump_reading(self, new_reading, liters_dispensed, vehicle_plate="", driver_name="", notes=""):
        """Update pump reading and log the transaction"""
        try:
            current_reading = self.get_pump_reading()
            
            # Log pump transaction
            self.cursor.execute("""
                INSERT INTO pump (date, reading, liters_dispensed, vehicle_plate, driver_name, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), new_reading, liters_dispensed, 
                  vehicle_plate, driver_name, notes))
            
            # Update current reading setting
            self.set_setting('pump_current_reading', str(new_reading))
            self.conn.commit()
            
            logging.info(f"Pump reading updated: {current_reading} -> {new_reading} (+{liters_dispensed}L)")
            return True
            
        except Exception as e:
            logging.error(f"Error updating pump reading: {e}")
            return False

    def get_pump_history(self, limit=50):
        """Get pump transaction history"""
        try:
            self.cursor.execute("""
                SELECT date, reading, liters_dispensed, vehicle_plate, driver_name, notes
                FROM pump 
                ORDER BY date DESC, id DESC
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"Error getting pump history: {e}")
            return []
    
    # ===== DRIVER MANAGEMENT METHODS =====
    
    def get_all_drivers(self):
        """Get all drivers from database"""
        try:
            self.cursor.execute("""
                SELECT id, name, surname, notes, created_at
                FROM drivers 
                ORDER BY name, surname
            """)
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"Error getting all drivers: {e}")
            return []
    
    def get_driver_by_id(self, driver_id):
        """Get driver by ID"""
        try:
            self.cursor.execute("""
                SELECT id, name, surname, notes, created_at
                FROM drivers 
                WHERE id = ?
            """, (driver_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logging.error(f"Error getting driver by ID {driver_id}: {e}")
            return None
    
    # ===== PURPOSE MANAGEMENT METHODS =====
    
    def get_purposes(self, category=None, active_only=True):
        """Get all purposes, optionally filtered by category"""
        try:
            query = "SELECT id, name, description, category, active FROM purposes"
            params = []
            
            conditions = []
            if active_only:
                conditions.append("active = 1")
            if category:
                conditions.append("category = ?")
                params.append(category)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY name"
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logging.error(f"Error getting purposes: {e}")
            return []
    
    def get_purpose_names(self, category=None, active_only=True):
        """Get list of purpose names"""
        purposes = self.get_purposes(category, active_only)
        return [purpose[1] for purpose in purposes]  # purpose[1] is the name
    
    def add_purpose(self, name, description="", category="general"):
        """Add a new purpose"""
        try:
            self.cursor.execute("""
                INSERT INTO purposes (name, description, category)
                VALUES (?, ?, ?)
            """, (name, description, category))
            self.conn.commit()
            logging.info(f"Purpose added: {name}")
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(f"Purpose '{name}' already exists")
            return None
        except Exception as e:
            logging.error(f"Error adding purpose: {e}")
            return None
    
    def update_purpose(self, purpose_id, name=None, description=None, category=None, active=None):
        """Update an existing purpose"""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            if active is not None:
                updates.append("active = ?")
                params.append(active)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(purpose_id)
            
            query = f"UPDATE purposes SET {', '.join(updates)} WHERE id = ?"
            self.cursor.execute(query, params)
            self.conn.commit()
            
            logging.info(f"Purpose updated: ID {purpose_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error updating purpose: {e}")
            return False
    
    def delete_purpose(self, purpose_id):
        """Delete a purpose (soft delete - mark as inactive)"""
        try:
            self.cursor.execute("""
                UPDATE purposes SET active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (purpose_id,))
            self.conn.commit()
            logging.info(f"Purpose deactivated: ID {purpose_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting purpose: {e}")
            return False
    
    def restore_purpose(self, purpose_id):
        """Restore a deactivated purpose"""
        try:
            self.cursor.execute("""
                UPDATE purposes SET active = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (purpose_id,))
            self.conn.commit()
            logging.info(f"Purpose restored: ID {purpose_id}")
            return True
        except Exception as e:
            logging.error(f"Error restoring purpose: {e}")
            return False
    
    # Driver Analytics Methods
    def get_driver_analytics(self, driver_id, start_date=None, end_date=None):
        """Get comprehensive analytics for a driver"""
        try:
            analytics = {}
            
            # Basic info
            driver_info = self.get_driver_by_id(driver_id)
            if not driver_info:
                return None
            
            analytics['driver_name'] = driver_info[1]  # name field
            analytics['driver_id'] = driver_id
            
            # Date filter condition
            date_condition = ""
            date_params = [driver_id]
            
            if start_date and end_date:
                date_condition = " AND date BETWEEN ? AND ?"
                date_params.extend([start_date, end_date])
            elif start_date:
                date_condition = " AND date >= ?"
                date_params.append(start_date)
            elif end_date:
                date_condition = " AND date <= ?"
                date_params.append(end_date)
            
            # Total movements
            self.cursor.execute(f"""
                SELECT COUNT(*) FROM movements 
                WHERE driver_id = ?{date_condition}
            """, date_params)
            analytics['total_movements'] = self.cursor.fetchone()[0]
            
            # Total kilometers
            self.cursor.execute(f"""
                SELECT SUM(end_km - start_km) as total_km
                FROM movements 
                WHERE driver_id = ? AND end_km IS NOT NULL{date_condition}
            """, date_params)
            result = self.cursor.fetchone()[0]
            analytics['total_kilometers'] = result if result else 0
            
            # Total fuel consumed
            self.cursor.execute(f"""
                SELECT SUM(liters) as total_fuel
                FROM fuel 
                WHERE driver_id = ?{date_condition}
            """, date_params)
            result = self.cursor.fetchone()[0]
            analytics['total_fuel_liters'] = result if result else 0
            
            # Total fuel cost
            self.cursor.execute(f"""
                SELECT SUM(cost) as total_cost
                FROM fuel 
                WHERE driver_id = ?{date_condition}
            """, date_params)
            result = self.cursor.fetchone()[0]
            analytics['total_fuel_cost'] = result if result else 0
            
            # Average consumption (km per liter)
            if analytics['total_fuel_liters'] > 0:
                analytics['avg_consumption_km_per_liter'] = round(
                    analytics['total_kilometers'] / analytics['total_fuel_liters'], 2
                )
            else:
                analytics['avg_consumption_km_per_liter'] = 0
            
            # Average cost per kilometer
            if analytics['total_kilometers'] > 0:
                analytics['avg_cost_per_km'] = round(
                    analytics['total_fuel_cost'] / analytics['total_kilometers'], 3
                )
            else:
                analytics['avg_cost_per_km'] = 0
            
            # Most used vehicles
            self.cursor.execute(f"""
                SELECT v.plate, COUNT(*) as usage_count, SUM(m.end_km - m.start_km) as total_km
                FROM movements m
                JOIN vehicles v ON m.vehicle_id = v.id
                WHERE m.driver_id = ? AND m.end_km IS NOT NULL{date_condition}
                GROUP BY v.id, v.plate
                ORDER BY usage_count DESC
                LIMIT 5
            """, date_params)
            analytics['most_used_vehicles'] = [
                {
                    'plate': row[0], 
                    'usage_count': row[1], 
                    'total_km': row[2] if row[2] else 0
                }
                for row in self.cursor.fetchall()
            ]
            
            # Monthly breakdown
            self.cursor.execute(f"""
                SELECT 
                    strftime('%Y-%m', date) as month,
                    COUNT(*) as movements,
                    SUM(end_km - start_km) as km,
                    (SELECT SUM(liters) FROM fuel f WHERE f.driver_id = m.driver_id 
                     AND strftime('%Y-%m', f.date) = strftime('%Y-%m', m.date)) as fuel
                FROM movements m
                WHERE driver_id = ? AND end_km IS NOT NULL{date_condition}
                GROUP BY strftime('%Y-%m', date)
                ORDER BY month DESC
                LIMIT 12
            """, date_params)
            analytics['monthly_breakdown'] = [
                {
                    'month': row[0],
                    'movements': row[1],
                    'kilometers': row[2] if row[2] else 0,
                    'fuel_liters': row[3] if row[3] else 0
                }
                for row in self.cursor.fetchall()
            ]
            
            # Purpose breakdown
            self.cursor.execute(f"""
                SELECT purpose, COUNT(*) as count, SUM(end_km - start_km) as total_km
                FROM movements 
                WHERE driver_id = ? AND end_km IS NOT NULL{date_condition}
                GROUP BY purpose
                ORDER BY count DESC
            """, date_params)
            analytics['purpose_breakdown'] = [
                {
                    'purpose': row[0] if row[0] else 'Άλλο',
                    'count': row[1],
                    'total_km': row[2] if row[2] else 0
                }
                for row in self.cursor.fetchall()
            ]
            
            # Efficiency per 100km (liters per 100km)
            if analytics['total_kilometers'] > 0:
                analytics['efficiency_per_100km'] = round(
                    (analytics['total_fuel_liters'] / analytics['total_kilometers']) * 100, 2
                )
            else:
                analytics['efficiency_per_100km'] = 0
            
            return analytics
            
        except Exception as e:
            logging.error(f"Error getting driver analytics: {e}")
            return None
    
    def get_all_drivers_summary(self, start_date=None, end_date=None):
        """Get summary analytics for all drivers"""
        try:
            drivers = self.get_all_drivers()
            summary = []
            
            for driver in drivers:
                driver_id = driver[0]
                analytics = self.get_driver_analytics(driver_id, start_date, end_date)
                if analytics:
                    summary.append({
                        'driver_id': driver_id,
                        'driver_name': analytics['driver_name'],
                        'total_movements': analytics['total_movements'],
                        'total_kilometers': analytics['total_kilometers'],
                        'total_fuel_liters': analytics['total_fuel_liters'],
                        'total_fuel_cost': analytics['total_fuel_cost'],
                        'avg_consumption': analytics['avg_consumption_km_per_liter'],
                        'avg_cost_per_km': analytics['avg_cost_per_km']
                    })
            
            # Sort by total kilometers descending
            summary.sort(key=lambda x: x['total_kilometers'], reverse=True)
            return summary
            
        except Exception as e:
            logging.error(f"Error getting drivers summary: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        try:
            if self.conn:
                self.conn.close()
                logging.info("Database connection closed")
        except Exception as e:
            logging.error(f"Error closing database: {e}")
