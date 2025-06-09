"""
Web Scraping Module for Square Circle Tender System
Handles scraping of both public and login-required tender sites
"""
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import chromedriver_autoinstaller
from fake_useragent import UserAgent
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import os
import hashlib
from typing import List, Dict, Optional, Tuple
from config import Config
from models import Tender, TenderDocument, ScrapingLog, SessionLocal
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TenderScraper:
    """Base class for scraping tender sites"""
    
    def __init__(self, site_config: Dict):
        """Initialize scraper with site configuration"""
        self.site_config = site_config
        self.session = requests.Session()
        self.ua = UserAgent()
        self.driver = None
        self.scraped_tenders = []
        
        # Setup Chrome driver
        chromedriver_autoinstaller.install()
        
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(Config.scraping.timeout)
        return driver
    
    def login_if_required(self) -> bool:
        """Login to site if credentials are required"""
        if not self.site_config.get('requires_login', False):
            return True
        
        try:
            login_url = self.site_config['login_url']
            self.driver.get(login_url)
            
            # Wait for login form to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.site_config['selectors']['email_field']))
            )
            
            # Get credentials based on site
            site_name = self.site_config['name'].lower()
            if 'devex' in site_name:
                email = Config.DEVEX_EMAIL
                password = Config.DEVEX_PASSWORD
            elif 'tenders.gov' in site_name:
                email = Config.TENDERS_GOV_EMAIL
                password = Config.TENDERS_GOV_PASSWORD
            else:
                logger.error(f"No credentials configured for {site_name}")
                return False
            
            if not email or not password:
                logger.error(f"Missing credentials for {site_name}")
                return False
              # Fill login form
            email_field = self.driver.find_element(By.CSS_SELECTOR, self.site_config['selectors']['email_field'])
            password_field = self.driver.find_element(By.CSS_SELECTOR, self.site_config['selectors']['password_field'])
            login_button = self.driver.find_element(By.CSS_SELECTOR, self.site_config['selectors']['login_button'])
            
            email_field.send_keys(email)
            password_field.send_keys(password)
            login_button.click()
            
            # Wait for login to complete
            time.sleep(3)
            
            # Check if login was successful (basic check)
            current_url = self.driver.current_url
            if 'login' in current_url.lower() or 'sign-in' in current_url.lower():
                logger.warning(f"Login may have failed for {site_name}")
                return False
            
            logger.info(f"Successfully logged into {site_name}")
            return True
        except Exception as e:
            logger.error(f"Login failed for {self.site_config['name']}: {str(e)}")
            return False

    def extract_tender_links(self) -> List[str]:
        """Extract tender links from search/listing page"""
        try:
            search_url = self.site_config['search_url']
            self.driver.get(search_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Extract links using CSS selectors
            link_selector = self.site_config['selectors']['tender_links']
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, link_selector)
            
            links = []
            invalid_prefixes = ['javascript:', 'mailto:', '#', 'tel:']
            exclude_patterns = [
                '/careers', '/about', '/contact', '/press', '/subscribe', 
                '/board-of-directors', '/executive-leadership', '/expertise',
                '/impact/', '/doing-business-with-abt$'  # Main page, not specific solicitations
            ]
            
            for element in link_elements:
                href = element.get_attribute('href')
                if href and not any(href.startswith(prefix) for prefix in invalid_prefixes):
                    # Skip general navigation links
                    if not any(pattern in href for pattern in exclude_patterns):
                        full_url = urljoin(self.site_config['base_url'], href)
                        if full_url not in links:  # Avoid duplicates
                            links.append(full_url)
            
            logger.info(f"Found {len(links)} tender links on {self.site_config['name']}")
            return links
            
        except Exception as e:
            logger.error(f"Error extracting tender links from {self.site_config['name']}: {str(e)}")
            return []
    
    def scrape_tender_details(self, url: str) -> Optional[Dict]:
        """Scrape details from individual tender page"""
        try:
            self.driver.get(url)
            time.sleep(2)
            
            # Get page source for BeautifulSoup parsing
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            tender_data = {
                'url': url,
                'source_site': self.site_config['name'],
                'scraped_at': datetime.utcnow()
            }
            
            # Extract title with fallbacks
            title = None
            title_selectors = self.site_config['selectors']['title'].split(', ')
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element and title_element.get_text(strip=True):
                    title = title_element.get_text(strip=True)
                    break
            
            # If no title found, try common fallbacks
            if not title:
                fallback_selectors = ['title', 'h1', 'h2', '.title', '.page-title', '.entry-title']
                for selector in fallback_selectors:
                    element = soup.select_one(selector)
                    if element and element.get_text(strip=True):
                        title = element.get_text(strip=True)
                        break
            
            # If still no title, generate from URL
            if not title:
                title = f"Tender from {self.site_config['name']} - {url.split('/')[-1]}"
            
            tender_data['title'] = title
            
            # Extract description with fallbacks
            description = None
            desc_selectors = self.site_config['selectors']['description'].split(', ')
            for selector in desc_selectors:
                desc_element = soup.select_one(selector)
                if desc_element and desc_element.get_text(strip=True):
                    description = desc_element.get_text(strip=True)
                    break
            
            # If no description found, try to extract from page content
            if not description:
                # Get main content areas
                content_selectors = ['main', '.content', '.main-content', 'article', '.article']
                for selector in content_selectors:
                    content_element = soup.select_one(selector)
                    if content_element:
                        text = content_element.get_text(strip=True)
                        if len(text) > 50:  # Ensure it's substantial content
                            description = text[:500] + "..." if len(text) > 500 else text
                            break
            
            tender_data['description'] = description
            
            # Extract deadline
            deadline_selectors = self.site_config['selectors']['deadline'].split(', ')
            for selector in deadline_selectors:
                deadline_element = soup.select_one(selector)
                if deadline_element:
                    deadline_text = deadline_element.get_text(strip=True)
                    tender_data['deadline'] = self.parse_deadline(deadline_text)
                    break
            
            # Extract budget
            budget_selectors = self.site_config['selectors']['budget'].split(', ')
            for selector in budget_selectors:
                budget_element = soup.select_one(selector)
                if budget_element:
                    budget_text = budget_element.get_text(strip=True)
                    budget_info = self.parse_budget(budget_text)
                    tender_data.update(budget_info)
                    break
            
            # Extract additional information from page content
            page_text = soup.get_text()
            tender_data.update(self.extract_additional_info(page_text))
            
            # Find and download attachments
            attachments = self.find_attachments(soup, url)
            tender_data['attachments'] = attachments
            
            return tender_data
            
        except Exception as e:
            logger.error(f"Error scraping tender details from {url}: {str(e)}")
            return None
    
    def parse_deadline(self, deadline_text: str) -> Optional[datetime]:
        """Parse deadline text into datetime object"""
        if not deadline_text:
            return None
        
        # Common date patterns
        patterns = [
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',  # DD/MM/YYYY or MM/DD/YYYY
            r'(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2}\s+\w+\s+\d{4})',                # DD Month YYYY
            r'(\w+\s+\d{1,2},?\s+\d{4})',              # Month DD, YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, deadline_text)
            if match:
                try:
                    date_str = match.group(1)
                    # Try different parsing formats
                    for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d %B %Y', '%B %d, %Y', '%d-%m-%Y']:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except:
                    pass
        
        return None
    
    def parse_budget(self, budget_text: str) -> Dict:
        """Parse budget text to extract budget information"""
        budget_info = {
            'budget_min': None,
            'budget_max': None,
            'budget_currency': 'USD'
        }
        
        if not budget_text:
            return budget_info
        
        # Extract currency
        currencies = ['USD', 'EUR', 'GBP', 'AUD', 'CAD']
        for currency in currencies:
            if currency in budget_text.upper():
                budget_info['budget_currency'] = currency
                break
        
        # Extract numbers (remove commas, handle millions/thousands)
        numbers = re.findall(r'[\d,]+\.?\d*', budget_text.replace(',', ''))
        parsed_numbers = []
        
        for num_str in numbers:
            try:
                num = float(num_str)
                # Handle millions and thousands
                if 'million' in budget_text.lower() or 'mil' in budget_text.lower():
                    num *= 1000000
                elif 'thousand' in budget_text.lower() or 'k' in budget_text.lower():
                    num *= 1000
                parsed_numbers.append(num)
            except ValueError:
                pass
        
        if parsed_numbers:
            if len(parsed_numbers) == 1:
                budget_info['budget_max'] = parsed_numbers[0]
            else:
                budget_info['budget_min'] = min(parsed_numbers)
                budget_info['budget_max'] = max(parsed_numbers)
        
        return budget_info
    
    def extract_additional_info(self, page_text: str) -> Dict:
        """Extract additional information from page text using patterns"""
        info = {}
        
        # Extract sector/industry keywords
        sector_keywords = [
            'climate', 'environment', 'governance', 'infrastructure', 'health',
            'education', 'agriculture', 'water', 'energy', 'development'
        ]
        
        found_sectors = []
        for keyword in sector_keywords:
            if keyword in page_text.lower():
                found_sectors.append(keyword)
        
        if found_sectors:
            info['sector'] = ', '.join(found_sectors[:3])  # Top 3 sectors
        
        # Extract location information
        countries = [
            'australia', 'fiji', 'vanuatu', 'solomon islands', 'papua new guinea',
            'tonga', 'samoa', 'kiribati', 'tuvalu', 'nauru', 'palau', 'marshall islands',
            'pacific', 'asia', 'africa', 'latin america'
        ]
        
        found_locations = []
        for country in countries:
            if country in page_text.lower():
                found_locations.append(country.title())
        
        if found_locations:
            info['location'] = ', '.join(found_locations[:3])
        
        return info
    
    def find_attachments(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Find and catalog document attachments"""
        attachments = []
        
        # Look for PDF and Word document links
        file_patterns = ['.pdf', '.doc', '.docx', '.rtf']
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text(strip=True)
            
            # Check if link points to a document
            for pattern in file_patterns:
                if pattern in href.lower() or pattern in link_text.lower():
                    full_url = urljoin(base_url, href)
                    attachments.append({
                        'url': full_url,
                        'filename': os.path.basename(urlparse(href).path) or f"document{pattern}",
                        'description': link_text,
                        'file_type': pattern.replace('.', '')
                    })
                    break
        
        return attachments
    
    def download_attachment(self, attachment: Dict, tender_id: int) -> Optional[str]:
        """Download attachment file and return local path"""
        try:
            url = attachment['url']
            filename = attachment['filename']
            
            # Create unique filename to avoid conflicts
            hash_suffix = hashlib.md5(url.encode()).hexdigest()[:8]
            safe_filename = f"{tender_id}_{hash_suffix}_{filename}"
            local_path = os.path.join(Config.ATTACHMENT_PATH, safe_filename)
            
            # Download file
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded attachment: {safe_filename}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading attachment {attachment['url']}: {str(e)}")
            return None
    
    def scrape_site(self) -> List[Dict]:
        """Main method to scrape the entire site"""
        logger.info(f"Starting scrape of {self.site_config['name']}")
        
        try:
            # Setup driver
            self.driver = self.setup_driver()
            
            # Login if required
            if not self.login_if_required():
                logger.error(f"Failed to login to {self.site_config['name']}")
                return []
            
            # Extract tender links
            tender_links = self.extract_tender_links()
            
            if not tender_links:
                logger.warning(f"No tender links found on {self.site_config['name']}")
                return []
            
            # Scrape each tender
            scraped_tenders = []
            for i, link in enumerate(tender_links[:20]):  # Limit for demo
                logger.info(f"Scraping tender {i+1}/{min(len(tender_links), 20)}: {link}")
                
                tender_data = self.scrape_tender_details(link)
                if tender_data:
                    scraped_tenders.append(tender_data)
                
                # Add delay between requests
                time.sleep(Config.scraping.delay_between_requests)
            
            logger.info(f"Successfully scraped {len(scraped_tenders)} tenders from {self.site_config['name']}")
            return scraped_tenders
            
        except Exception as e:
            logger.error(f"Error scraping {self.site_config['name']}: {str(e)}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()

class ScrapingManager:
    """Manages scraping operations across multiple sites"""
    
    def __init__(self):
        """Initialize scraping manager"""
        self.db = SessionLocal()
    
    def scrape_all_sites(self) -> Dict:
        """Scrape all configured sites and return summary"""
        results = {
            'total_sites': len(Config.SITES_CONFIG),
            'successful_sites': 0,
            'failed_sites': 0,
            'total_tenders': 0,
            'new_tenders': 0,
            'updated_tenders': 0,
            'site_results': {}
        }
        
        for site_key, site_config in Config.SITES_CONFIG.items():
            logger.info(f"Starting scrape of {site_config['name']}")
            
            # Create scraping log entry
            log = ScrapingLog(
                site_name=site_config['name'],
                start_time=datetime.utcnow(),
                status='running'
            )
            self.db.add(log)
            self.db.commit()
            
            try:
                # Create scraper and run
                scraper = TenderScraper(site_config)
                tender_data_list = scraper.scrape_site()
                
                # Process scraped data
                site_stats = self.process_scraped_data(tender_data_list, site_config['name'])
                
                # Update log
                log.end_time = datetime.utcnow()
                log.status = 'success'
                log.tenders_found = len(tender_data_list)
                log.tenders_new = site_stats['new']
                log.tenders_updated = site_stats['updated']
                
                results['successful_sites'] += 1
                results['total_tenders'] += len(tender_data_list)
                results['new_tenders'] += site_stats['new']
                results['updated_tenders'] += site_stats['updated']
                results['site_results'][site_config['name']] = site_stats
                
            except Exception as e:
                logger.error(f"Failed to scrape {site_config['name']}: {str(e)}")
                
                # Update log
                log.end_time = datetime.utcnow()
                log.status = 'failed'
                log.error_message = str(e)
                
                results['failed_sites'] += 1
                results['site_results'][site_config['name']] = {'error': str(e)}
            
            finally:
                self.db.commit()
        
        return results
    
    def process_scraped_data(self, tender_data_list: List[Dict], site_name: str) -> Dict:
        """Process scraped tender data and save to database"""
        stats = {'new': 0, 'updated': 0, 'errors': 0}
        
        for tender_data in tender_data_list:
            try:
                # Check if tender already exists
                existing_tender = self.db.query(Tender).filter_by(
                    url=tender_data['url']
                ).first()
                
                if existing_tender:
                    # Update existing tender
                    for key, value in tender_data.items():
                        if key != 'attachments' and hasattr(existing_tender, key):
                            setattr(existing_tender, key, value)
                    existing_tender.last_updated = datetime.utcnow()
                    tender = existing_tender
                    stats['updated'] += 1
                else:
                    # Create new tender
                    tender_data_copy = tender_data.copy()
                    attachments = tender_data_copy.pop('attachments', [])
                    
                    # Validate required fields to prevent NULL constraint errors
                    if not tender_data_copy.get('title'):
                        logger.warning(f"Skipping tender with no title: {tender_data_copy.get('url')}")
                        stats['errors'] += 1
                        continue
                    
                    # Ensure all required fields have default values
                    tender_data_copy.setdefault('description', '')
                    tender_data_copy.setdefault('budget_currency', 'USD')
                    tender_data_copy.setdefault('last_updated', datetime.utcnow())
                    
                    tender = Tender(**tender_data_copy)
                    self.db.add(tender)
                    self.db.flush()  # Get the ID
                    stats['new'] += 1
                
                # Handle attachments
                if 'attachments' in tender_data:
                    self.process_attachments(tender_data['attachments'], tender.id)
                
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Error processing tender data: {str(e)}")
                stats['errors'] += 1
                self.db.rollback()
        
        return stats
    
    def process_attachments(self, attachments: List[Dict], tender_id: int):
        """Process and save tender attachments"""
        scraper = TenderScraper({})  # Create instance for download method
        
        for attachment_data in attachments:
            try:
                # Check if document already exists
                existing_doc = self.db.query(TenderDocument).filter_by(
                    tender_id=tender_id,
                    original_url=attachment_data['url']
                ).first()
                
                if not existing_doc:
                    # Download file
                    local_path = scraper.download_attachment(attachment_data, tender_id)
                    
                    # Create document record
                    doc = TenderDocument(
                        tender_id=tender_id,
                        filename=attachment_data['filename'],
                        original_url=attachment_data['url'],
                        local_path=local_path,
                        file_type=attachment_data.get('file_type', 'unknown')
                    )
                    
                    if local_path and os.path.exists(local_path):
                        doc.file_size = os.path.getsize(local_path)
                    
                    self.db.add(doc)
                
            except Exception as e:
                logger.error(f"Error processing attachment: {str(e)}")
    
    def close(self):
        """Close database connection"""
        self.db.close()

# Example usage
if __name__ == "__main__":
    # Test scraping a single site
    site_config = Config.SITES_CONFIG['abt_global']
    scraper = TenderScraper(site_config)
    
    tenders = scraper.scrape_site()
    print(f"Scraped {len(tenders)} tenders from {site_config['name']}")
    
    for tender in tenders[:2]:  # Show first 2
        print(f"Title: {tender.get('title', 'N/A')}")
        print(f"URL: {tender.get('url', 'N/A')}")
        print(f"Description: {tender.get('description', 'N/A')[:100]}...")
        print("---")
