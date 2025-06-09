"""
Scraper Manager for Square Circle Tender System
Command-line interface for running scraping operations
"""
import argparse
import logging
from datetime import datetime
from scraper import ScrapingManager
from evaluator import TenderEvaluator
from models import create_tables
from config import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function for command-line scraping"""
    parser = argparse.ArgumentParser(description='Square Circle Tender Scraper')
    parser.add_argument('--sites', nargs='+', help='Specific sites to scrape', 
                       choices=list(Config.SITES_CONFIG.keys()))
    parser.add_argument('--evaluate', action='store_true', 
                       help='Run evaluation after scraping')
    parser.add_argument('--init-db', action='store_true', 
                       help='Initialize database tables')
    parser.add_argument('--status', action='store_true', 
                       help='Show system status')
    
    args = parser.parse_args()
    
    if args.init_db:
        logger.info("Initializing database tables...")
        create_tables()
        logger.info("Database tables created successfully!")
        return
    
    if args.status:
        show_status()
        return
    
    # Initialize database if needed
    create_tables()
    
    # Run scraping
    logger.info("Starting scraping operation...")
    manager = ScrapingManager()
    
    try:
        if args.sites:
            logger.info(f"Scraping specific sites: {args.sites}")
            results = scrape_specific_sites(manager, args.sites)
        else:
            logger.info("Scraping all configured sites...")
            results = manager.scrape_all_sites()
        
        # Display results
        display_scraping_results(results)
        
        # Run evaluation if requested
        if args.evaluate:
            logger.info("Running tender evaluation...")
            run_evaluation()
        
    except Exception as e:
        logger.error(f"Scraping operation failed: {str(e)}")
    finally:
        manager.close()

def scrape_specific_sites(manager, site_keys):
    """Scrape specific sites"""
    results = {
        'total_sites': len(site_keys),
        'successful_sites': 0,
        'failed_sites': 0,
        'total_tenders': 0,
        'new_tenders': 0,
        'updated_tenders': 0,
        'site_results': {}
    }
    
    from scraper import TenderScraper
    
    for site_key in site_keys:
        if site_key not in Config.SITES_CONFIG:
            logger.error(f"Unknown site: {site_key}")
            continue
        
        site_config = Config.SITES_CONFIG[site_key]
        logger.info(f"Scraping {site_config['name']}...")
        
        try:
            scraper = TenderScraper(site_config)
            tender_data_list = scraper.scrape_site()
            site_stats = manager.process_scraped_data(tender_data_list, site_config['name'])
            
            results['successful_sites'] += 1
            results['total_tenders'] += len(tender_data_list)
            results['new_tenders'] += site_stats['new']
            results['updated_tenders'] += site_stats['updated']
            results['site_results'][site_config['name']] = site_stats
            
        except Exception as e:
            logger.error(f"Failed to scrape {site_config['name']}: {str(e)}")
            results['failed_sites'] += 1
            results['site_results'][site_config['name']] = {'error': str(e)}
    
    return results

def run_evaluation():
    """Run tender evaluation"""
    try:
        evaluator = TenderEvaluator()
        results = evaluator.evaluate_all_tenders()
        
        successful = len([r for r in results if 'error' not in r])
        failed = len(results) - successful
        
        logger.info(f"Evaluation completed: {successful} successful, {failed} failed")
        
        # Display top-scoring tenders
        successful_results = [r for r in results if 'error' not in r]
        if successful_results:
            top_tenders = sorted(successful_results, 
                               key=lambda x: x['scores']['overall_score'], 
                               reverse=True)[:5]
            
            logger.info("Top 5 scoring tenders:")
            for i, result in enumerate(top_tenders, 1):
                score = result['scores']['overall_score']
                recommendation = result['recommendation']['priority']
                logger.info(f"{i}. Score: {score:.1f}/5.0, Priority: {recommendation}")
        
        evaluator.close()
        
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")

def display_scraping_results(results):
    """Display scraping results summary"""
    logger.info("=" * 50)
    logger.info("SCRAPING RESULTS SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total sites attempted: {results['total_sites']}")
    logger.info(f"Successful sites: {results['successful_sites']}")
    logger.info(f"Failed sites: {results['failed_sites']}")
    logger.info(f"Total tenders found: {results['total_tenders']}")
    logger.info(f"New tenders: {results['new_tenders']}")
    logger.info(f"Updated tenders: {results['updated_tenders']}")
    logger.info("")
    
    logger.info("Site-by-site results:")
    for site_name, stats in results['site_results'].items():
        if 'error' in stats:
            logger.error(f"{site_name}: ERROR - {stats['error']}")
        else:
            logger.info(f"{site_name}: {stats.get('new', 0)} new, {stats.get('updated', 0)} updated")
    
    logger.info("=" * 50)

def show_status():
    """Show system status"""
    from models import SessionLocal, Tender, TenderDocument, ScrapingLog
    
    logger.info("=" * 50)
    logger.info("SYSTEM STATUS")
    logger.info("=" * 50)
    
    # Database status
    try:
        db = SessionLocal()
        tender_count = db.query(Tender).count()
        document_count = db.query(TenderDocument).count()
        log_count = db.query(ScrapingLog).count()
        
        logger.info(f"Database: Connected")
        logger.info(f"Total tenders: {tender_count}")
        logger.info(f"Total documents: {document_count}")
        logger.info(f"Scraping logs: {log_count}")
        
        # Recent activity
        recent_tenders = db.query(Tender).filter(
            Tender.scraped_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        logger.info(f"Tenders scraped today: {recent_tenders}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
    
    # Configuration status
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"OpenAI API: {'Configured' if Config.OPENAI_API_KEY else 'Missing'}")
    logger.info(f"Devex credentials: {'Configured' if Config.DEVEX_EMAIL else 'Missing'}")
    logger.info(f"Tenders.gov.au credentials: {'Configured' if Config.TENDERS_GOV_EMAIL else 'Missing'}")
    
    # Site configuration
    logger.info("")
    logger.info("Configured sites:")
    for site_key, site_config in Config.SITES_CONFIG.items():
        login_required = site_config.get('requires_login', False)
        status = "Requires login" if login_required else "Public"
        logger.info(f"  {site_config['name']}: {status}")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
