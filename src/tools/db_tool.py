import sqlite3
import os
from crewai.tools import tool

DB_PATH = "data/fintech.db"

def init_compliance_db():
    """Initializing the SQLite database and populates a dummy blacklist for testing."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the blacklist table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compliance_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL UNIQUE,
            risk_category TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            details TEXT
        )
    ''')
    
    # Insert some sample mock fraudulent corporate names for your exception testing
    mock_blacklist = [
        ("Shell Corp Logistics Ltd", "Shell Company / Money Laundering", 95, "Flagged by FIU for suspicious offshore routing"),
        ("Apex Global Logistics Solutions Pvt Ltd", "High Risk / Audit Pending", 85, "Matches company name exactly for test exception handling"),
        ("Phantom Holdings Inc", "Tax Evasion", 90, "Global regulatory sanctions match")
    ]
    
    try:
        cursor.executemany('''
            INSERT OR IGNORE INTO compliance_blacklist (company_name, risk_category, risk_score, details)
            VALUES (?, ?, ?, ?)
        ''', mock_blacklist)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database initialization note: {e}")
    finally:
        conn.close()

# Automatically initialize the database table when the file is loaded
init_compliance_db()


@tool("Regulatory Compliance Screening Tool")
def screen_corporate_entity(company_name: str) -> str:
    """
    Queries the internal compliance database to check if a corporate entity is blacklisted.
    Input should be a clean string representing the company name.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Perform a fuzzy matching query using SQL LIKE
    query = "SELECT company_name, risk_category, risk_score, details FROM compliance_blacklist WHERE company_name LIKE ?"
    cursor.execute(query, (f"%{company_name.strip()}%",))
    match = cursor.fetchone()
    conn.close()
    
    if match:
        # Return a structured high-risk match payload back to the agent loop
        return f"CRITICAL_MATCH_FOUND | Company: {match[0]} | Risk Category: {match[1]} | Risk Score: {match[2]} | Details: {match[3]}"
    
    return "CLEAN | No compliance risks or blacklist hits detected for this entity."