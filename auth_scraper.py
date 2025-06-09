"""
Authentication-based scraper for premium tender sites
Handles login-required sites like Devex.org and Transparency International
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
from datetime import datetime
from urllib.parse import urljoin, urlparse
import os
from typing import List, Dict, Optional
from config import Config
from models import Tender, SessionLocal
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticatedScraper:
    """Scraper for sites requiring authentication"""
    
    def __init__(self):
        """Initialize the authenticated scraper"""
        self.session = requests.Session()
        self.ua = UserAgent()
        self.driver = None
        self.scraped_tenders = []
        
        # Setup Chrome driver
        chromedriver_autoinstaller.install()
        
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with stealth options"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add realistic user agent
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        
        # Add headers to avoid detection
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    def login_devex(self) -> bool:
        """Login to Devex.org"""
        try:
            self.driver = self.setup_driver()
            
            # Navigate to login page
            login_url = "https://www.devex.com/users/sign_in"
            self.driver.get(login_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Check if we have credentials
            if not Config.DEVEX_EMAIL or not Config.DEVEX_PASSWORD:
                logger.error("Missing Devex credentials")
                return False
            
            # Find and fill login form
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "user_email"))
            )
            password_field = self.driver.find_element(By.ID, "user_password")
            
            email_field.send_keys(Config.DEVEX_EMAIL)
            password_field.send_keys(Config.DEVEX_PASSWORD)
            
            # Submit form
            login_button = self.driver.find_element(By.XPATH, "//input[@type='submit'][@value='Sign in']")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            current_url = self.driver.current_url
            if 'sign_in' not in current_url and 'dashboard' in current_url:
                logger.info("Successfully logged into Devex")
                return True
            else:
                logger.warning("Devex login may have failed")
                return False
                
        except Exception as e:
            logger.error(f"Devex login failed: {str(e)}")
            return False
    
    def scrape_devex_tenders(self) -> List[Dict]:
        """Scrape tenders from Devex after authentication"""
        tenders = []
        
        if not self.login_devex():
            return tenders
            
        try:
            # Navigate to funding opportunities
            funding_url = "https://www.devex.com/funding"
            self.driver.get(funding_url)
            time.sleep(3)
            
            # Find tender links
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for funding opportunity links
            opportunity_links = soup.find_all('a', href=re.compile(r'/funding/\d+'))
            
            for link in opportunity_links[:10]:  # Limit to first 10
                try:
                    tender_url = urljoin("https://www.devex.com", link.get('href'))
                    title = link.get_text(strip=True)
                    
                    if title and len(title) > 10:  # Basic quality filter
                        tender_data = {
                            'title': title,
                            'url': tender_url,
                            'source_site': 'Devex.org',
                            'scraped_at': datetime.utcnow(),
                            'description': f"Funding opportunity from Devex: {title}",
                            'sector': 'Development',
                            'location': 'Global',
                        }
                        tenders.append(tender_data)
                        logger.info(f"Found Devex tender: {title}")
                        
                except Exception as e:
                    logger.error(f"Error processing Devex tender: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping Devex tenders: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                
        return tenders
    
    def login_transparency_international(self) -> bool:
        """Login to Transparency International"""
        try:
            self.driver = self.setup_driver()
            
            # Navigate to main site (they may not have a standard login)
            main_url = "https://www.transparency.org"
            self.driver.get(main_url)
            time.sleep(3)
            
            # Look for careers/opportunities section
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try to find careers or opportunities link
            careers_link = soup.find('a', href=re.compile(r'career|job|opportunit', re.I))
            if careers_link:
                careers_url = urljoin(main_url, careers_link.get('href'))
                self.driver.get(careers_url)
                time.sleep(3)
                logger.info("Navigated to Transparency International opportunities")
                return True
            else:
                logger.info("No login required for Transparency International")
                return True
                
        except Exception as e:
            logger.error(f"Transparency International access failed: {str(e)}")
            return False
    
    def scrape_transparency_tenders(self) -> List[Dict]:
        """Scrape opportunities from Transparency International"""
        tenders = []
        
        if not self.login_transparency_international():
            return tenders
            
        try:
            # Look for tender/opportunity announcements
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find opportunity links
            opportunity_links = soup.find_all('a', href=re.compile(r'tender|rfp|procurement|opportunit', re.I))
            
            for link in opportunity_links[:5]:  # Limit to first 5
                try:
                    tender_url = urljoin("https://www.transparency.org", link.get('href'))
                    title = link.get_text(strip=True)
                    
                    if title and len(title) > 10:
                        tender_data = {
                            'title': title,
                            'url': tender_url,
                            'source_site': 'Transparency International',
                            'scraped_at': datetime.utcnow(),
                            'description': f"Opportunity from Transparency International: {title}",
                            'sector': 'Governance',
                            'location': 'Global',
                        }
                        tenders.append(tender_data)
                        logger.info(f"Found TI opportunity: {title}")
                        
                except Exception as e:
                    logger.error(f"Error processing TI opportunity: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping TI opportunities: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                
        return tenders
    
    def save_tenders_to_db(self, tenders: List[Dict]):
        """Save scraped tenders to database"""
        db = SessionLocal()
        try:
            for tender_data in tenders:
                # Check if tender already exists
                existing = db.query(Tender).filter_by(url=tender_data['url']).first()
                
                if not existing:
                    # Create new tender
                    tender = Tender(**tender_data)
                    db.add(tender)
                    logger.info(f"Added new tender: {tender_data['title']}")
                else:
                    logger.info(f"Tender already exists: {tender_data['title']}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving tenders: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def run_authenticated_scraping(self):
        """Run full authenticated scraping process"""
        logger.info("Starting authenticated scraping...")
        
        all_tenders = []
        
        # Scrape Devex
        logger.info("Scraping Devex...")
        devex_tenders = self.scrape_devex_tenders()
        all_tenders.extend(devex_tenders)
        
        # Wait between sites
        time.sleep(5)
        
        # Scrape Transparency International
        logger.info("Scraping Transparency International...")
        ti_tenders = self.scrape_transparency_tenders()
        all_tenders.extend(ti_tenders)
        
        # Save to database
        if all_tenders:
            self.save_tenders_to_db(all_tenders)
            logger.info(f"Completed authenticated scraping. Found {len(all_tenders)} tenders.")
        else:
            logger.info("No tenders found during authenticated scraping.")
        
        return all_tenders

if __name__ == "__main__":
    scraper = AuthenticatedScraper()
    tenders = scraper.run_authenticated_scraping()
    print(f"Scraped {len(tenders)} tenders from authenticated sites")
