"""
Database models for the Square Circle Tender Curation System
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import Config

Base = declarative_base()

class Tender(Base):
    __tablename__ = 'tenders'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    source_site = Column(String(100), nullable=False)
    url = Column(String(1000), nullable=False)
    description = Column(Text)
    funder = Column(String(200))
    sector = Column(String(100))
    location = Column(String(200))
    budget_min = Column(Float)
    budget_max = Column(Float)
    budget_currency = Column(String(10), default='USD')
    deadline = Column(DateTime)
    project_duration = Column(String(100))
    scraped_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AI Analysis Results
    ai_analysis_complete = Column(Boolean, default=False)
    ai_extracted_sectors = Column(Text)  # JSON string of detected sectors
    ai_extracted_keywords = Column(Text)  # JSON string of keywords
    ai_summary = Column(Text)
    
    # Evaluation Results
    evaluation_score = Column(Float)
    sector_score = Column(Float)
    location_score = Column(Float)
    budget_score = Column(Float)
    deadline_score = Column(Float)
    experience_score = Column(Float)
    
    # Status
    is_shortlisted = Column(Boolean, default=False)
    status = Column(String(50), default='new')  # new, reviewed, applied, rejected
    notes = Column(Text)
    
    # Relationships
    documents = relationship("TenderDocument", back_populates="tender")
    
    def __repr__(self):
        return f"<Tender(id={self.id}, title='{self.title[:50]}...', source='{self.source_site}')>"

class TenderDocument(Base):
    __tablename__ = 'tender_documents'
    
    id = Column(Integer, primary_key=True)
    tender_id = Column(Integer, ForeignKey('tenders.id'), nullable=False)
    filename = Column(String(500), nullable=False)
    original_url = Column(String(1000))
    local_path = Column(String(1000))
    file_type = Column(String(10))  # pdf, docx, doc, etc.
    file_size = Column(Integer)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    # AI Analysis of Document
    ai_analyzed = Column(Boolean, default=False)
    extracted_text = Column(Text)
    ai_summary = Column(Text)
    key_requirements = Column(Text)  # JSON string
    
    # Relationship
    tender = relationship("Tender", back_populates="documents")
    
    def __repr__(self):
        return f"<TenderDocument(id={self.id}, filename='{self.filename}', tender_id={self.tender_id})>"

class ScrapingLog(Base):
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    site_name = Column(String(100), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50))  # success, failed, partial
    tenders_found = Column(Integer, default=0)
    tenders_new = Column(Integer, default=0)
    tenders_updated = Column(Integer, default=0)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<ScrapingLog(id={self.id}, site='{self.site_name}', status='{self.status}')>"

class CompanyProfile(Base):
    __tablename__ = 'company_profile'
    
    id = Column(Integer, primary_key=True)
    sector = Column(String(100), nullable=False)
    country = Column(String(100))
    region = Column(String(100))
    project_type = Column(String(200))
    experience_level = Column(Float, default=1.0)  # 1-5 scale
    similar_projects = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CompanyProfile(sector='{self.sector}', country='{self.country}', experience={self.experience_level})>"

# Database setup
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
