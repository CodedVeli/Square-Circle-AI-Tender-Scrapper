"""
Quick Setup and Demo Script for Square Circle Tender System
Run this to quickly test the system functionality
"""
import os
import sys
from datetime import datetime, timedelta
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import create_tables, SessionLocal, Tender, CompanyProfile
from evaluator import TenderEvaluator
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Initialize database with tables"""
    logger.info("Setting up database...")
    create_tables()
    logger.info("Database tables created successfully!")

def add_sample_company_profiles():
    """Add sample company experience profiles"""
    logger.info("Adding sample company experience profiles...")
    
    evaluator = TenderEvaluator()
    
    # Add Square Circle's experience profiles
    profiles = [
        ("climate change", "fiji", 4.2, 0.85),
        ("climate change", "vanuatu", 4.0, 0.80),
        ("climate change", "pacific", 4.5, 0.90),
        ("governance", "fiji", 3.8, 0.75),
        ("governance", "vanuatu", 3.5, 0.70),
        ("governance", "pacific", 4.0, 0.80),
        ("infrastructure", "pacific", 3.2, 0.75),
        ("infrastructure", "fiji", 3.5, 0.80),
        ("development", "pacific", 4.0, 0.85),
        ("environmental", "pacific", 4.3, 0.88),
        ("capacity building", "pacific", 4.1, 0.82),
        ("policy", "pacific", 3.8, 0.78)
    ]
    
    for sector, region, experience, success_rate in profiles:
        evaluator.update_company_profile(sector, region, experience, success_rate)
    
    evaluator.close()
    logger.info("Sample company profiles added!")

def add_sample_tenders():
    """Add sample tender data for testing"""
    logger.info("Adding sample tender data...")
    
    db = SessionLocal()
    
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
        db.add(tender)
    
    db.commit()
    db.close()
    logger.info("Sample tender data added!")

def run_sample_evaluation():
    """Run evaluation on sample data"""
    logger.info("Running evaluation on sample tenders...")
    
    evaluator = TenderEvaluator()
    results = evaluator.evaluate_all_tenders()
    
    logger.info("Evaluation Results:")
    logger.info("=" * 50)
    
    for result in results:
        if 'error' not in result:
            overall_score = result['scores']['overall_score']
            priority = result['recommendation']['priority']
            action = result['recommendation']['action_recommendation']
            
            logger.info(f"Tender ID: {result['tender_id']}")
            logger.info(f"Overall Score: {overall_score:.1f}/5.0")
            logger.info(f"Priority: {priority}")
            logger.info(f"Recommendation: {action}")
            
            if result['recommendation']['strengths']:
                logger.info(f"Strengths: {', '.join(result['recommendation']['strengths'])}")
            
            if result['recommendation']['concerns']:
                logger.info(f"Concerns: {', '.join(result['recommendation']['concerns'])}")
            
            logger.info("-" * 30)
    
    evaluator.close()

def check_system_status():
    """Check system configuration and status"""
    logger.info("Checking system status...")
    logger.info("=" * 50)
    
    # Check configuration
    logger.info("Configuration Status:")
    logger.info(f"OpenAI API Key: {'✅ Configured' if Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != 'your_openai_api_key_here' else '❌ Not configured'}")
    logger.info(f"Devex Credentials: {'✅ Configured' if Config.DEVEX_EMAIL else '❌ Missing'}")
    logger.info(f"Tenders.gov.au Credentials: {'✅ Configured' if Config.TENDERS_GOV_EMAIL else '❌ Missing'}")
    
    # Check database
    try:
        db = SessionLocal()
        tender_count = db.query(Tender).count()
        profile_count = db.query(CompanyProfile).count()
        db.close()
        
        logger.info(f"Database: ✅ Connected")
        logger.info(f"Tenders in database: {tender_count}")
        logger.info(f"Company profiles: {profile_count}")
        
    except Exception as e:
        logger.error(f"Database: ❌ Error - {str(e)}")
    
    # Check directories
    for path_name, path in [("Export Path", Config.EXPORT_PATH), ("Attachment Path", Config.ATTACHMENT_PATH)]:
        if os.path.exists(path):
            logger.info(f"{path_name}: ✅ {path}")
        else:
            logger.warning(f"{path_name}: ⚠️ Directory missing - {path}")
    
    logger.info("=" * 50)

def main():
    """Main demo setup function"""
    print("🎯 Square Circle Tender Curation System - Demo Setup")
    print("=" * 60)
    
    try:
        # Setup
        setup_database()
        # add_sample_company_profiles()
        # add_sample_tenders()
        
        # # Run evaluation
        # run_sample_evaluation()
        
        # System status
        check_system_status()
        
        print("\n✅ Demo setup completed successfully!")
        print("\nNext steps:")
        print("1. Update .env file with your OpenAI API key")
        print("2. Run 'streamlit run dashboard.py' to start the web interface")
        print("3. Or run 'python scraper_manager.py --status' to check system status")
        print("4. Or run 'python scraper_manager.py --sites abt_global' to test scraping")
        
    except Exception as e:
        logger.error(f"Demo setup failed: {str(e)}")
        print(f"❌ Setup failed: {str(e)}")

if __name__ == "__main__":
    main()
