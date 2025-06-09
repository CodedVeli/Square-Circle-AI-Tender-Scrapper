"""
Tender Evaluation System for Square Circle
Scores and ranks tenders based on configurable criteria
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from models import Tender, TenderDocument, CompanyProfile, SessionLocal
from config import Config
from ai_analyzer import DocumentAnalyzer
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TenderEvaluator:
    """Evaluates and scores tenders based on Square Circle's criteria"""
    
    def __init__(self):
        """Initialize the tender evaluator"""
        self.db = SessionLocal()
        self.ai_analyzer = DocumentAnalyzer()
        self.config = Config.evaluation
    
    def evaluate_tender(self, tender: Tender) -> Dict:
        """
        Evaluate a single tender and return detailed scoring
        """
        try:
            logger.info(f"Evaluating tender: {tender.title}")
            
            # Initialize scores
            scores = {
                'sector_score': 0.0,
                'location_score': 0.0,
                'budget_score': 0.0,
                'deadline_score': 0.0,
                'experience_score': 0.0,
                'ai_score': 0.0,
                'overall_score': 0.0
            }
            
            # Calculate individual scores
            scores['sector_score'] = self.calculate_sector_score(tender)
            scores['location_score'] = self.calculate_location_score(tender)
            scores['budget_score'] = self.calculate_budget_score(tender)
            scores['deadline_score'] = self.calculate_deadline_score(tender)
            scores['experience_score'] = self.calculate_experience_score(tender)
            scores['ai_score'] = self.calculate_ai_score(tender)
            
            # Calculate weighted overall score
            weights = {
                'sector_score': 0.25,
                'location_score': 0.20,
                'budget_score': 0.15,
                'deadline_score': 0.15,
                'experience_score': 0.15,
                'ai_score': 0.10
            }
            
            overall_score = sum(scores[key] * weights[key] for key in weights.keys())
            scores['overall_score'] = round(overall_score, 2)
            
            # Update tender with scores
            tender.sector_score = scores['sector_score']
            tender.location_score = scores['location_score']
            tender.budget_score = scores['budget_score']
            tender.deadline_score = scores['deadline_score']
            tender.experience_score = scores['experience_score']
            tender.evaluation_score = scores['overall_score']
            
            self.db.commit()
            
            # Generate recommendation
            recommendation = self.generate_recommendation(scores, tender)
            
            return {
                'tender_id': tender.id,
                'scores': scores,
                'recommendation': recommendation,
                'evaluation_date': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating tender {tender.id}: {str(e)}")
            self.db.rollback()
            return {
                'tender_id': tender.id,
                'error': str(e),
                'scores': scores
            }
    
    def calculate_sector_score(self, tender: Tender) -> float:
        """Calculate score based on sector relevance"""
        try:
            sectors_to_check = []
            
            # Add sectors from tender data
            if tender.sector:
                sectors_to_check.extend(tender.sector.lower().split(', '))
            
            # Add sectors from AI analysis
            if tender.ai_extracted_sectors:
                try:
                    ai_sectors = json.loads(tender.ai_extracted_sectors)
                    sectors_to_check.extend([s.lower() for s in ai_sectors])
                except json.JSONDecodeError:
                    pass
            
            # Check title and description for sector keywords
            text_to_analyze = f"{tender.title or ''} {tender.description or ''}".lower()
            for priority_sector in self.config.priority_sectors.keys():
                if priority_sector in text_to_analyze:
                    sectors_to_check.append(priority_sector)
            
            if not sectors_to_check:
                return 2.0  # Neutral score if no sectors identified
            
            # Find highest matching sector score
            max_score = 0.0
            for sector in sectors_to_check:
                for priority_sector, weight in self.config.priority_sectors.items():
                    if priority_sector in sector or sector in priority_sector:
                        max_score = max(max_score, weight)
            
            return min(max_score, 5.0) if max_score > 0 else 2.0
            
        except Exception as e:
            logger.error(f"Error calculating sector score: {str(e)}")
            return 2.0
    
    def calculate_location_score(self, tender: Tender) -> float:
        """Calculate score based on geographic location"""
        try:
            location_text = (tender.location or '').lower()
            
            if not location_text:
                return 2.5  # Neutral score if no location specified
            
            # Check against geographic preferences
            for region, weight in self.config.geographic_preferences.items():
                if region in location_text:
                    return min(weight, 5.0)
            
            # Check for specific countries/regions in description
            description_text = (tender.description or '').lower()
            combined_text = f"{location_text} {description_text}"
            
            for region, weight in self.config.geographic_preferences.items():
                if region in combined_text:
                    return min(weight * 0.8, 5.0)  # Slightly lower if only in description
            
            return 2.0  # Lower score for non-preferred locations
            
        except Exception as e:
            logger.error(f"Error calculating location score: {str(e)}")
            return 2.0
    
    def calculate_budget_score(self, tender: Tender) -> float:
        """Calculate score based on budget range suitability"""
        try:
            budget_max = tender.budget_max
            budget_min = tender.budget_min or 0
            
            if not budget_max:
                return 2.5  # Neutral score if budget not specified
            
            # Determine budget range
            if budget_max < 50000:
                budget_range = "under_50000"
            elif budget_max <= 200000:
                budget_range = "50000-200000"
            elif budget_max <= 500000:
                budget_range = "200000-500000"
            elif budget_max <= 1000000:
                budget_range = "500000-1000000"
            else:
                budget_range = "1000000+"
            
            score = self.config.budget_ranges.get(budget_range, 2.0)
            
            # Bonus for well-defined budget ranges
            if budget_min > 0 and budget_max > budget_min:
                score *= 1.1
            
            return min(score, 5.0)
            
        except Exception as e:
            logger.error(f"Error calculating budget score: {str(e)}")
            return 2.0
    
    def calculate_deadline_score(self, tender: Tender) -> float:
        """Calculate score based on deadline feasibility"""
        try:
            if not tender.deadline:
                return 2.5  # Neutral score if no deadline specified
            
            days_until_deadline = (tender.deadline - datetime.utcnow()).days
            
            if days_until_deadline < 0:
                return 0.0  # Deadline passed
            elif days_until_deadline < 7:
                return 1.0  # Very tight deadline
            elif days_until_deadline < 14:
                return 2.0  # Tight deadline
            elif days_until_deadline < 30:
                return 3.5  # Reasonable deadline
            elif days_until_deadline < 60:
                return 4.5  # Good deadline
            else:
                return 5.0  # Excellent deadline
            
        except Exception as e:
            logger.error(f"Error calculating deadline score: {str(e)}")
            return 2.0
    
    def calculate_experience_score(self, tender: Tender) -> float:
        """Calculate score based on Square Circle's relevant experience"""
        try:
            # Get sectors and location from tender
            sectors = []
            if tender.sector:
                sectors.extend(tender.sector.lower().split(', '))
            if tender.ai_extracted_sectors:
                try:
                    ai_sectors = json.loads(tender.ai_extracted_sectors)
                    sectors.extend([s.lower() for s in ai_sectors])
                except json.JSONDecodeError:
                    pass
            
            location = (tender.location or '').lower()
            
            # Query company experience
            experience_profiles = self.db.query(CompanyProfile).all()
            
            if not experience_profiles:
                # Default experience scoring based on tender content
                return self.default_experience_scoring(tender)
            
            max_experience_score = 0.0
            
            for profile in experience_profiles:
                score = 0.0
                
                # Sector match
                if profile.sector.lower() in sectors:
                    score += profile.experience_level * 0.6
                
                # Location match
                if profile.country and profile.country.lower() in location:
                    score += profile.experience_level * 0.3
                elif profile.region and profile.region.lower() in location:
                    score += profile.experience_level * 0.2
                
                # Success rate bonus
                if profile.success_rate > 0.7:
                    score *= 1.2
                
                max_experience_score = max(max_experience_score, score)
            
            return min(max_experience_score, 5.0)
            
        except Exception as e:
            logger.error(f"Error calculating experience score: {str(e)}")
            return 2.0
    
    def default_experience_scoring(self, tender: Tender) -> float:
        """Default experience scoring when no company profiles exist"""
        score = 3.0  # Base score
        
        # Sector-based adjustments
        content = f"{tender.title or ''} {tender.description or ''}".lower()
        
        # Higher score for consulting/advisory work
        consulting_keywords = ['consulting', 'advisory', 'technical assistance', 'capacity building']
        for keyword in consulting_keywords:
            if keyword in content:
                score += 0.3
        
        # Lower score for implementation/construction
        implementation_keywords = ['construction', 'implementation', 'installation', 'manufacturing']
        for keyword in implementation_keywords:
            if keyword in content:
                score -= 0.5
        
        return max(1.0, min(score, 5.0))
    
    def calculate_ai_score(self, tender: Tender) -> float:
        """Calculate score based on AI document analysis"""
        try:
            # Check if tender has documents for AI analysis
            documents = self.db.query(TenderDocument).filter_by(tender_id=tender.id).all()
            
            if not documents:
                return 3.0  # Neutral score if no documents
            
            total_score = 0.0
            analyzed_docs = 0
            
            for doc in documents:
                if not doc.ai_analyzed and doc.local_path:
                    # Perform AI analysis
                    self.analyze_document(doc, tender)
                
                if doc.ai_analyzed:
                    # Extract fit score from AI analysis
                    try:
                        if hasattr(doc, 'ai_fit_score'):
                            total_score += doc.ai_fit_score
                            analyzed_docs += 1
                    except:
                        pass
            
            if analyzed_docs > 0:
                return total_score / analyzed_docs
            else:
                return 3.0
            
        except Exception as e:
            logger.error(f"Error calculating AI score: {str(e)}")
            return 3.0
    
    def analyze_document(self, document: TenderDocument, tender: Tender):
        """Analyze a document using AI and update the document record"""
        try:
            if not document.local_path or not os.path.exists(document.local_path):
                return
            
            # Perform AI analysis
            analysis_result = self.ai_analyzer.analyze_document_file(
                document.local_path, 
                tender.title or ''
            )
            
            if 'error' not in analysis_result:
                # Update document with analysis results
                document.extracted_text = analysis_result.get('extracted_text', '')
                document.ai_summary = json.dumps(analysis_result.get('analysis', {}))
                
                # Get fit evaluation
                fit_evaluation = self.ai_analyzer.evaluate_tender_fit(analysis_result)
                document.ai_fit_score = fit_evaluation.get('overall_fit_score', 3.0)
                
                document.ai_analyzed = True
                self.db.commit()
                
                logger.info(f"AI analysis completed for document: {document.filename}")
            
        except Exception as e:
            logger.error(f"Error analyzing document {document.filename}: {str(e)}")
    
    def generate_recommendation(self, scores: Dict, tender: Tender) -> Dict:
        """Generate recommendation based on scores"""
        overall_score = scores['overall_score']
        
        if overall_score >= 4.0:
            priority = "High"
            action = "Highly recommended for immediate consideration"
            color = "green"
        elif overall_score >= 3.0:
            priority = "Medium"
            action = "Recommended for review and consideration"
            color = "orange"
        elif overall_score >= 2.0:
            priority = "Low"
            action = "Consider if resources available"
            color = "yellow"
        else:
            priority = "Very Low"
            action = "Not recommended unless specific interest"
            color = "red"
        
        # Identify key strengths and concerns
        strengths = []
        concerns = []
        
        for score_type, score in scores.items():
            if score_type == 'overall_score':
                continue
                
            score_name = score_type.replace('_score', '').replace('_', ' ').title()
            
            if score >= 4.0:
                strengths.append(f"Strong {score_name} fit ({score:.1f}/5.0)")
            elif score <= 2.0:
                concerns.append(f"Weak {score_name} fit ({score:.1f}/5.0)")
        
        return {
            'priority': priority,
            'action_recommendation': action,
            'color_code': color,
            'overall_score': overall_score,
            'strengths': strengths,
            'concerns': concerns,
            'deadline_days': (tender.deadline - datetime.utcnow()).days if tender.deadline else None
        }
    
    def evaluate_all_tenders(self, limit: Optional[int] = None) -> List[Dict]:
        """Evaluate all tenders in the database"""
        try:
            query = self.db.query(Tender)
            if limit:
                query = query.limit(limit)
            
            tenders = query.all()
            results = []
            
            for tender in tenders:
                result = self.evaluate_tender(tender)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating all tenders: {str(e)}")
            return []
    
    def get_shortlisted_tenders(self, min_score: float = 3.0) -> List[Tender]:
        """Get tenders that meet the minimum score threshold"""
        try:
            return self.db.query(Tender)\
                .filter(Tender.evaluation_score >= min_score)\
                .order_by(Tender.evaluation_score.desc())\
                .all()
        except Exception as e:
            logger.error(f"Error getting shortlisted tenders: {str(e)}")
            return []
    
    def update_company_profile(self, sector: str, country: str = None, 
                             experience_level: float = 3.0, success_rate: float = 0.8):
        """Add or update company experience profile"""
        try:
            existing_profile = self.db.query(CompanyProfile)\
                .filter_by(sector=sector, country=country)\
                .first()
            
            if existing_profile:
                existing_profile.experience_level = experience_level
                existing_profile.success_rate = success_rate
                existing_profile.similar_projects += 1
            else:
                new_profile = CompanyProfile(
                    sector=sector,
                    country=country,
                    experience_level=experience_level,
                    success_rate=success_rate,
                    similar_projects=1
                )
                self.db.add(new_profile)
            
            self.db.commit()
            logger.info(f"Updated company profile for {sector} in {country or 'global'}")
            
        except Exception as e:
            logger.error(f"Error updating company profile: {str(e)}")
            self.db.rollback()
    
    def close(self):
        """Close database connection"""
        self.db.close()

# Example usage and testing
if __name__ == "__main__":
    evaluator = TenderEvaluator()
    
    # Add some sample company profiles
    evaluator.update_company_profile("climate change", "fiji", 4.2, 0.85)
    evaluator.update_company_profile("governance", "vanuatu", 3.8, 0.75)
    evaluator.update_company_profile("infrastructure", "pacific", 3.5, 0.80)
    
    # Evaluate all tenders
    results = evaluator.evaluate_all_tenders(limit=5)
    
    print("Tender Evaluation Results:")
    print("=" * 50)
    
    for result in results:
        if 'error' not in result:
            print(f"Tender ID: {result['tender_id']}")
            print(f"Overall Score: {result['scores']['overall_score']}/5.0")
            print(f"Priority: {result['recommendation']['priority']}")
            print(f"Action: {result['recommendation']['action_recommendation']}")
            
            if result['recommendation']['strengths']:
                print(f"Strengths: {', '.join(result['recommendation']['strengths'])}")
            
            if result['recommendation']['concerns']:
                print(f"Concerns: {', '.join(result['recommendation']['concerns'])}")
            
            print("-" * 30)
    
    evaluator.close()
