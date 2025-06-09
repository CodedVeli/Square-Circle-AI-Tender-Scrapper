#!/usr/bin/env python3
"""
Database Initialization Script for AI Tender Curation System
This script safely initializes/reinitializes the database from scratch
"""
import os
import sys
import sqlite3
import shutil
from datetime import datetime, timedelta
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_existing_database():
    """Create a backup of existing database if it exists"""
    db_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db"
    
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"c:\\Users\\user\\Projects\\Scraping\\tenders_backup_{timestamp}.db"
        
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Existing database backed up to: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"⚠️ Could not backup database: {e}")
            return None
    else:
        logger.info("ℹ️ No existing database found - creating fresh")
        return None

def remove_database_locks():
    """Remove database and any lock files"""
    db_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db"
    journal_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db-journal"
    wal_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db-wal"
    shm_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db-shm"
    
    files_to_remove = [db_path, journal_path, wal_path, shm_path]
    
    for file_path in files_to_remove:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️ Removed: {os.path.basename(file_path)}")
            except Exception as e:
                logger.warning(f"⚠️ Could not remove {file_path}: {e}")

def create_fresh_database():
    """Create a fresh database with all required tables"""
    logger.info("🔧 Creating fresh database...")
    
    db_path = "c:\\Users\\user\\Projects\\Scraping\\tenders.db"
    
    try:
        # Import models after ensuring clean state
        from models import create_tables, SessionLocal, engine
        
        # Create all tables
        create_tables()
        logger.info("✅ Database tables created successfully")
        
        # Test connection
        session = SessionLocal()
        session.execute("SELECT 1")
        session.close()
        logger.info("✅ Database connection verified")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database: {e}")
        return False

