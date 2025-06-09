"""
Configuration settings for the Square Circle Tender Curation System
"""
import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class EvaluationCriteria:
    """Defines evaluation criteria and weights for tender scoring"""
    priority_sectors: Dict[str, float] = None
    geographic_preferences: Dict[str, float] = None
    budget_ranges: Dict[str, float] = None
    experience_multiplier: float = 2.0
    deadline_penalty_days: int = 30
    
    def __post_init__(self):
        if self.priority_sectors is None:
            self.priority_sectors = {
                "climate change": 3.0,
                "resource governance": 2.8,
                "infrastructure": 2.5,
                "environmental": 2.7,
                "governance": 2.3,
                "development": 2.0,
                "capacity building": 2.2,
                "policy": 2.1
            }
        
        if self.geographic_preferences is None:
            self.geographic_preferences = {
                "pacific": 3.0,
                "asia": 2.5,
                "africa": 2.3,
                "latin america": 2.0,
                "caribbean": 2.2,
                "global": 1.8
            }
        
        if self.budget_ranges is None:
            self.budget_ranges = {
                "50000-200000": 3.0,    # Sweet spot for Square Circle
                "200000-500000": 2.5,
                "500000-1000000": 2.0,
                "1000000+": 1.5,
                "under_50000": 1.8
            }

@dataclass
class ScrapingConfig:
    """Configuration for web scraping operations"""
    delay_between_requests: int = 2
    max_retries: int = 3
    timeout: int = 30
    user_agents: List[str] = None
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]

class Config:
    """Main configuration class"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Site Credentials
    DEVEX_EMAIL = os.getenv('DEVEX_EMAIL')
    DEVEX_PASSWORD = os.getenv('DEVEX_PASSWORD')
    TENDERS_GOV_EMAIL = os.getenv('TENDERS_GOV_EMAIL')
    TENDERS_GOV_PASSWORD = os.getenv('TENDERS_GOV_PASSWORD')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///tenders.db')
    
    # Paths
    EXPORT_PATH = os.getenv('EXPORT_PATH', 'exports/')
    ATTACHMENT_PATH = os.getenv('ATTACHMENT_PATH', 'attachments/')
    
    # AI Configuration
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2000'))
    
    # Evaluation and Scraping Config
    evaluation = EvaluationCriteria()
    scraping = ScrapingConfig()
    
    # Target Sites Configuration
    SITES_CONFIG = {
        'devex': {
            'name': 'Devex.org',
            'base_url': 'https://www.devex.com',
            'login_url': 'https://www.devex.com/en/sign-in',
            'search_url': 'https://www.devex.com/en/funding',
            'requires_login': True,
            'selectors': {
                'email_field': 'input[name="email"]',
                'password_field': 'input[name="password"]',
                'login_button': 'button[type="submit"]',
                'tender_links': '.funding-item a',
                'title': 'h1',
                'description': '.description',
                'deadline': '.deadline',
                'budget': '.budget'
            }
        },
        'tenders_gov_au': {
            'name': 'Tenders.gov.au',
            'base_url': 'https://www.tenders.gov.au',
            'login_url': 'https://www.tenders.gov.au/Atm/Common/Login.aspx',
            'search_url': 'https://www.tenders.gov.au/',
            'requires_login': True,
            'selectors': {                'email_field': '#ctl00_MainContent_txtUserName',
                'password_field': '#ctl00_MainContent_txtPassword',
                'login_button': '#ctl00_MainContent_btnLogin',
                'tender_links': '.home-buttons a, a.rBtn',
                'title': 'h1',
                'description': '.tender-description',
                'deadline': '.closing-date',
                'budget': '.tender-value'
            }
        },        'abt_global': {
            'name': 'Abt Global',
            'base_url': 'https://www.abtglobal.com',
            'search_url': 'https://www.abtglobal.com/doing-business-with-abt/solicitations',
            'requires_login': False,
            'selectors': {
                'tender_links': 'a[href*="solicitations"][href*="field_person_type"]',
                'title': 'h1, .title, .page-title',
                'description': '.description, .content, .field-content',
                'deadline': '.deadline, .closing-date, .field-closing-date',
                'budget': '.value, .budget, .field-budget'
            }
        },
        'spc': {
            'name': 'SPC (Pacific Community)',
            'base_url': 'https://www.spc.int',
            'search_url': 'https://www.spc.int/procurement',
            'requires_login': False,            'selectors': {
                'tender_links': '.views-field a, .field-content a',
                'title': 'h1, .title',
                'description': '.description, .content',
                'deadline': '.deadline, .closing-date',
                'budget': '.value, .budget'
            }
        },
        'tetratech': {
            'name': 'Tetra Tech International Development',
            'base_url': 'https://intdev.tetratech.com.au',
            'search_url': 'https://intdev.tetratech.com.au/partner-with-us/',
            'requires_login': False,            'selectors': {
                'tender_links': 'a[href*=".pdf"], a[href*=".docx"], a[href*="tender"]',
                'title': 'h1, .title',
                'description': '.description, .content',
                'deadline': '.deadline, .closing-date',
                'budget': '.value, .budget'
            }
        },
        'transparency_intl': {
            'name': 'Transparency International',
            'base_url': 'https://www.transparency.org',
            'search_url': 'https://www.transparency.org/en/career-tender-opportunities',
            'requires_login': False,
            'selectors': {
                'tender_links': '.opportunity-item a, .tender-link',
                'title': 'h1, .title',
                'description': '.description, .content',
                'deadline': '.deadline, .closing-date',
                'budget': '.value, .budget'
            }
        },
        'dt_global': {
            'name': 'DT Global',
            'base_url': 'https://dt-global.com',
            'search_url': 'https://dt-global.com/proposals/',
            'requires_login': False,            'selectors': {
                'tender_links': '.oxy-repeater-pages a, .ct-span a[href*="proposals/"]',
                'title': 'h1, .title',
                'description': '.description, .content',
                'deadline': '.deadline, .closing-date',
                'budget': '.value, .budget'
            }
        }
    }

# Create directories if they don't exist
for path in [Config.EXPORT_PATH, Config.ATTACHMENT_PATH]:
    os.makedirs(path, exist_ok=True)
