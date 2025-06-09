"""
Test Document Processing Functionality
Tests PDF and document analysis capabilities
"""
import sys
import os
sys.path.append('c:\\Users\\user\\Projects\\Scraping')

from document_processor import DocumentProcessor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_document_processing():
    """Test document processing capabilities"""
    processor = DocumentProcessor()
    
    print("=== TESTING DOCUMENT PROCESSOR ===")
    
    # Test URLs from earlier scraping
    test_urls = [
        "https://www.tetratechintdev.com/pdfs/AIFFP_AM-AIFFP-2024-001_RTF_FINAL.pdf",
        "https://www.tetratechintdev.com/pdfs/SC_Public_Consultation_Strategy_and_Plan.pdf"
    ]
    
    results = []
    
    for i, url in enumerate(test_urls[:2]):  # Test first 2 only
        print(f"\n--- Testing Document {i+1}: {url} ---")
        
        try:
            # Test download only first
            print(f"Attempting to download: {url}")
            filepath = processor.download_document(url)
            
            if filepath:
                print(f"✅ Downloaded to: {filepath}")
                
                # Check file size
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    print(f"File size: {size:,} bytes")
                    
                    # Try to extract text
                    text = processor.extract_text_from_document(filepath)
                    
                    if text:
                        print(f"✅ Extracted {len(text)} characters of text")
                        print(f"Text preview: {text[:200]}...")
                        
                        # Test basic analysis
                        analysis = processor.analyze_document_content(text, url)
                        
                        if analysis:
                            print(f"✅ Analysis completed")
                            print(f"Analysis keys: {list(analysis.keys())}")
                            
                            # Show some results
                            if 'key_requirements' in analysis:
                                reqs = analysis['key_requirements']
                                print(f"Found {len(reqs)} requirements")
                                
                            if 'location_mentions' in analysis:
                                locs = analysis['location_mentions']
                                print(f"Found {len(locs)} location mentions")
                        
                        results.append({
                            'url': url,
                            'success': True,
                            'text_length': len(text),
                            'analysis': analysis
                        })
                    else:
                        print("❌ No text extracted")
                        results.append({
                            'url': url,
                            'success': False,
                            'error': 'No text extracted'
                        })
                else:
                    print("❌ File not found after download")
                    results.append({
                        'url': url,
                        'success': False,
                        'error': 'File not found'
                    })
            else:
                print("❌ Download failed")
                results.append({
                    'url': url,
                    'success': False,
                    'error': 'Download failed'
                })
                
        except Exception as e:
            print(f"❌ Error processing {url}: {str(e)}")
            results.append({
                'url': url,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n=== SUMMARY ===")
    successful = sum(1 for r in results if r['success'])
    print(f"Successfully processed: {successful}/{len(results)} documents")
    
    for result in results:
        if result['success']:
            print(f"✅ {result['url']}: {result['text_length']} chars")
        else:
            print(f"❌ {result['url']}: {result['error']}")
    
    return results

if __name__ == "__main__":
    try:
        results = test_document_processing()
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
