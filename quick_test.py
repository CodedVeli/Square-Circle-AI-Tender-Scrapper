#!/usr/bin/env python3
"""
Quick system test for AI Tender Curation System
"""
import sqlite3
import os
from datetime import datetime

def test_system():
    print("=== AI TENDER CURATION SYSTEM - QUICK TEST ===")
    print(f"Test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Database connectivity
    print("\n1. Testing Database Connectivity...")
    try:
        db_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Count tenders
            cursor.execute("SELECT COUNT(*) FROM tenders")
            tender_count = cursor.fetchone()[0]
            print(f"   ✅ Database connected: {tender_count} tenders found")
            
            # Count evaluated tenders
            cursor.execute("SELECT COUNT(*) FROM tenders WHERE evaluation_score IS NOT NULL")
            evaluated_count = cursor.fetchone()[0]
            print(f"   ✅ Evaluated tenders: {evaluated_count}")
            
            # Show top 3 tenders
            cursor.execute("""
                SELECT title, source, evaluation_score 
                FROM tenders 
                WHERE evaluation_score IS NOT NULL 
                ORDER BY evaluation_score DESC 
                LIMIT 3
            """)
            top_tenders = cursor.fetchall()
            print("   📊 Top 3 tenders:")
            for i, (title, source, score) in enumerate(top_tenders, 1):
                print(f"      {i}. {title[:50]}... ({source}) - Score: {score:.2f}")
            
            conn.close()
        else:
            print(f"   ❌ Database not found at {db_path}")
    except Exception as e:
        print(f"   ❌ Database test failed: {str(e)}")
    
    # Test 2: Check key files
    print("\n2. Testing System Files...")
    key_files = [
        ("Config", "config.py"),
        ("Models", "models.py"), 
        ("AI Analyzer", "ai_analyzer.py"),
        ("Evaluator", "evaluator.py"),
        ("Dashboard", "dashboard.py"),
        ("Simple Scraper", "simple_scraper.py"),
        ("Export Module", "export_module.py"),
        ("Environment", ".env")
    ]
    
    for name, filename in key_files:
        filepath = f"c:\\Users\\user\\Projects\\Scraping\\{filename}"
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"   ✅ {name}: {filename} ({size:,} bytes)")
        else:
            print(f"   ❌ {name}: {filename} NOT FOUND")
    
    # Test 3: Check Python packages
    print("\n3. Testing Python Dependencies...")
    required_packages = [
        "requests", "beautifulsoup4", "selenium", "openai", 
        "streamlit", "pandas", "sqlite3"
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            if package == "sqlite3":
                import sqlite3 as sql3
                print(f"   ✅ sqlite3 (as built-in)")
            else:
                print(f"   ❌ {package} NOT AVAILABLE")
    
    # Test 4: Environment variables
    print("\n4. Testing Environment Configuration...")
    env_file = "c:\\Users\\user\\Projects\\Scraping\\.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            env_content = f.read()
            if "OPENAI_API_KEY" in env_content:
                print("   ✅ OpenAI API key configured")
            else:
                print("   ❌ OpenAI API key not found")
            
            if "DEVEX_USERNAME" in env_content:
                print("   ✅ Devex credentials configured")
            else:
                print("   ❌ Devex credentials not found")
    else:
        print("   ❌ .env file not found")
    
    print("\n=== SYSTEM TEST COMPLETED ===")

if __name__ == "__main__":
    test_system()
