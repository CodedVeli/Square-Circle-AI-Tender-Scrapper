#!/usr/bin/env python3
"""
Show top-scoring tenders and evaluation summary
"""
from models import SessionLocal, Tender
from datetime import datetime

def main():
    db = SessionLocal()
    try:
        # Get all evaluated tenders
        tenders = db.query(Tender).filter(Tender.evaluation_score.isnot(None))\
                   .order_by(Tender.evaluation_score.desc()).all()
        
        print(f'=== TENDER EVALUATION RESULTS ===')
        print(f'Total evaluated tenders: {len(tenders)}')
        print()
        
        # Score distribution
        high_priority = [t for t in tenders if t.evaluation_score >= 4.0]
        medium_priority = [t for t in tenders if 3.0 <= t.evaluation_score < 4.0]
        low_priority = [t for t in tenders if 2.0 <= t.evaluation_score < 3.0]
        very_low_priority = [t for t in tenders if t.evaluation_score < 2.0]
        
        print('Score Distribution:')
        print(f'  🟢 High Priority (4.0+): {len(high_priority)} tenders')
        print(f'  🟡 Medium Priority (3.0-3.9): {len(medium_priority)} tenders')
        print(f'  🟠 Low Priority (2.0-2.9): {len(low_priority)} tenders')
        print(f'  🔴 Very Low Priority (<2.0): {len(very_low_priority)} tenders')
        print()
        
        # Show top 10 scoring tenders
        print('🏆 TOP 10 SCORING TENDERS:')
        print('-' * 80)
        for i, tender in enumerate(tenders[:10], 1):
            source = tender.source_site[:20] + "..." if len(tender.source_site) > 20 else tender.source_site
            title = tender.title[:50] + "..." if len(tender.title) > 50 else tender.title
            
            # Priority indicator
            if tender.evaluation_score >= 4.0:
                priority = "🟢 HIGH"
            elif tender.evaluation_score >= 3.0:
                priority = "🟡 MED"
            elif tender.evaluation_score >= 2.0:
                priority = "🟠 LOW"
            else:
                priority = "🔴 V.LOW"
            
            print(f'{i:2d}. {title:<52} | {tender.evaluation_score:.2f}/5.0 | {priority} | {source}')
        
        print()
        
        # Show breakdown by source with average scores
        print('📊 PERFORMANCE BY SOURCE:')
        print('-' * 80)
        sources = {}
        for tender in tenders:
            source = tender.source_site
            if source not in sources:
                sources[source] = []
            sources[source].append(tender.evaluation_score)
        
        for source, scores in sources.items():
            avg_score = sum(scores) / len(scores)
            count = len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            print(f'{source:<30} | Avg: {avg_score:.2f} | Count: {count:2d} | Range: {min_score:.2f}-{max_score:.2f}')
        
        print()
        
        # Show recommended tenders (score >= 3.0)
        recommended = [t for t in tenders if t.evaluation_score >= 3.0]
        if recommended:
            print(f'✅ RECOMMENDED TENDERS (Score ≥ 3.0): {len(recommended)} tenders')
            print('-' * 80)
            for tender in recommended:
                deadline = tender.deadline.strftime('%Y-%m-%d') if tender.deadline else 'No deadline'
                location = tender.location[:20] + "..." if tender.location and len(tender.location) > 20 else (tender.location or 'Not specified')
                print(f'• {tender.title[:60]:<60} | {tender.evaluation_score:.2f} | {deadline} | {location}')
        else:
            print('❌ No tenders meet the recommended threshold (≥ 3.0)')
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