def add_company_profiles():
    """Add Square Circle's company experience profiles"""
    logger.info("👥 Adding company experience profiles...")
    
    try:
        from models import SessionLocal, CompanyProfile
        
        session = SessionLocal()
        
        # Clear existing profiles
        session.query(CompanyProfile).delete()
        
        # Square Circle's experience profiles
        profiles = [
            {"sector": "climate change", "region": "fiji", "experience_score": 4.2, "success_rate": 0.85},
            {"sector": "climate change", "region": "vanuatu", "experience_score": 4.0, "success_rate": 0.80},
            {"sector": "climate change", "region": "pacific", "experience_score": 4.5, "success_rate": 0.90},
            {"sector": "governance", "region": "fiji", "experience_score": 3.8, "success_rate": 0.75},
            {"sector": "governance", "region": "vanuatu", "experience_score": 3.5, "success_rate": 0.70},
            {"sector": "governance", "region": "pacific", "experience_score": 4.0, "success_rate": 0.80},
            {"sector": "infrastructure", "region": "pacific", "experience_score": 3.2, "success_rate": 0.75},
            {"sector": "infrastructure", "region": "fiji", "experience_score": 3.5, "success_rate": 0.80},
            {"sector": "development", "region": "pacific", "experience_score": 4.0, "success_rate": 0.85},
            {"sector": "environmental", "region": "pacific", "experience_score": 4.3, "success_rate": 0.88},
            {"sector": "capacity building", "region": "pacific", "experience_score": 4.1, "success_rate": 0.82},
            {"sector": "policy", "region": "pacific", "experience_score": 3.8, "success_rate": 0.78}
        ]
        
        for profile_data in profiles:
            profile = CompanyProfile(
                sector=profile_data["sector"],
                region=profile_data["region"],
                experience_score=profile_data["experience_score"],
                success_rate=profile_data["success_rate"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(profile)
        
        session.commit()
        session.close()
        
        logger.info(f"✅ Added {len(profiles)} company profiles")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add company profiles: {e}")
        return False

def add_sample_tenders():
    """Add sample tender data for testing"""
    logger.info("📄 Adding sample tender data...")
    
    try:
        from models import SessionLocal, Tender
        
        session = SessionLocal()
        
        sample_tenders = [
            {
                'title': 'Pacific Climate Resilience Advisory Services',
                'source_site': 'Sample Data',
                'url': 'https://example.com/tender1',
                'description': 'Seeking consultancy services for climate change adaptation planning in Fiji and Vanuatu. The project will focus on policy development, stakeholder engagement, and capacity building for local communities.',
                'funder': 'Pacific Development Fund',
                'sector': 'climate change, governance',
                'location': 'fiji, vanuatu, pacific',
                'budget_min': 80000,
                'budget_max': 150000,
                'budget_currency': 'USD',
                'deadline': datetime.now() + timedelta(days=45),
                'project_duration': '18 months',
                'scraped_at': datetime.utcnow()
            },
            {
                'title': 'Governance Assessment and Capacity Building - Solomon Islands',
                'source_site': 'Sample Data',
                'url': 'https://example.com/tender2',
                'description': 'Technical assistance for governance assessment and institutional capacity building in Solomon Islands. Focus on resource governance, transparency, and accountability mechanisms.',
                'funder': 'World Bank',
                'sector': 'governance, capacity building',
                'location': 'solomon islands, pacific',
                'budget_min': 200000,
                'budget_max': 350000,
                'budget_currency': 'USD',
                'deadline': datetime.now() + timedelta(days=30),
                'project_duration': '24 months',
                'scraped_at': datetime.utcnow()
            },
            {
                'title': 'Infrastructure Development Planning - Global',
                'source_site': 'Sample Data',
                'url': 'https://example.com/tender3',
                'description': 'Large-scale infrastructure development planning and implementation support required for multiple countries. Preference for major international contractors with extensive experience.',
                'funder': 'Asian Development Bank',
                'sector': 'infrastructure',
                'location': 'global',
                'budget_min': 2000000,
                'budget_max': 5000000,
                'budget_currency': 'USD',
                'deadline': datetime.now() + timedelta(days=60),
                'project_duration': '36 months',
                'scraped_at': datetime.utcnow()
            },
            {
                'title': 'Environmental Impact Assessment - Tonga',
                'source_site': 'Sample Data',
                'url': 'https://example.com/tender4',
                'description': 'Environmental impact assessment and management planning for coastal development project in Tonga. Requires expertise in marine ecosystems and climate adaptation.',
                'funder': 'Green Climate Fund',
                'sector': 'environmental, climate change',
                'location': 'tonga, pacific',
                'budget_min': 45000,
                'budget_max': 85000,
                'budget_currency': 'USD',
                'deadline': datetime.now() + timedelta(days=25),
                'project_duration': '12 months',
                'scraped_at': datetime.utcnow()
            },
            {
                'title': 'Policy Research and Analysis - Pacific Region',
                'source_site': 'Sample Data',
                'url': 'https://example.com/tender5',
                'description': 'Comprehensive policy research and analysis on sustainable development goals implementation across Pacific Island nations. Focus on data collection, analysis, and policy recommendations.',
                'funder': 'UN Development Programme',
                'sector': 'policy, development, research',
                'location': 'pacific',
                'budget_min': 120000,
                'budget_max': 180000,
                'budget_currency': 'USD',
                'deadline': datetime.now() + timedelta(days=55),
                'project_duration': '20 months',
                'scraped_at': datetime.utcnow()
            }
        ]
        
        for tender_data in sample_tenders:
            tender = Tender(**tender_data)
            session.add(tender)
        
        session.commit()
        session.close()
        
        logger.info(f"✅ Added {len(sample_tenders)} sample tenders")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to add sample tenders: {e}")
        return False

def run_initial_evaluation():
    """Run evaluation on the sample tenders"""
    logger.info("🤖 Running initial tender evaluation...")
    
    try:
        from evaluator import TenderEvaluator
        
        evaluator = TenderEvaluator()
        results = evaluator.evaluate_all_tenders()
        
        evaluated_count = 0
        for result in results:
            if 'error' not in result:
                evaluated_count += 1
        
        evaluator.close()
        
        logger.info(f"✅ Evaluated {evaluated_count} tenders")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to run evaluation: {e}")
        return False

def verify_database():
    """Verify the database is properly initialized"""
    logger.info("🔍 Verifying database initialization...")
    
    try:
        from models import SessionLocal, Tender, CompanyProfile
        
        session = SessionLocal()
        
        tender_count = session.query(Tender).count()
        profile_count = session.query(CompanyProfile).count()
        evaluated_count = session.query(Tender).filter(Tender.evaluation_score.isnot(None)).count()
        
        session.close()
        
        logger.info(f"📊 Database Statistics:")
        logger.info(f"   • Tenders: {tender_count}")
        logger.info(f"   • Company Profiles: {profile_count}")
        logger.info(f"   • Evaluated Tenders: {evaluated_count}")
        
        if tender_count > 0 and profile_count > 0:
            logger.info("✅ Database verification successful")
            return True
        else:
            logger.error("❌ Database verification failed - missing data")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database verification error: {e}")
        return False

def main():
    """Main initialization function"""
    print("🚀 AI TENDER CURATION SYSTEM - DATABASE INITIALIZATION")
    print("=" * 60)
    print(f"🕒 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Backup existing database
    print("📋 Step 1: Backup existing database")
    backup_path = backup_existing_database()
    print()
    
    # Step 2: Remove locks and clean slate
    print("📋 Step 2: Remove database locks")
    remove_database_locks()
    print()
    
    # Step 3: Create fresh database
    print("📋 Step 3: Create fresh database")
    if not create_fresh_database():
        print("❌ Database initialization failed!")
        return False
    print()
    
    # Step 4: Add company profiles
    print("📋 Step 4: Add company profiles")
    if not add_company_profiles():
        print("❌ Failed to add company profiles!")
        return False
    print()
    
    # Step 5: Add sample tenders
    print("📋 Step 5: Add sample tenders")
    if not add_sample_tenders():
        print("❌ Failed to add sample tenders!")
        return False
    print()
    
    # Step 6: Run initial evaluation
    print("📋 Step 6: Run initial evaluation")
    if not run_initial_evaluation():
        print("❌ Failed to run initial evaluation!")
        return False
    print()
    
    # Step 7: Verify everything
    print("📋 Step 7: Verify database")
    if not verify_database():
        print("❌ Database verification failed!")
        return False
    print()
    
    # Success!
    print("🎉 DATABASE INITIALIZATION COMPLETE!")
    print("=" * 60)
    print("✅ Database is ready for use")
    print("✅ Sample data loaded and evaluated")
    print("✅ Company profiles configured")
    print()
    print("🚀 Next Steps:")
    print("1. Run: python -m streamlit run dashboard.py --server.port=8503")
    print("2. Open: http://localhost:8503")
    print("3. Test: python simple_scraper.py")
    print()
    
    if backup_path:
        print(f"💾 Backup saved to: {backup_path}")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
