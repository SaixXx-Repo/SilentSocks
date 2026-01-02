import sqlite3
import pandas as pd
import os

DB_NAME = "sales_data.db"

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Enable foreign keys
    c.execute("PRAGMA foreign_keys = ON")
    
    # Create customers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_number TEXT PRIMARY KEY,
            name TEXT,
            address TEXT,
            zip_code TEXT,
            city TEXT,
            country TEXT,
            customer_group TEXT
        )
    ''')
    
    # Create sales table with new schema
    # We drop and recreate if schema changed significantly (for development speed)
    # Check if table has new columns, if not, recreate
    try:
        c.execute("SELECT article_id FROM sales LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS sales")
        c.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                customer_number TEXT,
                article_id TEXT,
                article_name TEXT,
                quantity INTEGER,
                tb_amount REAL, -- User emphasized TB i kr
                sales_amount REAL, -- Total sales excl VAT
                source_file TEXT,
                FOREIGN KEY (customer_number) REFERENCES customers(customer_number)
            )
        ''')
    
    # Create settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_customers(df):
    """
    Upsert customer data.
    Assumes df has columns matching database schema.
    """
    if df.empty:
        return
        
    conn = sqlite3.connect(DB_NAME)
    # Convert to list of dicts for easier handling
    records = df.to_dict('records')
    
    c = conn.cursor()
    for row in records:
        c.execute('''
            INSERT INTO customers (customer_number, name, address, zip_code, city, country, customer_group)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(customer_number) DO UPDATE SET
                name=excluded.name,
                address=excluded.address,
                zip_code=excluded.zip_code,
                city=excluded.city,
                country=excluded.country,
                customer_group=excluded.customer_group
        ''', (
            str(row.get('customer_number', '')),
            row.get('name'),
            row.get('address'),
            str(row.get('zip_code', '')),
            row.get('city'),
            row.get('country'),
            row.get('customer_group')
        ))
    
    conn.commit()
    conn.close()

def save_sales_data(df, source_filename):
    """
    Save the sales DataFrame to the database.
    """
    if df.empty:
        return

    conn = sqlite3.connect(DB_NAME)
    
    # Add source_file column
    data_to_save = df.copy()
    data_to_save['source_file'] = source_filename
    
    # Ensure columns match table schema order/names slightly different from raw dataframe
    # Expected DF columns: date, customer_number, article_id, article_name, quantity, tb_amount, sales_amount
    
    # Write to SQLite
    data_to_save.to_sql('sales', conn, if_exists='append', index=False)
    conn.close()

def get_all_data():
    """
    Retrieve sales data joined with customer data.
    """
    conn = sqlite3.connect(DB_NAME)
    try:
        query = '''
            SELECT 
                s.date,
                s.article_id,
                s.article_name as article,
                s.customer_number,
                s.quantity,
                s.tb_amount,
                s.sales_amount,
                s.sales_amount as total_amount, -- Alias for backward compatibility
                c.name as customer,
                c.country,
                c.customer_group,
                c.city
            FROM sales s
            LEFT JOIN customers c ON s.customer_number = c.customer_number
        '''
        df = pd.read_sql_query(query, conn)
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            
    except Exception as e:
        print(f"Error reading database: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def get_customer_count():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM customers")
    count = c.fetchone()[0]
    conn.close()
    return count

def clear_database():
    """Delete all records from sales and customers tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM sales")
    c.execute("DELETE FROM customers")
    conn.commit()
    conn.close()

def save_setting(key, value):
    """Save a setting (e.g., API key) to the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def get_setting(key):
    """Retrieve a setting from the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def delete_setting(key):
    """Delete a setting from the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM settings WHERE key = ?", (key,))
    conn.commit()
    conn.close()
