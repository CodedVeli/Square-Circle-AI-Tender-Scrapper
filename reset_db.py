#!/usr/bin/env python3
"""
Simple Database Reset Script
Forcefully resets the database by killing processes and recreating
"""
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta

def kill_python_processes():
    """Kill any Python processes that might be holding the database"""
    print("🔧 Stopping any running Python processes...")
    
    try:
        # Kill any streamlit processes
        result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                              capture_output=True, text=True)
        print("   Stopped Python processes")
        
        time.sleep(2)  # Wait for processes to fully stop
        
    except Exception as e:
        print(f"   Note: {e}")

def force_remove_database():
    """Force remove database files"""
    print("🗑️ Removing database files...")
    
    db_files = [
        "c:\\Users\\user\\Projects\\Scraping\\tenders.db",
        "c:\\Users\\user\\Projects\\Scraping\\tenders.db-journal",
        "c:\\Users\\user\\Projects\\Scraping\\tenders.db-wal",
        "c:\\Users\\user\\Projects\\Scraping\\tenders.db-shm"
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"   ✅ Removed {os.path.basename(db_file)}")
            except Exception as e:
                print(f"   ⚠️ Could not remove {db_file}: {e}")

def create_simple_database():
    """Create database with direct SQL"""
    print("🔧 Creating new database...")
    
    import sqlite3
    
    # Create new database
    conn = sqlite3.connect("c:\\Users\\user\\Projects\\Scraping\\tenders.db")
    cursor = conn.cursor()
    
    # Create tenders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(500),
            source_site VARCHAR(100),
            url TEXT,
            description TEXT,
            funder VARCHAR(200),
            sector VARCHAR(200),
            location VARCHAR(200),
            budget_min FLOAT,
            budget_max FLOAT,
            budget_currency VARCHAR(10),
            deadline DATETIME,
            project_duration VARCHAR(100),
            scraped_at DATETIME,
            last_updated DATETIME,
            ai_analysis_complete BOOLEAN,
            ai_extracted_sectors TEXT,
            ai_extracted_keywords TEXT,
            ai_summary TEXT,
            evaluation_score FLOAT,
            sector_score FLOAT,
            location_score FLOAT,
            budget_score FLOAT,
            deadline_score FLOAT,
            experience_score FLOAT,
            is_shortlisted BOOLEAN,
            status VARCHAR(50),
            notes TEXT
        )
    ''')
    
    # Create company_profiles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sector VARCHAR(100),
            region VARCHAR(100),
            experience_score FLOAT,
            success_rate FLOAT,
            created_at DATETIME,
            updated_at DATETIME
        )
    ''')
    
    # Create scraping_logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraping_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name VARCHAR(100),
            start_time DATETIME,
            end_time DATETIME,
            status VARCHAR(50),
            tenders_found INTEGER,
            tenders_new INTEGER,
            tenders_updated INTEGER,
            error_message TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("   ✅ Database created successfully")

def add_sample_data():
    """Add sample data directly with SQL"""
    print("📄 Adding sample data...")
    
    import sqlite3
    
    conn = sqlite3.connect("c:\\Users\\user\\Projects\\Scraping\\tenders.db")
    cursor = conn.cursor()
    
    # Add company profiles
    profiles = [
        ("climate change", "fiji", 4.2, 0.85),
        ("climate change", "vanuatu", 4.0, 0.80),
        ("climate change", "pacific", 4.5, 0.90),
        ("governance", "fiji", 3.8, 0.75),
        ("governance", "pacific", 4.0, 0.80),
        ("infrastructure", "pacific", 3.2, 0.75),
        ("development", "pacific", 4.0, 0.85),
        ("environmental", "pacific", 4.3, 0.88),
        ("policy", "pacific", 3.8, 0.78)
    ]
    
    current_time = datetime.now().isoformat()
    
    for sector, region, exp_score, success_rate in profiles:
        cursor.execute('''
            INSERT INTO company_profiles (sector, region, experience_score, success_rate, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sector, region, exp_score, success_rate, current_time, current_time))
    
    # Add sample tenders
    tenders = [
        (
            "Pacific Climate Resilience Advisory Services",
            "Sample Data",
            "https://example.com/tender1",
            "Seeking consultancy services for climate change adaptation planning in Fiji and Vanuatu.",
            "Pacific Development Fund",
            "climate change, governance",
            "fiji, vanuatu, pacific",
            80000, 150000, "USD",
            (datetime.now() + timedelta(days=45)).isoformat(),
            "18 months",
            current_time,
            3.55, 4.0, 5.0, 3.0, 4.0, 4.0  # Sample scores
        ),
        (
            "Environmental Impact Assessment - Tonga", 
            "Sample Data",
            "https://example.com/tender2",
            "Environmental impact assessment and management planning for coastal development project in Tonga.",
            "Green Climate Fund",
            "environmental, climate change",
            "tonga, pacific",
            45000, 85000, "USD",
            (datetime.now() + timedelta(days=25)).isoformat(),
            "12 months",
            current_time,
            3.40, 4.0, 5.0, 2.5, 3.5, 4.0  # Sample scores
        ),
        (
            "Governance Assessment - Solomon Islands",
            "Sample Data", 
            "https://example.com/tender3",
            "Technical assistance for governance assessment and institutional capacity building in Solomon Islands.",
            "World Bank",
            "governance, capacity building",
            "solomon islands, pacific",
            200000, 350000, "USD",
            (datetime.now() + timedelta(days=30)).isoformat(),
            "24 months",
            current_time,
            3.35, 4.0, 5.0, 3.5, 3.0, 3.0  # Sample scores
        )
    ]
    
    for tender in tenders:
        cursor.execute('''
            INSERT INTO tenders (
                title, source_site, url, description, funder, sector, location,
                budget_min, budget_max, budget_currency, deadline, project_duration, scraped_at,
                evaluation_score, sector_score, location_score, budget_score, deadline_score, experience_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tender)
    
    conn.commit()
    conn.close()
    print(f"   ✅ Added {len(profiles)} company profiles")
    print(f"   ✅ Added {len(tenders)} sample tenders")

def verify_database():
    """Verify the database is working"""
    print("🔍 Verifying database...")
    
    import sqlite3
    
    conn = sqlite3.connect("c:\\Users\\user\\Projects\\Scraping\\tenders.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM tenders")
    tender_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM company_profiles")
    profile_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tenders WHERE evaluation_score IS NOT NULL")
    evaluated_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"   📊 Tenders: {tender_count}")
    print(f"   📊 Profiles: {profile_count}")  
    print(f"   📊 Evaluated: {evaluated_count}")
    
    if tender_count > 0 and profile_count > 0:
        print("   ✅ Database verification successful")
        return True
    else:
        print("   ❌ Database verification failed")
        return False

def main():
    print("🚀 SIMPLE DATABASE RESET")
    print("=" * 40)
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Kill processes
    kill_python_processes()
    
    # Step 2: Remove database files
    force_remove_database()
    
    # Step 3: Create new database
    create_simple_database()
    
    # Step 4: Add sample data
    add_sample_data()
    
    # Step 5: Verify
    if verify_database():
        print("\n🎉 DATABASE RESET COMPLETE!")
        print("✅ Ready to use")
        print("\n🚀 Next: python -m streamlit run dashboard.py --server.port=8503")
        return True
    else:
        print("\n❌ DATABASE RESET FAILED!")
        return False

if __name__ == "__main__":
    main()
