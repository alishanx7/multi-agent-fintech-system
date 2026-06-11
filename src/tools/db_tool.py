import sqlite3
import os

DB_PATH = 'fintech_compliance.db'

def init_compliance_db():
    """
    Initializes a local SQLite database and seeds a mock corporate blacklist
    for compliance and risk screening.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS corporate_blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT UNIQUE NOT NULL,
        risk_reason TEXT NOT NULL
    )
    """)
    
    # Seed initial test compliance data records safely
    mock_blacklist = [
        ('Acme Fraud Corp', 'Active ongoing AML investigation involvement'),
        ('Shell Ventures Ltd', 'Sanctioned entity tracking matching offshore capital lines'),
        ('Shadow Holdings', 'High volume transaction chargeback frequency failures')
    ]
    
    try:
        cursor.executemany(
            "INSERT OR IGNORE INTO corporate_blacklist (company_name, risk_reason) VALUES (?, ?)", 
            mock_blacklist
        )
        conn.commit()
    except Exception as e:
        print(f"Database seeding note: {e}")
    finally:
        conn.close()


def check_compliance_blacklist(company_name: str) -> dict:
    """
    Queries the database to see if an applicant entity is blacklisted.
    """
    init_compliance_db()  # Ensures the database and records exist before checking
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT risk_reason FROM corporate_blacklist WHERE LOWER(company_name) = LOWER(?)", 
        (company_name.strip(),)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"status": "FAILED", "flag_reason": result[0]}
    return {"status": "PASSED", "flag_reason": None}