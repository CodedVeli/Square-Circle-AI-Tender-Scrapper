# Square Circle AI Tender Curation System

A proof-of-concept AI system for automated tender discovery, evaluation, and proposal assistance.

## Features

- **Automated Tender Scraping**: Scrapes both public and login-required tender sites
- **AI Document Analysis**: Extracts and analyzes tender documents (PDFs/Word)
- **Smart Evaluation**: Scores tenders based on configurable criteria
- **Dashboard Interface**: Web-based interface for managing and reviewing tenders
- **Data Export**: Export shortlisted tenders to Excel/CSV

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
copy .env.example .env
# Edit .env with your credentials and API keys
```

3. Run the system:
```bash
# Start the dashboard
streamlit run dashboard.py

# Run manual scraping
python scraper_manager.py

# Schedule daily scraping
python scheduler.py
```

## Priority Sites Supported

### Login Required:
- Devex.org (funding opportunities)
- Tenders.gov.au

### Public Sites:
- Abt Global
- SPC (Pacific Community)
- Tetra Tech International Development
- Transparency International
- DT Global

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Scrapers  │───▶│   AI Analysis   │───▶│   Evaluation    │
│                 │    │                 │    │                 │
│ • Public sites  │    │ • Document      │    │ • Scoring       │
│ • Login sites   │    │   extraction    │    │ • Ranking       │
│ • File download │    │ • Content       │    │ • Filtering     │
└─────────────────┘    │   analysis      │    └─────────────────┘
                       └─────────────────┘             │
┌─────────────────┐                                   │
│    Database     │◀──────────────────────────────────┘
│                 │
│ • Tender data   │    ┌─────────────────┐
│ • Scores        │───▶│   Dashboard     │
│ • Documents     │    │                 │
└─────────────────┘    │ • Web interface │
                       │ • Export tools  │
                       │ • Management    │
                       └─────────────────┘
```

## Configuration

Edit `config.py` to customize:
- Evaluation criteria and weights
- Priority sectors
- Geographic preferences
- Budget ranges
- AI model settings

## Security

- Credentials stored securely using encryption
- Environment variables for sensitive data
- Secure session management for login sites
