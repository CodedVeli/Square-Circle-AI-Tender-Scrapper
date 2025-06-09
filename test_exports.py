"""
Test Export Functionality - Direct CSV Export
Tests the export module without Streamlit interface
"""
import sys
import os
sys.path.append('c:\\Users\\user\\Projects\\Scraping')

from export_module import TenderExporter, get_all_tenders
import pandas as pd
from datetime import datetime

def test_export_functionality():
    """Test direct export functionality"""
    print("=== TESTING EXPORT FUNCTIONALITY ===")
    
    # Load tenders
    print("Loading tenders from database...")
    tenders = get_all_tenders()
    print(f"Found {len(tenders)} tenders in database")
    
    if not tenders:
        print("❌ No tenders found for export test")
        return
    
    # Initialize exporter
    exporter = TenderExporter()
    
    # Test CSV export
    print("\n--- Testing CSV Export ---")
    try:
        csv_data = exporter.export_to_csv(tenders)
        csv_content = csv_data.getvalue()
        
        # Save to file for verification
        filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join("c:\\Users\\user\\Projects\\Scraping\\exports", filename)
        
        # Create exports directory if it doesn't exist
        os.makedirs("c:\\Users\\user\\Projects\\Scraping\\exports", exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        print(f"✅ CSV export successful: {filepath}")
        print(f"File size: {len(csv_content):,} characters")
        
        # Show preview
        lines = csv_content.split('\\n')
        print(f"Preview (first 3 lines):")
        for i, line in enumerate(lines[:3]):
            print(f"  {i+1}: {line[:100]}...")
            
    except Exception as e:
        print(f"❌ CSV export failed: {str(e)}")
    
    # Test Excel export
    print("\n--- Testing Excel Export ---")
    try:
        excel_data = exporter.export_to_excel(tenders)
        excel_content = excel_data.getvalue()
        
        # Save to file for verification
        filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join("c:\\Users\\user\\Projects\\Scraping\\exports", filename)
        
        with open(filepath, 'wb') as f:
            f.write(excel_content)
        
        print(f"✅ Excel export successful: {filepath}")
        print(f"File size: {len(excel_content):,} bytes")
        
    except Exception as e:
        print(f"❌ Excel export failed: {str(e)}")
    
    # Test summary report
    print("\n--- Testing Summary Report ---")
    try:
        report = exporter.export_summary_report(tenders)
        
        print(f"✅ Summary report generated")
        print(f"Summary statistics:")
        for key, value in report["summary"].items():
            print(f"  {key}: {value}")
        
        print(f"Score distribution:")
        for priority, count in report["score_distribution"].items():
            print(f"  {priority}: {count}")
        
        print(f"Top 3 tenders:")
        for i, tender in enumerate(report["top_tenders"][:3], 1):
            print(f"  {i}. {tender['title'][:50]}... (Score: {tender['score']})")
        
    except Exception as e:
        print(f"❌ Summary report failed: {str(e)}")
    
    # Filter test - high priority only
    print("\n--- Testing Filtered Export (Medium+ Priority) ---")
    try:
        high_priority_tenders = [t for t in tenders if t.evaluation_score and t.evaluation_score >= 3.0]
        print(f"Found {len(high_priority_tenders)} medium+ priority tenders")
        
        if high_priority_tenders:
            csv_data = exporter.export_to_csv(high_priority_tenders)
            
            filename = f"high_priority_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join("c:\\Users\\user\\Projects\\Scraping\\exports", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_data.getvalue())
            
            print(f"✅ High priority export successful: {filepath}")
        else:
            print("ℹ️ No high priority tenders to export")
            
    except Exception as e:
        print(f"❌ Filtered export failed: {str(e)}")
    
    print("\n=== EXPORT TEST COMPLETED ===")

if __name__ == "__main__":
    test_export_functionality()
