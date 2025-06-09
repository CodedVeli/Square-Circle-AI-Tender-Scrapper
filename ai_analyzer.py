"""
AI Document Analysis Module for Square Circle Tender System
Handles extraction and analysis of tender documents using OpenAI API
"""
import os
import json
import PyPDF2
import docx
import openai
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentAnalyzer:
    """AI-powered document analyzer for tender documents"""
    
    def __init__(self):
        """Initialize the document analyzer"""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in configuration")
        
        openai.api_key = Config.OPENAI_API_KEY
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {file_path}: {str(e)}")
            return ""
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from document based on file extension"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif extension in ['.docx', '.doc']:
            return self.extract_text_from_docx(str(file_path))
        else:
            logger.warning(f"Unsupported file type: {extension}")
            return ""
    
    def analyze_tender_content(self, content: str, title: str = "") -> Dict:
        """
        Analyze tender content using AI to extract key information
        """
        try:
            prompt = f"""
            Analyze the following tender document and extract key information:
            
            Title: {title}
            Content: {content[:8000]}  # Limit content to avoid token limits
            
            Please extract and provide the following information in JSON format:
            {{
                "sectors": ["list of relevant sectors/industries"],
                "keywords": ["key terms and phrases"],
                "budget_info": "extracted budget information",
                "deadline_info": "deadline or timeline information",
                "location": "geographic location or regions",
                "key_requirements": ["main requirements or qualifications"],
                "project_duration": "project timeline or duration",
                "funder_organization": "funding organization name",
                "summary": "brief 2-3 sentence summary",
                "difficulty_assessment": "assessment of complexity (1-5 scale)",
                "experience_required": ["types of experience needed"],
                "deliverables": ["main project deliverables"],
                "evaluation_criteria": ["how proposals will be evaluated"]
            }}
            
            Focus on information relevant to a small aid and development consulting company.
            """
            
            response = openai.ChatCompletion.create(
                model=Config.AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing tender documents for development consulting opportunities. Extract key information accurately and comprehensively."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=Config.MAX_TOKENS,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                analysis_result = json.loads(ai_response)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a structured response
                analysis_result = {
                    "sectors": [],
                    "keywords": [],
                    "budget_info": "Not specified",
                    "deadline_info": "Not specified",
                    "location": "Not specified",
                    "key_requirements": [],
                    "project_duration": "Not specified",
                    "funder_organization": "Not specified",
                    "summary": ai_response[:500],
                    "difficulty_assessment": "3",
                    "experience_required": [],
                    "deliverables": [],
                    "evaluation_criteria": []
                }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return {
                "sectors": [],
                "keywords": [],
                "budget_info": "Analysis failed",
                "deadline_info": "Analysis failed",
                "location": "Analysis failed",
                "key_requirements": [],
                "project_duration": "Analysis failed",
                "funder_organization": "Analysis failed",
                "summary": "AI analysis failed due to technical error",
                "difficulty_assessment": "3",
                "experience_required": [],
                "deliverables": [],
                "evaluation_criteria": [],
                "error": str(e)
            }
    
    def analyze_document_file(self, file_path: str, title: str = "") -> Dict:
        """
        Analyze a document file and return AI analysis results
        """
        logger.info(f"Analyzing document: {file_path}")
        
        # Extract text from document
        extracted_text = self.extract_text_from_file(file_path)
        
        if not extracted_text:
            return {
                "error": "Could not extract text from document",
                "extracted_text": "",
                "analysis": {}
            }
        
        # Perform AI analysis
        analysis = self.analyze_tender_content(extracted_text, title)
        
        return {
            "extracted_text": extracted_text,
            "analysis": analysis,
            "file_analyzed": file_path,
            "text_length": len(extracted_text)
        }
    
    def evaluate_tender_fit(self, analysis_result: Dict) -> Dict:
        """
        Evaluate how well a tender fits Square Circle's profile
        """
        try:
            sectors = analysis_result.get('analysis', {}).get('sectors', [])
            location = analysis_result.get('analysis', {}).get('location', '')
            requirements = analysis_result.get('analysis', {}).get('key_requirements', [])
            difficulty = analysis_result.get('analysis', {}).get('difficulty_assessment', '3')
            
            # Calculate fit scores
            sector_fit = self._calculate_sector_fit(sectors)
            location_fit = self._calculate_location_fit(location)
            capability_fit = self._calculate_capability_fit(requirements)
            complexity_fit = self._calculate_complexity_fit(difficulty)
            
            overall_fit = (sector_fit + location_fit + capability_fit + complexity_fit) / 4
            
            return {
                "overall_fit_score": round(overall_fit, 2),
                "sector_fit_score": round(sector_fit, 2),
                "location_fit_score": round(location_fit, 2),
                "capability_fit_score": round(capability_fit, 2),
                "complexity_fit_score": round(complexity_fit, 2),
                "recommendation": self._get_recommendation(overall_fit),
                "key_factors": self._get_key_factors(sectors, location, requirements)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating tender fit: {str(e)}")
            return {
                "overall_fit_score": 2.5,
                "error": str(e)
            }
    
    def _calculate_sector_fit(self, sectors: List[str]) -> float:
        """Calculate fit score based on sectors"""
        if not sectors:
            return 2.5
        
        priority_sectors = Config.evaluation.priority_sectors
        max_score = 0
        
        for sector in sectors:
            sector_lower = sector.lower()
            for priority_sector, weight in priority_sectors.items():
                if priority_sector in sector_lower or sector_lower in priority_sector:
                    max_score = max(max_score, weight)
        
        return min(max_score, 5.0) if max_score > 0 else 2.0
    
    def _calculate_location_fit(self, location: str) -> float:
        """Calculate fit score based on location"""
        if not location:
            return 2.5
        
        location_lower = location.lower()
        geo_preferences = Config.evaluation.geographic_preferences
        
        for region, weight in geo_preferences.items():
            if region in location_lower:
                return min(weight, 5.0)
        
        return 2.0
    
    def _calculate_capability_fit(self, requirements: List[str]) -> float:
        """Calculate fit based on capability requirements"""
        if not requirements:
            return 3.0
        
        # Keywords that indicate good fit for Square Circle
        good_fit_keywords = [
            'consulting', 'advisory', 'technical assistance', 'capacity building',
            'policy', 'governance', 'analysis', 'research', 'evaluation',
            'small', 'medium', 'local', 'regional'
        ]
        
        bad_fit_keywords = [
            'construction', 'large scale', 'manufacturing', 'infrastructure development',
            'multinational only', 'fortune 500', 'major contractor'
        ]
        
        score = 3.0
        req_text = ' '.join(requirements).lower()
        
        for keyword in good_fit_keywords:
            if keyword in req_text:
                score += 0.3
        
        for keyword in bad_fit_keywords:
            if keyword in req_text:
                score -= 0.5
        
        return max(1.0, min(score, 5.0))
    
    def _calculate_complexity_fit(self, difficulty: str) -> float:
        """Calculate fit based on complexity assessment"""
        try:
            difficulty_num = float(difficulty)
            # Square Circle likely fits best with moderate complexity (2-4 range)
            if 2 <= difficulty_num <= 4:
                return 4.0
            elif difficulty_num < 2:
                return 3.0  # Might be too simple
            else:
                return 2.0  # Might be too complex
        except:
            return 3.0
    
    def _get_recommendation(self, overall_fit: float) -> str:
        """Get recommendation based on overall fit score"""
        if overall_fit >= 4.0:
            return "Highly Recommended - Excellent fit for Square Circle"
        elif overall_fit >= 3.5:
            return "Recommended - Good fit with minor considerations"
        elif overall_fit >= 2.5:
            return "Consider - Moderate fit, review carefully"
        elif overall_fit >= 2.0:
            return "Low Priority - Limited fit"
        else:
            return "Not Recommended - Poor fit"
    
    def _get_key_factors(self, sectors: List[str], location: str, requirements: List[str]) -> List[str]:
        """Get key factors affecting the recommendation"""
        factors = []
        
        if sectors:
            factors.append(f"Sectors: {', '.join(sectors[:3])}")
        if location:
            factors.append(f"Location: {location}")
        if requirements:
            factors.append(f"Key requirements: {len(requirements)} identified")
        
        return factors

# Example usage and testing
if __name__ == "__main__":
    analyzer = DocumentAnalyzer()
    
    # Test with sample text
    sample_text = """
    The Pacific Climate Change Adaptation Project seeks a consulting firm to provide 
    technical assistance for climate resilience planning in Fiji and Vanuatu. 
    The project budget is USD 150,000 over 18 months. Deadline for submissions is March 15, 2025.
    
    Key requirements:
    - Experience in climate change adaptation
    - Knowledge of Pacific Island contexts
    - Policy development expertise
    - Stakeholder engagement experience
    """
    
    result = analyzer.analyze_tender_content(sample_text, "Pacific Climate Adaptation Project")
    print("AI Analysis Result:")
    print(json.dumps(result, indent=2))
    
    fit_evaluation = analyzer.evaluate_tender_fit({"analysis": result})
    print("\nFit Evaluation:")
    print(json.dumps(fit_evaluation, indent=2))
