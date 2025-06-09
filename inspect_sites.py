#!/usr/bin/env python3
"""
Script to inspect target websites and identify correct CSS selectors
"""
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse

def inspect_site(site_config, site_key):
    """Inspect a site and find appropriate selectors"""
    print(f"\n{'='*50}")
    print(f"Inspecting: {site_config['name']}")
    print(f"URL: {site_config['search_url']}")
    print(f"{'='*50}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(site_config['search_url'], headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Failed to access site")
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        page_title = soup.title.string.strip() if soup.title else "No title"
        print(f"Page Title: {page_title}")
        
        # Look for links that might be tenders/opportunities
        all_links = soup.find_all('a', href=True)
        
        # Keywords that might indicate tender/opportunity links
        tender_keywords = [
            'solicitation', 'tender', 'rfp', 'opportunity', 'procurement', 
            'proposal', 'bid', 'contract', 'award', 'funding', 'grant',
            'competition', 'call', 'expression'
        ]
        
        potential_links = []
        for link in all_links:
            link_text = link.get_text().strip().lower()
            link_href = link.get('href', '').lower()
            
            # Check if link text or href contains tender keywords
            if any(keyword in link_text or keyword in link_href for keyword in tender_keywords):
                potential_links.append({
                    'text': link.get_text().strip()[:100],
                    'href': link.get('href'),
                    'classes': link.get('class', []),
                    'parent_classes': link.parent.get('class', []) if link.parent else []
                })
        
        print(f"Found {len(potential_links)} potential tender links")
        
        # Show sample links
        for i, link in enumerate(potential_links[:5]):
            print(f"  Link {i+1}: {link['text']}")
            print(f"    Href: {link['href']}")
            print(f"    Classes: {link['classes']}")
            print(f"    Parent Classes: {link['parent_classes']}")
            print()
        
        # Look for common container patterns
        container_selectors = [
            '.solicitation', '.solicitation-item', '.solicitations',
            '.opportunity', '.opportunity-item', '.opportunities',
            '.tender', '.tender-item', '.tenders',
            '.procurement', '.procurement-item', '.procurements',
            '.proposal', '.proposal-item', '.proposals',
            '.funding', '.funding-item', '.fundings',
            '.card', '.item', '.listing', '.entry',
            '[class*="solicitation"]', '[class*="opportunity"]', '[class*="tender"]'
        ]
        
        print("Checking container patterns:")
        found_containers = []
        for selector in container_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    print(f"  ✓ {selector}: {len(elements)} elements")
                    found_containers.append(selector)
            except:
                pass
        
        # Look for pagination or "more" links
        pagination_keywords = ['next', 'more', 'page', 'continue', 'load more']
        pagination_links = []
        for link in all_links:
            link_text = link.get_text().strip().lower()
            if any(keyword in link_text for keyword in pagination_keywords):
                pagination_links.append(link.get_text().strip())
        
        if pagination_links:
            print(f"Pagination/More links found: {pagination_links[:3]}")
        
        return {
            'status': 'success',
            'potential_links': len(potential_links),
            'found_containers': found_containers,
            'sample_links': potential_links[:3]
        }
        
    except Exception as e:
        print(f"❌ Error inspecting site: {e}")
        return None

def main():
    """Main inspection function"""
    from config import Config
    
    results = {}
    
    # Sites to inspect (excluding login-required ones for now)
    sites_to_check = ['abt_global', 'spc', 'tetratech', 'transparency_intl', 'dt_global']
    
    for site_key in sites_to_check:
        if site_key in Config.SITES_CONFIG:
            site_config = Config.SITES_CONFIG[site_key]
            if not site_config.get('requires_login', False):
                result = inspect_site(site_config, site_key)
                results[site_key] = result
                time.sleep(2)  # Be respectful
    
    # Summary
    print(f"\n{'='*60}")
    print("INSPECTION SUMMARY")
    print(f"{'='*60}")
    
    for site_key, result in results.items():
        if result:
            site_name = Config.SITES_CONFIG[site_key]['name']
            print(f"{site_name}: {result['potential_links']} potential links found")
            if result['found_containers']:
                print(f"  Suggested selectors: {', '.join(result['found_containers'][:3])}")
        else:
            print(f"{site_key}: Failed to inspect")

if __name__ == "__main__":
    main()
