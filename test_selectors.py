#!/usr/bin/env python3
"""
Simple script to test CSS selectors for each target site
"""
import requests
from bs4 import BeautifulSoup
from config import Config

def test_site_selectors(site_key, site_config):
    print(f"\n{'='*60}")
    print(f"Testing: {site_config['name']}")
    print(f"URL: {site_config['search_url']}")
    print(f"Current selector: {site_config['selectors']['tender_links']}")
    print(f"{'='*60}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(site_config['search_url'], headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Failed to access site - Status: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        page_title = soup.title.string.strip() if soup.title else "No title"
        print(f"Page Title: {page_title}")
          # Test current selector
        current_links = soup.select(site_config['selectors']['tender_links'])
        print(f"\nCurrent selector found: {len(current_links)} links")
        
        if len(current_links) == 0:
            print("❌ Current selector returns 0 results")
            
            # Look for alternative selectors
            print("\n🔍 Searching for potential tender links...")
            
            # Check for common link patterns
            all_links = soup.find_all('a', href=True)
            print(f"Total links on page: {len(all_links)}")
            
            # Keywords that might indicate tender/opportunity links
            tender_keywords = [
                'solicitation', 'tender', 'rfp', 'opportunity', 'procurement', 
                'proposal', 'bid', 'contract', 'award', 'funding', 'grant',
                'competition', 'call', 'expression', 'notice'
            ]
            
            potential_links = []
            for link in all_links:
                link_text = link.get_text().strip().lower()
                link_href = link.get('href', '').lower()
                
                # Check if link text or href contains tender keywords
                if any(keyword in link_text or keyword in link_href for keyword in tender_keywords):
                    potential_links.append({
                        'text': link.get_text().strip()[:80],
                        'href': link.get('href'),
                        'classes': ' '.join(link.get('class', [])),
                        'parent_tag': link.parent.name if link.parent else 'none',
                        'parent_classes': ' '.join(link.parent.get('class', [])) if link.parent and link.parent.get('class') else ''
                    })
            
            print(f"Found {len(potential_links)} potential tender links")
            
            # Show first 3 examples
            for i, link in enumerate(potential_links[:3]):
                print(f"\n  Example {i+1}:")
                print(f"    Text: {link['text']}")
                print(f"    Href: {link['href']}")
                print(f"    Classes: {link['classes']}")
                print(f"    Parent: {link['parent_tag']}.{link['parent_classes']}")
            
            # Suggest new selectors based on common patterns
            if potential_links:
                print(f"\n💡 Suggested selectors to try:")
                unique_classes = set()
                for link in potential_links:
                    if link['classes']:
                        unique_classes.add(f"a.{link['classes'].split()[0]}")
                    if link['parent_classes']:
                        unique_classes.add(f".{link['parent_classes'].split()[0]} a")
                
                for selector in list(unique_classes)[:3]:
                    print(f"    {selector}")
                    
        else:
            print(f"✅ Current selector works - found {len(current_links)} links")
            for i, link in enumerate(current_links[:3]):
                print(f"  {i+1}. {link.get_text().strip()[:80]}")
                
    except Exception as e:
        print(f"❌ Error accessing site: {e}")

def main():
    print("Testing CSS selectors for all target sites...")
    
    config = Config()
    
    for site_key, site_config in config.SITES_CONFIG.items():
        test_site_selectors(site_key, site_config)
    
    print(f"\n{'='*60}")
    print("Testing complete!")

if __name__ == "__main__":
    main()
