#!/usr/bin/env python3
"""
Final Export Test - AI Tender Curation System
"""
import sqlite3
import csv
import json
import os
from datetime import datetime

def test_basic_export():
    """Test basic export functionality without complex dependencies"""
    print("🧪 FINAL EXPORT FUNCTIONALITY TEST")
    print("=" * 50)
    
    # Create exports directory
    export_dir = "c:\\Users\\user\\Projects\\Scraping\\exports"
    os.makedirs(export_dir, exist_ok=True)
    
    try:
        # Connect to database
        conn = sqlite3.connect("c:\\Users\\user\\Projects\\Scraping\\tenders.db")
        cursor = conn.cursor()
          # Get all tenders with evaluation data
        cursor.execute("""
            SELECT 
                title, 
                description,
                url,
                deadline,
                evaluation_score,
                sector_score,
                location_score,
                budget_score,
                deadline_score,
                experience_score,
                ai_extracted_sectors,
                ai_extracted_keywords,
                ai_summary,
                scraped_at
            FROM tenders 
            WHERE evaluation_score IS NOT NULL
            ORDER BY evaluation_score DESC        """)
        
        tenders = cursor.fetchall()
        headers = [
            "Title", "Description", "URL", "Deadline", "Overall Score",
            "Sector Score", "Location Score", "Budget Score", "Deadline Score", 
            "Experience Score", "AI Sectors", "AI Keywords", "AI Summary", "Scraped At"
        ]
        
        print(f"📊 Found {len(tenders)} evaluated tenders")
        
        # Test 1: CSV Export
        print("\n1. Testing CSV Export...")
        csv_filename = f"tenders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_filepath = os.path.join(export_dir, csv_filename)
        
        with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(tenders)
        
        csv_size = os.path.getsize(csv_filepath)
        print(f"   ✅ CSV export successful: {csv_filename} ({csv_size:,} bytes)")
        
        # Test 2: JSON Export
        print("\n2. Testing JSON Export...")
        json_filename = f"tenders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_filepath = os.path.join(export_dir, json_filename)
        
        tender_list = []
        for tender in tenders:
            tender_dict = dict(zip(headers, tender))
            tender_list.append(tender_dict)
        
        with open(json_filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump({
                "export_date": datetime.now().isoformat(),
                "total_tenders": len(tender_list),
                "tenders": tender_list
            }, jsonfile, indent=2, default=str)
        
        json_size = os.path.getsize(json_filepath)
        print(f"   ✅ JSON export successful: {json_filename} ({json_size:,} bytes)")
        
        # Test 3: Filtered Export (High Priority)
        print("\n3. Testing Filtered Export (Score ≥ 3.0)...")
        high_priority = [t for t in tenders if t[4] and t[4] >= 3.0]  # evaluation_score index
        
        if high_priority:
            filtered_filename = f"high_priority_tenders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filtered_filepath = os.path.join(export_dir, filtered_filename)
            
            with open(filtered_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(high_priority)
            
            filtered_size = os.path.getsize(filtered_filepath)
            print(f"   ✅ Filtered export successful: {filtered_filename} ({filtered_size:,} bytes)")
            print(f"   📊 {len(high_priority)} high-priority tenders exported")
        else:
            print("   ℹ️ No high-priority tenders found")
        
        # Test 4: Summary Report
        print("\n4. Generating Summary Report...")
        summary_filename = f"tender_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_filepath = os.path.join(export_dir, summary_filename)
        
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            f.write("AI TENDER CURATION SYSTEM - SUMMARY REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"OVERVIEW:\n")
            f.write(f"Total Tenders: {len(tenders)}\n")
            f.write(f"Average Score: {sum(t[4] for t in tenders if t[4])/len(tenders):.2f}/5.0\n")
            f.write(f"High Priority (≥3.0): {len(high_priority)}\n\n")
            
            f.write("TOP 5 TENDERS:\n")
            for i, tender in enumerate(tenders[:5], 1):
                f.write(f"{i}. {tender[0]} (Score: {tender[4]:.2f})\n")
            
        summary_size = os.path.getsize(summary_filepath)
        print(f"   ✅ Summary report created: {summary_filename} ({summary_size:,} bytes)")
        
        # Show export directory contents
        print(f"\n📁 EXPORT DIRECTORY CONTENTS:")
        for filename in os.listdir(export_dir):
            filepath = os.path.join(export_dir, filename)
            size = os.path.getsize(filepath)
            print(f"   • {filename} ({size:,} bytes)")
        
        conn.close()
        
        print(f"\n🎉 ALL EXPORT TESTS COMPLETED SUCCESSFULLY!")
        print(f"Files saved to: {export_dir}")
        
    except Exception as e:
        print(f"❌ Export test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_export()
