#!/usr/bin/env python3
"""
Tender Scraper Manager for Square Circle Tender System
Consolidated class for web scraping, data management, and CLI interface
"""
import argparse
import asyncio
import aiohttp
import aiofiles
import logging
import os
import hashlib
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import nodriver as uc
from nodriver import *
from config import Config as konfig
from models import Tender, TenderDocument, ScrapingLog, SessionLocal, create_tables
from evaluator import TenderEvaluator

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

# BrowserSetup class
class BrowserSetup:
    """Class to manage nodriver browser setup for web scraping"""
    def __init__(self, user_agent: Optional[UserAgent] = None):
        """Initialize browser setup with optional UserAgent"""
        self.ua = user_agent or UserAgent()

    async def setup_browser(self) -> Browser:
        """Setup nodriver browser with robust options"""
        browser_args = [
            '--no-sandbox',
            '--incognito',
            '--no-first-run',
            '--no-service-autorun',
            '--no-default-browser-check',
            '--homepage=about:blank',
            '--no-pings',
            '--password-store=basic',
            '--disable-infobars',
            '--disable-breakpad',
            '--disable-dev-shm-usage',
            '--disable-session-crashed-bubble',
            '--disable-search-engine-choice-screen',
            '--disable-gpu',
            '--window-size=1920,1080',
            f'--user-agent={self.ua.chrome or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}'
        ]
        
        config = Config(
            headless=True,
            no_sandbox=True,  # Ensures --no-sandbox
            host="127.0.0.1",
            port=0,
            browser_executable_path=None,  # Auto-detect
            browser_args=browser_args
        )
        
        user_data_dir = "/sec/root/Builder/TYLA"
        if os.path.exists(user_data_dir) and os.access(user_data_dir, os.W_OK):
            config.user_data_dir = user_data_dir
            config.use_temp_dir = False
            config._custom_data_dir = True  # Prevent temp profile cleanup
        else:
            logger.warning(f"Invalid user_data_dir {user_data_dir}, using temporary profile")
            config.user_data_dir = None
            config.use_temp_dir = True

        try:
            browser = await uc.start(config=config)
            logger.info(f"Browser started with args: {browser.config.browser_args}")
            await asyncio.sleep(1)
            if not browser.connection or not browser.connection.is_connected:
                raise RuntimeError("Browser connection not established")
            logger.info("Browser initialized successfully")
            return browser
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

