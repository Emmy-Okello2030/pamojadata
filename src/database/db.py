# db.py — PamojaData Database Engine
# Sets up SQLite database with all tables needed across the platform

import sqlite3
import os

# Database file will be created in the data/ folder
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'pamojadata.db')

def get_connection():
    """Returns a connection to the PamojaData database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
    return conn


def initialise_database():
    """
    Creates all tables if they don't exist.
    Run this once on first launch.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Organisations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organisations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            donor_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Programmes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS programmes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER,
            name TEXT NOT NULL,
            sector TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'Active',
            FOREIGN KEY (org_id) REFERENCES organisations(id)
        )
    ''')

    # Indicators table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            programme_id INTEGER,
            indicator_code TEXT,
            indicator_name TEXT NOT NULL,
            sector TEXT,
            target REAL,
            achieved REAL,
            reporting_period TEXT,
            location TEXT,
            notes TEXT,
            data_source TEXT DEFAULT 'Manual Upload',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (programme_id) REFERENCES programmes(id)
        )
    ''')

    # Data quality log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quality_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id INTEGER,
            issue_type TEXT,
            issue_description TEXT,
            resolved INTEGER DEFAULT 0,
            flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (indicator_id) REFERENCES indicators(id)
        )
    ''')

    # Reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            programme_id INTEGER,
            report_period TEXT,
            donor_type TEXT,
            narrative TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (programme_id) REFERENCES programmes(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ PamojaData database initialised successfully.")


def save_indicators(df, programme_id, mapping, data_source="Manual Upload"):
    """
    Saves a dataframe of indicators into the database.
    """
    conn = get_connection()
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO indicators 
            (programme_id, indicator_name, sector, target, achieved, 
             reporting_period, location, notes, data_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            programme_id,
            row[mapping['indicator_name']],
            row[mapping['sector']],
            row[mapping['target']],
            row[mapping['achieved']],
            row.get(mapping.get('period', ''), ''),
            row.get(mapping.get('location', ''), ''),
            row.get('Notes', ''),
            data_source
        ))

    conn.commit()
    conn.close()
    print(f"✅ {len(df)} indicators saved to database.")


def get_indicators(programme_id):
    """Retrieves all indicators for a given programme."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM indicators WHERE programme_id = ?', (programme_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_report(programme_id=None, report_period=None, donor_type=None, narrative=None):
    """Saves a generated report to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reports (programme_id, report_period, donor_type, narrative)
        VALUES (?, ?, ?, ?)
    ''', (programme_id, report_period, donor_type, narrative))
    conn.commit()
    conn.close()
    print("✅ Report saved to database.")


if __name__ == "__main__":
    initialise_database()