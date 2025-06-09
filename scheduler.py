"""
Scheduler for Daily Automated Scraping
Runs tender scraping operations on a scheduled basis
"""
import schedule
import time
import logging
from datetime import datetime
from scraper_manager import ScrapingManager
from evaluator import TenderEvaluator
from models import create_tables
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def daily_scraping_job():
    """Daily scraping and evaluation job"""
    logger.info("Starting daily scraping job...")
    
    try:
        # Initialize database
        create_tables()
        
        # Run scraping
        manager = ScrapingManager()
        results = manager.scrape_all_sites()
        manager.close()
        
        logger.info(f"Scraping completed: {results['new_tenders']} new, {results['updated_tenders']} updated")
        
        # Run evaluation
        if results['new_tenders'] > 0 or results['updated_tenders'] > 0:
            logger.info("Running evaluation for new/updated tenders...")
            evaluator = TenderEvaluator()
            eval_results = evaluator.evaluate_all_tenders()
            evaluator.close()
            
            successful_evaluations = len([r for r in eval_results if 'error' not in r])
            logger.info(f"Evaluation completed: {successful_evaluations} tenders evaluated")
        
        logger.info("Daily scraping job completed successfully")
        
    except Exception as e:
        logger.error(f"Daily scraping job failed: {str(e)}")

def weekly_cleanup_job():
    """Weekly cleanup and maintenance job"""
    logger.info("Starting weekly cleanup job...")
    
    try:
        from models import SessionLocal, Tender, TenderDocument, ScrapingLog
        from datetime import timedelta
        
        db = SessionLocal()
        
        # Clean up old scraping logs (keep last 100)
        old_logs = db.query(ScrapingLog).order_by(ScrapingLog.start_time.desc()).offset(100).all()
        for log in old_logs:
            db.delete(log)
        
        # Clean up orphaned documents
        orphaned_docs = db.query(TenderDocument).filter(
            ~TenderDocument.tender_id.in_(db.query(Tender.id))
        ).all()
        
        for doc in orphaned_docs:
            # Remove local file if exists
            if doc.local_path and os.path.exists(doc.local_path):
                try:
                    os.remove(doc.local_path)
                    logger.info(f"Removed orphaned file: {doc.local_path}")
                except Exception as e:
                    logger.warning(f"Could not remove file {doc.local_path}: {str(e)}")
            
            db.delete(doc)
        
        db.commit()
        db.close()
        
        logger.info("Weekly cleanup completed")
        
    except Exception as e:
        logger.error(f"Weekly cleanup failed: {str(e)}")

def health_check_job():
    """Health check job to verify system status"""
    logger.info("Running health check...")
    
    try:
        from models import SessionLocal
        from config import Config
        
        # Check database connectivity
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("✅ Database connection OK")
        
        # Check API configuration
        if Config.OPENAI_API_KEY:
            logger.info("✅ OpenAI API configured")
        else:
            logger.warning("⚠️ OpenAI API not configured")
        
        # Check credentials
        if Config.DEVEX_EMAIL and Config.DEVEX_PASSWORD:
            logger.info("✅ Devex credentials configured")
        else:
            logger.warning("⚠️ Devex credentials missing")
        
        if Config.TENDERS_GOV_EMAIL and Config.TENDERS_GOV_PASSWORD:
            logger.info("✅ Tenders.gov.au credentials configured")
        else:
            logger.warning("⚠️ Tenders.gov.au credentials missing")
        
        # Check file system
        for path_name, path in [("Export", Config.EXPORT_PATH), ("Attachments", Config.ATTACHMENT_PATH)]:
            if os.path.exists(path) and os.access(path, os.W_OK):
                logger.info(f"✅ {path_name} path accessible: {path}")
            else:
                logger.error(f"❌ {path_name} path not accessible: {path}")
        
        logger.info("Health check completed")
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")

def main():
    """Main scheduler function"""
    logger.info("Starting Square Circle Tender Scraping Scheduler")
    logger.info("Scheduled jobs:")
    logger.info("- Daily scraping: 08:00 AM")
    logger.info("- Weekly cleanup: Sunday 02:00 AM")
    logger.info("- Health check: Every 6 hours")
    
    # Schedule jobs
    schedule.every().day.at("08:00").do(daily_scraping_job)
    schedule.every().sunday.at("02:00").do(weekly_cleanup_job)
    schedule.every(6).hours.do(health_check_job)
    
    # Run initial health check
    health_check_job()
    
    # Main scheduler loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Square Circle Tender Scheduler')
    parser.add_argument('--run-now', action='store_true', 
                       help='Run daily scraping job immediately')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Run cleanup job immediately')
    parser.add_argument('--health-check', action='store_true', 
                       help='Run health check immediately')
    
    args = parser.parse_args()
    
    if args.run_now:
        daily_scraping_job()
    elif args.cleanup:
        weekly_cleanup_job()
    elif args.health_check:
        health_check_job()
    else:
        main()
