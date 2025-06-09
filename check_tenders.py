#!/usr/bin/env python3
"""
Check tenders in database
"""
from models import SessionLocal, Tender

def main():
    db = SessionLocal()
    try:
        count = db.query(Tender).count()
        print(f'Total tenders in database: {count}')
        
        # Get breakdown by source
        sources = {}
        evaluated = 0
        unevaluated = 0
        
        tenders = db.query(Tender).all()
        for tender in tenders:
            source = tender.source_site
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
            
            if tender.evaluation_score is not None:
                evaluated += 1
            else:
                unevaluated += 1
        
        print('\nTenders by source:')
        for source, count in sources.items():
            print(f'  {source}: {count}')
        
        print(f'\nEvaluation status:')
        print(f'  Evaluated: {evaluated}')
        print(f'  Not evaluated: {unevaluated}')
        
        # Show some recent tenders
        print('\nRecent tenders:')
        recent_tenders = db.query(Tender).order_by(Tender.scraped_at.desc()).limit(5).all()
        for tender in recent_tenders:
            score = tender.evaluation_score if tender.evaluation_score else "Not evaluated"
            print(f"  - {tender.title[:60]}... (Score: {score}) from {tender.source_site}")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
