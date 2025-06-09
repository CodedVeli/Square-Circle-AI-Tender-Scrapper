#!/usr/bin/env python3
"""
Test document analysis functionality
"""
from ai_analyzer import DocumentAnalyzer
import os

def test_document_analysis():
    """Test the AI document analysis on a sample tender document"""
    print("=== TESTING AI DOCUMENT ANALYSIS ===")
    
    # Create analyzer
    analyzer = DocumentAnalyzer()
    
    # Test with sample tender content
    sample_content = """
    REQUEST FOR PROPOSALS
    
    Climate Resilience Planning for Pacific Island Nations
    
    The Australian Department of Foreign Affairs and Trade (DFAT) is seeking qualified 
    consulting firms to provide technical assistance for climate resilience planning 
    in Fiji, Vanuatu, and Solomon Islands.
    
    PROJECT BACKGROUND:
    This project aims to strengthen the capacity of Pacific Island governments to develop 
    and implement climate adaptation policies and plans. The work will focus on coastal 
    protection, water security, and agricultural resilience.
    
    SCOPE OF WORK:
    1. Conduct stakeholder consultations in each target country
    2. Review existing climate policies and institutional frameworks
    3. Develop climate vulnerability assessments
    4. Design adaptation strategies and action plans
    5. Provide capacity building training to government officials
    
    BUDGET: AUD 250,000 - 400,000
    DURATION: 18 months
    DEADLINE: Applications must be submitted by March 30, 2025
    
    ELIGIBILITY REQUIREMENTS:
    - Minimum 5 years experience in climate change adaptation
    - Demonstrated experience working in Pacific Island contexts
    - Team must include climate scientists and policy specialists
    - Small to medium-sized consulting firms are encouraged to apply
    
    EVALUATION CRITERIA:
    - Technical approach and methodology (40%)
    - Team qualifications and experience (30%)
    - Understanding of Pacific Island contexts (20%)
    - Value for money (10%)
    
    For more information, contact: climate.projects@dfat.gov.au
    """
    
    print("Analyzing sample tender document...")
    print("-" * 50)
    
    # Run AI analysis
    analysis_result = analyzer.analyze_tender_content(
        sample_content, 
        "Climate Resilience Planning for Pacific Island Nations"
    )
    
    print("AI ANALYSIS RESULTS:")
    print(f"Sectors: {analysis_result.get('sectors', [])}")
    print(f"Keywords: {analysis_result.get('keywords', [])}")
    print(f"Budget: {analysis_result.get('budget_info', 'N/A')}")
    print(f"Deadline: {analysis_result.get('deadline_info', 'N/A')}")
    print(f"Location: {analysis_result.get('location', 'N/A')}")
    print(f"Requirements: {analysis_result.get('key_requirements', [])}")
    print(f"Duration: {analysis_result.get('project_duration', 'N/A')}")
    print(f"Funder: {analysis_result.get('funder_organization', 'N/A')}")
    print(f"Difficulty: {analysis_result.get('difficulty_assessment', 'N/A')}/5")
    print()
    print("SUMMARY:")
    print(analysis_result.get('summary', 'No summary available'))
    print()
    
    # Test fit evaluation
    print("=== EVALUATING TENDER FIT ===")
    fit_result = analyzer.evaluate_tender_fit({'analysis': analysis_result})
    
    print(f"Overall Fit Score: {fit_result.get('overall_fit_score', 'N/A')}/5.0")
    print(f"Sector Fit: {fit_result.get('sector_fit_score', 'N/A')}/5.0")
    print(f"Location Fit: {fit_result.get('location_fit_score', 'N/A')}/5.0")
    print(f"Capability Fit: {fit_result.get('capability_fit_score', 'N/A')}/5.0")
    print(f"Complexity Fit: {fit_result.get('complexity_fit_score', 'N/A')}/5.0")
    print()
    print("RECOMMENDATION:")
    print(fit_result.get('recommendation', 'No recommendation available'))
    print()
    print("KEY FACTORS:")
    for factor in fit_result.get('key_factors', []):
        print(f"- {factor}")

if __name__ == "__main__":
    test_document_analysis()