class TenderScraperManager:
    def __init__(self):
        self.session = None
        self.ua = UserAgent()
        self.browser_setup = BrowserSetup(user_agent=self.ua)
        self.browser = None
        self.db = SessionLocal()
        self._scraping = False
        self.site_config = konfig.SITES_CONFIG
        self.scraped_tenders = []

    async def setup_browser(self) -> Browser:
        return await self.browser_setup.setup_browser()


    async def login_if_required(self, page: Tab, site_config: Dict) -> bool:
        """Login to site if credentials are required"""
        if not site_config.get('requires_login', False):
            return True

        try:
            login_url = site_config.get('login_url', site_config['base_url'])

            await page.get(login_url)
            await page.sleep(5)  # Handle anti-bot challenges

            if 'cloudflare' in page.url.lower() or 'captcha' in page.url.lower():
                logger.warning("Anti-bot protection detected during login")
                await page.sleep(10)
                if 'cloudflare' in page.url.lower():
                    raise ValueError("Failed to bypass Cloudflare during login")

            email_field = await page.find(site_config['selectors']['email_field'], best_match=True, timeout=10_000)
            if not email_field:
                logger.error(f"Email field {site_config['selectors']['email_field']} not found")
                return False

            site_name = site_config['name'].lower()
            if 'devex' in site_name:
                email = Config.DEVEX_EMAIL
                password = Config.DEVEX_PASSWORD
            elif 'austender' in site_name or 'tenders.gov' in site_name:
                email = Config.TENDERS_GOV_EMAIL
                password = Config.TENDERS_GOV_PASSWORD
            else:
                logger.error(f"No credentials configured for {site_name}")
                return False

            if not email or not password:
                logger.error(f"Missing credentials for {site_name}")
                return False

            password_field = await page.find(site_config['selectors']['password_field'], best_match=True)
            login_button = await page.find(site_config['selectors']['login_button'], best_match=True)

            if not (password_field and login_button):
                logger.error("Password field or login button not found")
                return False

            await email_field.send_keys(email)
            await password_field.send_keys(password)
            await login_button.mouse_click()
            await page.sleep(5)

            current_url = page.url
            if 'login' in current_url.lower() or 'sign-in' in current_url.lower():
                logger.warning(f"Login may have failed for {site_name}")
                return False

            logger.info(f"Successfully logged into {site_name}")
            return True
        except Exception as e:
            logger.error(f"Login failed for {site_config['name']}: {str(e)}")
            return False

    async def extract_tender_links(self, page: Tab, site_config: Dict) -> List[str]:
        """Extract tender links from search/listing page"""
        try:
            search_url = site_config['search_url']
            await page.get(search_url)
            await page.sleep(5)

            if not page.url or 'about:blank' in page.url:
                raise ValueError(f"Failed to load {search_url}")

            if 'cloudflare' in page.url.lower() or 'captcha' in page.url.lower():
                logger.warning("Possible anti-bot protection detected")
                await page.sleep(10)
                if 'cloudflare' in page.url.lower():
                    raise ValueError("Failed to bypass Cloudflare protection")

            link_selector = site_config['selectors']['tender_links']
            link_elements = await page.find(link_selector, best_match=True, all=True)
            if not link_elements:
                logger.warning(f"No elements found for {link_selector}, trying JavaScript fallback")
                script = f'return Array.from(document.querySelectorAll("{link_selector}")).map(e => e.href)'
                link_elements = await page.evaluate(script)
                if not link_elements:
                    logger.warning(f"No links found for {site_config['name']}")
                    return []

            links = []
            invalid_prefixes = ['javascript:', 'mailto:', '#', 'tel:']
            exclude_patterns = ['/careers', '/about', '/contact', '/press', '/subscribe']

            for href in link_elements:
                if isinstance(href, str):
                    full_url = urljoin(site_config['base_url'], href)
                else:
                    full_url = urljoin(site_config['base_url'], await href.get_attribute('href'))
                if (full_url and not any(full_url.startswith(prefix) for prefix in invalid_prefixes) and
                    not any(pattern in full_url for pattern in exclude_patterns) and
                    full_url not in links):
                    links.append(full_url)

            logger.info(f"Found {len(links)} tender links on {site_config['name']}")
            return links
        except Exception as e:
            logger.error(f"Error extracting tender links from {site_config['name']}: {str(e)}")
            return []

    async def scrape_tender_details(self, url: str, page: Tab, site_config: Dict) -> Optional[Dict]:
        """Scrape details from individual tender page"""
        try:
            await page.get(url)
            await page.sleep(2)

            html = await page.get_content()
            soup = BeautifulSoup(html, 'html.parser')

            tender_data = {
                'url': url,
                'source_site': site_config['name'],
                'scraped_at': datetime.utcnow()
            }

            title_selectors = site_config['selectors']['title'].split(', ')
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element and title_element.get_text(strip=True):
                    tender_data['title'] = title_element.get_text(strip=True)
                    break

            if not tender_data.get('title'):
                fallback_selectors = ['title', 'h1', 'h2', '.title', '.page-title']
                for selector in fallback_selectors:
                    element = soup.select_one(selector)
                    if element and element.get_text(strip=True):
                        tender_data['title'] = element.get_text(strip=True)
                        break

            if not tender_data.get('title'):
                tender_data['title'] = f"Tender from {site_config['name']} - {url.split('/')[-1]}"

            desc_selectors = site_config['selectors']['description'].split(', ')
            for selector in desc_selectors:
                desc_element = soup.select_one(selector)
                if desc_element and desc_element.get_text(strip=True):
                    tender_data['description'] = desc_element.get_text(strip=True)
                    break

            if not tender_data.get('description'):
                content_selectors = ['main', '.content', '.main-content', 'article']
                for selector in content_selectors:
                    content_element = soup.select_one(selector)
                    if content_element:
                        text = content_element.get_text(strip=True)
                        if len(text) > 50:
                            tender_data['description'] = text[:500] + "..." if len(text) > 500 else text
                            break

            deadline_selectors = site_config['selectors']['deadline'].split(', ')
            for selector in deadline_selectors:
                deadline_element = soup.select_one(selector)
                if deadline_element:
                    deadline_text = deadline_element.get_text(strip=True)
                    tender_data['deadline'] = self.parse_deadline(deadline_text)
                    break

            budget_selectors = site_config['selectors']['budget'].split(', ')
            for selector in budget_selectors:
                budget_element = soup.select_one(selector)
                if budget_element:
                    budget_text = budget_element.get_text(strip=True)
                    tender_data.update(self.parse_budget(budget_text))
                    break

            page_text = soup.get_text()
            tender_data.update(self.extract_additional_info(page_text))
            tender_data['attachments'] = self.find_attachments(soup, url)

            return tender_data
        except Exception as e:
            logger.error(f"Error scraping tender details from {url}: {str(e)}")
            return None

    def parse_deadline(self, deadline_text: str) -> Optional[datetime]:
        """Parse deadline text into datetime object"""
        if not deadline_text:
            return None

        patterns = [
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
            r'(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, deadline_text)
            if match:
                try:
                    date_str = match.group(1)
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

        currencies = ['USD', 'EUR', 'GBP', 'AUD', 'CAD']
        for currency in currencies:
            if currency in budget_text.upper():
                budget_info['budget_currency'] = currency
                break

        numbers = re.findall(r'[\d,]+\.?\d*', budget_text.replace(',', ''))
        parsed_numbers = []
        for num_str in numbers:
            try:
                num = float(num_str)
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
        """Extract additional information from page text"""
        info = {}
        sector_keywords = ['climate', 'environment', 'governance', 'infrastructure', 'health']
        found_sectors = [keyword for keyword in sector_keywords if keyword in page_text.lower()]
        if found_sectors:
            info['sector'] = ', '.join(found_sectors[:3])

        countries = ['australia', 'fiji', 'vanuatu', 'solomon islands', 'papua new guinea']
        found_locations = [country.title() for country in countries if country in page_text.lower()]
        if found_locations:
            info['location'] = ', '.join(found_locations[:3])
        return info

    def find_attachments(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Find and catalog document attachments"""
        attachments = []
        file_patterns = ['.pdf', '.doc', '.docx', '.rtf']
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text(strip=True)
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

    async def download_attachment(self, attachment: Dict, tender_id: int) -> Optional[str]:
        """Download attachment file and return local path"""
        try:
            url = attachment['url']
            filename = attachment['filename']
            hash_suffix = hashlib.md5(url.encode()).hexdigest()[:8]
            safe_filename = f"{tender_id}_{hash_suffix}_{filename}"
            local_path = os.path.join(Config.ATTACHMENT_PATH, safe_filename)

            async with self.session.get(url, timeout=30) as response:
                response.raise_for_status()
                content = await response.read()

            async with aiofiles.open(local_path, 'wb') as f:
                await f.write(content)

            logger.info(f"Downloaded attachment: {safe_filename}")
            return local_path
        except Exception as e:
            logger.error(f"Error downloading attachment {attachment['url']}: {str(e)}")
            return None

    async def scrape_site(self, site_config: Dict) -> List[Dict]:
        """Scrape a single site"""
        if self._scraping:
            logger.warning(f"Scrape already in progress for {site_config['name']}, skipping")
            return []
        self._scraping = True

        logger.info(f"Starting scrape of {site_config['name']}")
        page = None

        try:
            self.browser = await self.setup_browser()
            try:
                page = await self.browser.get(site_config['base_url'], timeout=10)
                logger.info(f"Loaded base URL: {site_config['base_url']}")
            except Exception as e:
                logger.error(f"Failed to load base URL: {str(e)}")
                return []

            if not await self.login_if_required(page, site_config):
                logger.error(f"Failed to login to {site_config['name']}")
                return []

            tender_links = await self.extract_tender_links(page, site_config)
            if not tender_links:
                logger.warning(f"No tender links found on {site_config['name']}")
                return []

            semaphore = asyncio.Semaphore(3)
            async def scrape_with_limit(url: str) -> Optional[Dict]:
                async with semaphore:
                    try:
                        result = await self.scrape_tender_details(url, page, site_config)
                        await page.sleep(Config.scraping.delay_between_requests)
                        return result
                    except Exception as e:
                        logger.error(f"Error scraping tender {url}: {str(e)}")
                        return None

            tasks = [scrape_with_limit(link) for link in tender_links[:20]]
            scraped_tenders = await asyncio.gather(*tasks, return_exceptions=True)
            results = [tender for tender in scraped_tenders if not isinstance(tender, Exception) and tender is not None]

            logger.info(f"Successfully scraped {len(results)} tenders from {site_config['name']}")
            return results
        except Exception as e:
            logger.error(f"Error scraping {site_config['name']}: {str(e)}")
            return []
        finally:
            self._scraping = False
            if page:
                try:
                    await page.close()
                    logger.info("Closed browser page")
                except Exception as e:
                    logger.error(f"Error closing page: {str(e)}")
            await self.close_browser()

    async def scrape_specific_sites(self, site_keys: List[str]) -> Dict:
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

        for site_key in site_keys:
            if site_key not in self.site_config:
                logger.error(f"Unknown site: {site_key}")
                results['failed_sites'] += 1
                results['site_results'][site_key] = {'error': f"Unknown site: {site_key}"}
                continue

            site_config = self.site_config[site_key]
            logger.info(f"Scraping {site_config['name']}...")
            log = ScrapingLog(
                site_name=site_config['name'],
                start_time=datetime.utcnow(),
                status='running'
            )
            self.db.add(log)
            self.db.commit()

            try:
                tender_data_list = await self.scrape_site(site_config)
                site_stats = self.process_scraped_data(tender_data_list, site_config['name'])

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
                log.end_time = datetime.utcnow()
                log.status = 'failed'
                log.error_message = str(e)
                results['failed_sites'] += 1
                results['site_results'][site_config['name']] = {'error': str(e)}
            finally:
                self.db.commit()

        return results

    async def scrape_all_sites(self) -> Dict:
        """Scrape all configured sites"""
        results = {
            'total_sites': len(self.site_config),
            'successful_sites': 0,
            'failed_sites': 0,
            'total_tenders': 0,
            'new_tenders': 0,
            'updated_tenders': 0,
            'site_results': {}
        }

        async def scrape_site_with_config(site_key, site_config):
            logger.info(f"Starting scrape of {site_config['name']}")
            log = ScrapingLog(
                site_name=site_config['name'],
                start_time=datetime.utcnow(),
                status='running'
            )
            self.db.add(log)
            self.db.commit()

            try:
                tender_data_list = await self.scrape_site(site_config)
                site_stats = self.process_scraped_data(tender_data_list, site_config['name'])

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
                log.end_time = datetime.utcnow()
                log.status = 'failed'
                log.error_message = str(e)
                results['failed_sites'] += 1
                results['site_results'][site_config['name']] = {'error': str(e)}
            finally:
                self.db.commit()

        tasks = [
            scrape_site_with_config(site_key, site_config)
            for site_key, site_config in self.site_config.items()
            if site_key not in {t.get_name() for t in asyncio.all_tasks()}
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def process_scraped_data(self, tender_data_list: List[Dict], site_name: str) -> Dict:
        """Process scraped tender data and save to database"""
        stats = {'new': 0, 'updated': 0, 'errors': 0}

        for tender_data in tender_data_list:
            try:
                existing_tender = self.db.query(Tender).filter_by(url=tender_data['url']).first()
                if existing_tender:
                    for key, value in tender_data.items():
                        if key != 'attachments' and hasattr(existing_tender, key):
                            setattr(existing_tender, key, value)
                    existing_tender.last_updated = datetime.utcnow()
                    tender = existing_tender
                    stats['updated'] += 1
                else:
                    tender_data_copy = tender_data.copy()
                    attachments = tender_data_copy.pop('attachments', [])
                    if not tender_data_copy.get('title'):
                        logger.warning(f"Skipping tender with no title: {tender_data_copy.get('url')}")
                        stats['errors'] += 1
                        continue

                    tender_data_copy.setdefault('description', '')
                    tender_data_copy.setdefault('budget_currency', 'USD')
                    tender_data_copy.setdefault('last_updated', datetime.utcnow())
                    tender = Tender(**tender_data_copy)
                    self.db.add(tender)
                    self.db.flush()
                    stats['new'] += 1

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
        for attachment_data in attachments:
            try:
                existing_doc = self.db.query(TenderDocument).filter_by(
                    tender_id=tender_id,
                    original_url=attachment_data['url']
                ).first()
                if not existing_doc:
                    local_path = asyncio.run(self.download_attachment(attachment_data, tender_id))
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

    def run_evaluation(self):
        """Run tender evaluation"""
        try:
            evaluator = TenderEvaluator()
            results = evaluator.evaluate_all_tenders()
            successful = len([r for r in results if 'error' not in r])
            failed = len(results) - successful
            logger.info(f"Evaluation completed: {successful} successful, {failed} failed")

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

    def display_scraping_results(self, results: Dict):
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

    def show_status(self):
        """Show system status"""
        logger.info("=" * 50)
        logger.info("SYSTEM STATUS")
        logger.info("=" * 50)
        try:
            tender_count = self.db.query(Tender).count()
            document_count = self.db.query(TenderDocument).count()
            log_count = self.db.query(ScrapingLog).count()
            logger.info(f"Database: Connected")
            logger.info(f"Total tenders: {tender_count}")
            logger.info(f"Total documents: {document_count}")
            logger.info(f"Scraping logs: {log_count}")

            recent_tenders = self.db.query(Tender).filter(
                Tender.scraped_at >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count()
            logger.info(f"Tenders scraped today: {recent_tenders}")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")

        logger.info("")
        logger.info("Configuration:")
        logger.info(f"OpenAI API: {'Configured' if Config.OPENAI_API_KEY else 'Missing'}")
        logger.info(f"Devex credentials: {'Configured' if Config.DEVEX_EMAIL else 'Missing'}")
        logger.info(f"Tenders.gov.au credentials: {'Configured' if Config.TENDERS_GOV_EMAIL else 'Missing'}")

        logger.info("")
        logger.info("Configured sites:")
        for site_key, site_config in self.site_config.items():
            login_required = site_config.get('requires_login', False)
            status = "Requires login" if login_required else "Public"
            logger.info(f"  {site_config['name']}: {status}")
        logger.info("=" * 50)

    async def close_browser(self):
        """Clean up browser resources"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                logger.info("Closed aiohttp session")
            if self.browser and hasattr(self.browser, 'stop'):
                try:
                    await self.browser.stop()
                    logger.info("Closed nodriver browser")
                except Exception as e:
                    logger.error(f"Error stopping browser: {str(e)}")
                self.browser = None
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def close(self):
        """Clean up all resources"""
        self.db.close()
        logger.info("Closed database session")

    async def run(self):
        """Run CLI interface"""
        parser = argparse.ArgumentParser(description='Square Circle Tender Scraper')
        parser.add_argument('--sites', nargs='+', help='Specific sites to scrape',
                            choices=list(self.site_config.keys()))
        parser.add_argument('--evaluate', action='store_true',
                            help='Run evaluation after scraping')
        parser.add_argument('--init-db', action='store_true',
                            help='Initialize database tables')
        parser.add_argument('--status', action='store_true',
                            help='Show system status')
        args = parser.parse_args()

        try:
            if args.init_db:
                logger.info("Initializing database tables...")
                create_tables()
                logger.info("Database tables created successfully!")
                return

            if args.status:
                self.show_status()
                return

            create_tables()
            logger.info("Starting scraping operation...")
            if args.sites:
                logger.info(f"Scraping specific sites: {args.sites}")
                results = await self.scrape_specific_sites(args.sites)
            else:
                logger.info("Scraping all configured sites...")
                results = await self.scrape_all_sites()

            self.display_scraping_results(results)
            if args.evaluate:
                logger.info("Running tender evaluation...")
                self.run_evaluation()
        except Exception as e:
            logger.error(f"Scraping operation failed: {str(e)}")
        finally:
            await self.close_browser()
            self.close()

if __name__ == "__main__":
    manager = TenderScraperManager()
    try:
        asyncio.run(manager.run())
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        uc.loop().run_until_complete(manager.run())
    finally:
        manager.close()
