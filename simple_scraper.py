#!/usr/bin/env python3
"""
Simplified scraper for testing updated selectors
"""
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from config import Config
from models import SessionLocal, Tender

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTenderScraper:
    def __init__(self):
        self.config = Config()
        self.db = SessionLocal()
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def extract_tender_links(self, site_config):
        """Extract tender links from search/listing page"""
        try:
            search_url = site_config['search_url']
            self.driver.get(search_url)
            time.sleep(3)
            
            # Extract links using CSS selectors
            link_selector = site_config['selectors']['tender_links']
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, link_selector)
            
            links = []
            invalid_prefixes = ['javascript:', 'mailto:', '#', 'tel:']
            exclude_patterns = [
                '/careers', '/about', '/contact', '/press', '/subscribe', 
                '/board-of-directors', '/executive-leadership', '/expertise',
                '/impact/', '/doing-business-with-abt$'
            ]
            
            for element in link_elements:
                href = element.get_attribute('href')
                if href and not any(href.startswith(prefix) for prefix in invalid_prefixes):
                    # Skip general navigation links
                    if not any(pattern in href for pattern in exclude_patterns):
                        # For specific sites, be more selective
                        if site_config['name'] == 'Abt Global':
                            if 'field_person_type' in href:
                                links.append(href)
                        elif site_config['name'] == 'Tetra Tech International Development':
                            if any(ext in href for ext in ['.pdf', '.docx']) or 'tender' in href.lower():
                                links.append(href)
                        elif site_config['name'] == 'DT Global':
                            if 'proposals/' in href and href != site_config['search_url']:
                                links.append(href)
                        else:
                            links.append(href)
            
            # Remove duplicates
            links = list(set(links))
            logger.info(f"Found {len(links)} tender links on {site_config['name']}")
            return links[:10]  # Limit for demo
            
        except Exception as e:
            logger.error(f"Error extracting tender links from {site_config['name']}: {str(e)}")
            return []
    
    def scrape_tender_details(self, url, site_config):
        """Scrape details from individual tender page"""
        try:
            self.driver.get(url)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract title with fallbacks
            title = None
            title_selectors = site_config['selectors']['title'].split(', ')
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    title = element.get_text(strip=True)
                    break
            
            if not title:
                # Try common fallbacks
                for selector in ['title', 'h1', 'h2', '.title', '.page-title']:
                    element = soup.select_one(selector)
                    if element and element.get_text(strip=True):
                        title = element.get_text(strip=True)
                        break
            
            if not title:
                title = f"Tender from {site_config['name']} - {url.split('/')[-1]}"
            
            # Extract description
            description = None
            desc_selectors = site_config['selectors']['description'].split(', ')
            for selector in desc_selectors:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True):
                    description = element.get_text(strip=True)
                    break
            
            if not description:
                # Try to get main content
                for selector in ['main', '.content', '.main-content', 'article']:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if len(text) > 50:
                            description = text[:500] + "..." if len(text) > 500 else text
                            break
            
            tender_data = {
                'title': title,
                'url': url,
                'source_site': site_config['name'],
                'description': description or '',
                'budget_currency': 'USD',
                'scraped_at': datetime.utcnow(),
                'last_updated': datetime.utcnow()
            }
            
            return tender_data
            
        except Exception as e:
            logger.error(f"Error scraping tender details from {url}: {str(e)}")
            return None
    
    def save_tender(self, tender_data):
        """Save tender to database"""
        try:
            # Check if tender already exists
            existing = self.db.query(Tender).filter_by(url=tender_data['url']).first()
            
            if existing:
                logger.info(f"Tender already exists: {tender_data['title']}")
                return False
            
            tender = Tender(**tender_data)
            self.db.add(tender)
            self.db.commit()
            logger.info(f"Saved new tender: {tender_data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving tender: {str(e)}")
            self.db.rollback()
            return False
    
    def scrape_site(self, site_key, site_config):
        """Scrape a single site"""
        logger.info(f"Scraping {site_config['name']}...")
        
        if not self.driver:
            self.setup_driver()
        
        try:
            # Extract tender links
            tender_links = self.extract_tender_links(site_config)
            
            if not tender_links:
                logger.warning(f"No tender links found for {site_config['name']}")
                return 0
            
            saved_count = 0
            for i, link in enumerate(tender_links):
                logger.info(f"Scraping tender {i+1}/{len(tender_links)}: {link}")
                
                tender_data = self.scrape_tender_details(link, site_config)
                if tender_data:
                    if self.save_tender(tender_data):
                        saved_count += 1
                
                time.sleep(1)  # Be polite
            
            logger.info(f"Successfully scraped {saved_count} new tenders from {site_config['name']}")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error scraping {site_config['name']}: {str(e)}")
            return 0
    
    def run(self, site_keys=None):
        """Run the scraper on specified sites"""
        if site_keys is None:
            site_keys = ['abt_global', 'dt_global', 'tetratech']  # Working sites only
        
        total_scraped = 0
        
        try:
            for site_key in site_keys:
                if site_key in self.config.SITES_CONFIG:
                    site_config = self.config.SITES_CONFIG[site_key]
                    count = self.scrape_site(site_key, site_config)
                    total_scraped += count
                else:
                    logger.error(f"Unknown site: {site_key}")
        
        finally:
            if self.driver:
                self.driver.quit()
            self.db.close()
        
        logger.info(f"Scraping complete. Total new tenders: {total_scraped}")
        return total_scraped

if __name__ == "__main__":
    scraper = SimpleTenderScraper()
    scraper.run()
