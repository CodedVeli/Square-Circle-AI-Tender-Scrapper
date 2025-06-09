"""
Streamlit Dashboard for Square Circle Tender Curation System
Web interface for managing and reviewing tenders
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
from models import Tender, TenderDocument, ScrapingLog, CompanyProfile, SessionLocal, create_tables
from evaluator import TenderEvaluator
from scraper import ScrapingManager
from ai_analyzer import DocumentAnalyzer
from config import Config
from export_module import create_export_interface
import io
import base64

# Page config
st.set_page_config(
    page_title="Square Circle Tender Curation System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
create_tables()

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .high-priority {
        background-color: #d4edda;
        border-left-color: #28a745;
    }
    .medium-priority {
        background-color: #fff3cd;
        border-left-color: #ffc107;
    }
    .low-priority {
        background-color: #f8d7da;
        border-left-color: #dc3545;
    }
    .tender-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_tender_data():
    """Load tender data from database"""
    db = SessionLocal()
    try:
        tenders = db.query(Tender).all()
        return tenders
    finally:
        db.close()

@st.cache_data
def load_scraping_logs():
    """Load scraping logs from database"""
    db = SessionLocal()
    try:
        logs = db.query(ScrapingLog).order_by(ScrapingLog.start_time.desc()).limit(20).all()
        return logs
    finally:
        db.close()

def display_tender_card(tender):
    """Display a tender as a card"""
    priority_class = ""
    if tender.evaluation_score:
        if tender.evaluation_score >= 4.0:
            priority_class = "high-priority"
        elif tender.evaluation_score >= 3.0:
            priority_class = "medium-priority"
        else:
            priority_class = "low-priority"
    
    st.markdown(f"""
    <div class="tender-card {priority_class}">
        <h4>{tender.title or 'Untitled Tender'}</h4>
        <p><strong>Source:</strong> {tender.source_site}</p>
        <p><strong>Score:</strong> {tender.evaluation_score or 'Not evaluated'}/5.0</p>
        <p><strong>Deadline:</strong> {tender.deadline.strftime('%Y-%m-%d') if tender.deadline else 'Not specified'}</p>
        <p><strong>Budget:</strong> {format_budget(tender)}</p>
        <p><strong>Location:</strong> {tender.location or 'Not specified'}</p>
        <p><strong>Sector:</strong> {tender.sector or 'Not specified'}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button(f"📋 Details", key=f"details_{tender.id}"):
            show_tender_details(tender)
    with col2:
        if st.button(f"⭐ Shortlist", key=f"shortlist_{tender.id}"):
            update_tender_status(tender.id, "shortlisted")
            st.success("Added to shortlist!")
    with col3:
        if st.button(f"🔄 Re-evaluate", key=f"evaluate_{tender.id}"):
            reevaluate_tender(tender.id)
    with col4:
        if st.button(f"🔗 View Source", key=f"source_{tender.id}"):
            st.markdown(f'<a href="{tender.url}" target="_blank">Open in new tab</a>', unsafe_allow_html=True)

def format_budget(tender):
    """Format budget display"""
    if tender.budget_max:
        currency = tender.budget_currency or 'USD'
        if tender.budget_min:
            return f"{currency} {tender.budget_min:,.0f} - {tender.budget_max:,.0f}"
        else:
            return f"{currency} {tender.budget_max:,.0f}"
    return "Not specified"

def show_tender_details(tender):
    """Show detailed tender information in a modal-like container"""
    st.subheader(f"Tender Details: {tender.title}")
    
    # Basic Information
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Source Site:**", tender.source_site)
        st.write("**URL:**", tender.url)
        st.write("**Scraped At:**", tender.scraped_at)
        st.write("**Last Updated:**", tender.last_updated)
    
    with col2:
        st.write("**Deadline:**", tender.deadline)
        st.write("**Budget:**", format_budget(tender))
        st.write("**Location:**", tender.location or "Not specified")
        st.write("**Sector:**", tender.sector or "Not specified")
    
    # Description
    if tender.description:
        st.subheader("Description")
        st.write(tender.description)
    
    # Evaluation Scores
    if tender.evaluation_score:
        st.subheader("Evaluation Scores")
        score_cols = st.columns(6)
        scores = [
            ("Overall", tender.evaluation_score),
            ("Sector", tender.sector_score),
            ("Location", tender.location_score),
            ("Budget", tender.budget_score),
            ("Deadline", tender.deadline_score),
            ("Experience", tender.experience_score)
        ]
        
        for i, (label, score) in enumerate(scores):
            with score_cols[i]:
                st.metric(label, f"{score:.1f}/5.0" if score else "N/A")
    
    # AI Analysis
    if tender.ai_analysis_complete:
        st.subheader("AI Analysis")
        if tender.ai_summary:
            st.write(tender.ai_summary)
        if tender.ai_extracted_sectors:
            try:
                sectors = json.loads(tender.ai_extracted_sectors)
                st.write("**AI-Extracted Sectors:**", ", ".join(sectors))
            except:
                pass
        if tender.ai_extracted_keywords:
            try:
                keywords = json.loads(tender.ai_extracted_keywords)
                st.write("**Key Terms:**", ", ".join(keywords))
            except:
                pass
    
    # Documents
    db = SessionLocal()
    try:
        documents = db.query(TenderDocument).filter_by(tender_id=tender.id).all()
        if documents:
            st.subheader("Documents")
            for doc in documents:
                st.write(f"📄 {doc.filename}")
                if doc.ai_analyzed and doc.ai_summary:
                    with st.expander("AI Document Analysis"):
                        try:
                            analysis = json.loads(doc.ai_summary)
                            st.json(analysis)
                        except:
                            st.write(doc.ai_summary)
    finally:
        db.close()

def update_tender_status(tender_id, status):
    """Update tender status"""
    db = SessionLocal()
    try:
        tender = db.query(Tender).filter_by(id=tender_id).first()
        if tender:
            tender.status = status
            if status == "shortlisted":
                tender.is_shortlisted = True
            db.commit()
    finally:
        db.close()

def reevaluate_tender(tender_id):
    """Re-evaluate a specific tender"""
    evaluator = TenderEvaluator()
    try:
        db = SessionLocal()
        tender = db.query(Tender).filter_by(id=tender_id).first()
        if tender:
            result = evaluator.evaluate_tender(tender)
            st.success(f"Re-evaluated! New score: {result['scores']['overall_score']:.1f}/5.0")
        db.close()
    finally:
        evaluator.close()

def main():
    """Main dashboard interface"""
    st.title("🎯 Square Circle Tender Curation System")
    st.markdown("AI-powered tender discovery, evaluation, and proposal assistance")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", [
        "Dashboard",
        "Tender Browser",
        "Scraping Management", 
        "Evaluation Settings",
        "Data Export",
        "System Status"
    ])
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Tender Browser":
        show_tender_browser()
    elif page == "Scraping Management":
        show_scraping_management()
    elif page == "Evaluation Settings":
        show_evaluation_settings()
    elif page == "Data Export":
        show_data_export()
    elif page == "System Status":
        show_system_status()

def show_dashboard():
    """Main dashboard overview"""
    st.header("Dashboard Overview")
    
    # Load data
    tenders = load_tender_data()
    
    if not tenders:
        st.warning("No tenders found. Please run the scraper first.")
        if st.button("🔄 Run Quick Scrape"):
            run_scraping()
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tenders", len(tenders))
    
    with col2:
        evaluated_count = sum(1 for t in tenders if t.evaluation_score is not None)
        st.metric("Evaluated", evaluated_count)
    
    with col3:
        high_priority = sum(1 for t in tenders if t.evaluation_score and t.evaluation_score >= 4.0)
        st.metric("High Priority", high_priority)
    
    with col4:
        shortlisted = sum(1 for t in tenders if t.is_shortlisted)
        st.metric("Shortlisted", shortlisted)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Score distribution
        if any(t.evaluation_score for t in tenders):
            scores = [t.evaluation_score for t in tenders if t.evaluation_score]
            fig = px.histogram(
                x=scores, 
                title="Tender Score Distribution",
                labels={'x': 'Evaluation Score', 'y': 'Number of Tenders'},
                nbins=20
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Source sites
        source_counts = {}
        for tender in tenders:
            source_counts[tender.source_site] = source_counts.get(tender.source_site, 0) + 1
        
        if source_counts:
            fig = px.pie(
                values=list(source_counts.values()),
                names=list(source_counts.keys()),
                title="Tenders by Source Site"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent high-priority tenders
    st.subheader("🔥 Top Priority Tenders")
    high_priority_tenders = [t for t in tenders if t.evaluation_score and t.evaluation_score >= 4.0]
    high_priority_tenders.sort(key=lambda x: x.evaluation_score or 0, reverse=True)
    
    for tender in high_priority_tenders[:5]:
        display_tender_card(tender)
    
    # Quick actions
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Run Full Scrape"):
            run_scraping()
    
    with col2:
        if st.button("📊 Evaluate All Tenders"):
            evaluate_all_tenders()
    
    with col3:
        if st.button("📥 Export Shortlisted"):
            export_shortlisted_tenders()

def show_tender_browser():
    """Tender browsing interface"""
    st.header("Tender Browser")
    
    tenders = load_tender_data()
    
    if not tenders:
        st.warning("No tenders available.")
        return
    
    # Filters
    st.subheader("Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        min_score = st.slider("Minimum Score", 0.0, 5.0, 0.0, 0.1)
    
    with col2:
        source_sites = list(set(t.source_site for t in tenders))
        selected_sites = st.multiselect("Source Sites", source_sites, default=source_sites)
    
    with col3:
        sectors = list(set(t.sector for t in tenders if t.sector))
        selected_sectors = st.multiselect("Sectors", sectors)
    
    with col4:
        show_only_shortlisted = st.checkbox("Show only shortlisted")
    
    # Apply filters
    filtered_tenders = tenders
    
    if min_score > 0:
        filtered_tenders = [t for t in filtered_tenders if t.evaluation_score and t.evaluation_score >= min_score]
    
    if selected_sites:
        filtered_tenders = [t for t in filtered_tenders if t.source_site in selected_sites]
    
    if selected_sectors:
        filtered_tenders = [t for t in filtered_tenders if t.sector and any(sector in t.sector for sector in selected_sectors)]
    
    if show_only_shortlisted:
        filtered_tenders = [t for t in filtered_tenders if t.is_shortlisted]
    
    # Sort options
    sort_by = st.selectbox("Sort by", ["Evaluation Score", "Deadline", "Scraped Date", "Title"])
    
    if sort_by == "Evaluation Score":
        filtered_tenders.sort(key=lambda x: x.evaluation_score or 0, reverse=True)
    elif sort_by == "Deadline":
        filtered_tenders.sort(key=lambda x: x.deadline or datetime.max)
    elif sort_by == "Scraped Date":
        filtered_tenders.sort(key=lambda x: x.scraped_at, reverse=True)
    elif sort_by == "Title":
        filtered_tenders.sort(key=lambda x: x.title or "")
    
    # Display results
    st.subheader(f"Results ({len(filtered_tenders)} tenders)")
    
    for tender in filtered_tenders:
        display_tender_card(tender)
        st.markdown("---")

def show_scraping_management():
    """Scraping management interface"""
    st.header("Scraping Management")
    
    # Manual scraping controls
    st.subheader("Manual Scraping")
    
    sites = list(Config.SITES_CONFIG.keys())
    selected_sites = st.multiselect("Select sites to scrape", sites, default=sites)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start Scraping"):
            if selected_sites:
                run_scraping(selected_sites)
            else:
                st.warning("Please select at least one site")
    
    with col2:
        if st.button("📊 Evaluate After Scraping"):
            st.session_state.evaluate_after_scrape = True
    
    # Scraping logs
    st.subheader("Recent Scraping Activity")
    logs = load_scraping_logs()
    
    if logs:
        log_data = []
        for log in logs:
            log_data.append({
                "Site": log.site_name,
                "Start Time": log.start_time,
                "End Time": log.end_time,
                "Status": log.status,
                "Tenders Found": log.tenders_found,
                "New": log.tenders_new,
                "Updated": log.tenders_updated,
                "Error": log.error_message
            })
        
        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No scraping logs available")
    
    # Site configuration
    st.subheader("Site Configuration")
    
    for site_key, site_config in Config.SITES_CONFIG.items():
        with st.expander(f"{site_config['name']} Configuration"):
            st.write(f"**Base URL:** {site_config['base_url']}")
            st.write(f"**Search URL:** {site_config['search_url']}")
            st.write(f"**Requires Login:** {site_config.get('requires_login', False)}")
            
            if site_config.get('requires_login'):
                if site_key == 'devex':
                    status = "✅ Configured" if Config.DEVEX_EMAIL else "❌ Missing credentials"
                elif site_key == 'tenders_gov_au':
                    status = "✅ Configured" if Config.TENDERS_GOV_EMAIL else "❌ Missing credentials"
                else:
                    status = "❓ Unknown"
                st.write(f"**Credentials Status:** {status}")

def show_evaluation_settings():
    """Evaluation settings interface"""
    st.header("Evaluation Settings")
    
    # Company experience profiles
    st.subheader("Company Experience Profiles")
    
    db = SessionLocal()
    try:
        profiles = db.query(CompanyProfile).all()
        
        if profiles:
            profile_data = []
            for profile in profiles:
                profile_data.append({
                    "Sector": profile.sector,
                    "Country/Region": profile.country or profile.region or "Global",
                    "Experience Level": profile.experience_level,
                    "Success Rate": profile.success_rate,
                    "Similar Projects": profile.similar_projects
                })
            
            df = pd.DataFrame(profile_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No experience profiles configured")
        
        # Add new profile
        st.subheader("Add Experience Profile")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_sector = st.text_input("Sector")
        with col2:
            new_country = st.text_input("Country/Region (optional)")
        with col3:
            new_experience = st.slider("Experience Level", 1.0, 5.0, 3.0, 0.1)
        
        if st.button("Add Profile"):
            if new_sector:
                evaluator = TenderEvaluator()
                evaluator.update_company_profile(new_sector, new_country, new_experience)
                evaluator.close()
                st.success("Profile added!")
                st.experimental_rerun()
    
    finally:
        db.close()
    
    # Priority sectors configuration
    st.subheader("Priority Sectors & Weights")
    
    sectors_df = pd.DataFrame([
        {"Sector": sector, "Weight": weight}
        for sector, weight in Config.evaluation.priority_sectors.items()
    ])
    
    st.dataframe(sectors_df, use_container_width=True)
    
    # Geographic preferences
    st.subheader("Geographic Preferences")
    
    geo_df = pd.DataFrame([
        {"Region": region, "Weight": weight}
        for region, weight in Config.evaluation.geographic_preferences.items()
    ])
    
    st.dataframe(geo_df, use_container_width=True)

def show_data_export():
    """Data export interface"""
    create_export_interface()

def show_system_status():
    """System status and health check"""
    st.header("System Status")
    
    # API Status
    st.subheader("API Configuration")
    col1, col2 = st.columns(2)
    
    with col1:
        openai_status = "✅ Configured" if Config.OPENAI_API_KEY else "❌ Missing"
        st.write(f"**OpenAI API:** {openai_status}")
    
    with col2:
        db_status = "✅ Connected"
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
        except:
            db_status = "❌ Connection Failed"
        st.write(f"**Database:** {db_status}")
    
    # Site credentials
    st.subheader("Site Credentials")
    credentials_status = {
        "Devex.org": "✅ Configured" if Config.DEVEX_EMAIL and Config.DEVEX_PASSWORD else "❌ Missing",
        "Tenders.gov.au": "✅ Configured" if Config.TENDERS_GOV_EMAIL and Config.TENDERS_GOV_PASSWORD else "❌ Missing"
    }
    
    for site, status in credentials_status.items():
        st.write(f"**{site}:** {status}")
    
    # Database statistics
    st.subheader("Database Statistics")
    db = SessionLocal()
    try:
        tender_count = db.query(Tender).count()
        document_count = db.query(TenderDocument).count()
        log_count = db.query(ScrapingLog).count()
        profile_count = db.query(CompanyProfile).count()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Tenders", tender_count)
        with col2:
            st.metric("Documents", document_count)
        with col3:
            st.metric("Scraping Logs", log_count)
        with col4:
            st.metric("Experience Profiles", profile_count)
    
    finally:
        db.close()
    
    # System health check
    if st.button("🔍 Run Health Check"):
        run_health_check()

def run_scraping(selected_sites=None):
    """Run scraping operation"""
    with st.spinner("Running scraper..."):
        try:
            manager = ScrapingManager()
            
            if selected_sites:
                # Scrape only selected sites
                results = {'site_results': {}}
                for site_key in selected_sites:
                    if site_key in Config.SITES_CONFIG:
                        site_config = Config.SITES_CONFIG[site_key]
                        from scraper import TenderScraper
                        scraper = TenderScraper(site_config)
                        tender_data_list = scraper.scrape_site()
                        site_stats = manager.process_scraped_data(tender_data_list, site_config['name'])
                        results['site_results'][site_config['name']] = site_stats
            else:
                # Scrape all sites
                results = manager.scrape_all_sites()
            
            manager.close()
            
            # Display results
            st.success("Scraping completed!")
            
            for site_name, stats in results['site_results'].items():
                if 'error' in stats:
                    st.error(f"{site_name}: {stats['error']}")
                else:
                    st.info(f"{site_name}: {stats.get('new', 0)} new, {stats.get('updated', 0)} updated")
            
            # Auto-evaluate if requested
            if st.session_state.get('evaluate_after_scrape', False):
                evaluate_all_tenders()
                st.session_state.evaluate_after_scrape = False
        
        except Exception as e:
            st.error(f"Scraping failed: {str(e)}")

def evaluate_all_tenders():
    """Evaluate all tenders"""
    with st.spinner("Evaluating tenders..."):
        try:
            evaluator = TenderEvaluator()
            results = evaluator.evaluate_all_tenders()
            evaluator.close()
            
            successful = len([r for r in results if 'error' not in r])
            st.success(f"Evaluated {successful} tenders successfully!")
            
            # Clear cache to refresh data
            st.cache_data.clear()
        
        except Exception as e:
            st.error(f"Evaluation failed: {str(e)}")

def export_shortlisted_tenders():
    """Export shortlisted tenders"""
    tenders = load_tender_data()
    shortlisted = [t for t in tenders if t.is_shortlisted]
    
    if shortlisted:
        file_data = generate_export_file(shortlisted, "Excel (.xlsx)")
        
        st.download_button(
            label="Download Shortlisted Tenders (Excel)",
            data=file_data,
            file_name=f"shortlisted_tenders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No shortlisted tenders found")

def generate_export_file(tenders, format_type):
    """Generate export file in specified format"""
    # Prepare data
    export_data = []
    for tender in tenders:
        export_data.append({
            "Title": tender.title,
            "Source Site": tender.source_site,
            "URL": tender.url,
            "Description": tender.description,
            "Funder": tender.funder,
            "Sector": tender.sector,
            "Location": tender.location,
            "Budget Min": tender.budget_min,
            "Budget Max": tender.budget_max,
            "Currency": tender.budget_currency,
            "Deadline": tender.deadline,
            "Evaluation Score": tender.evaluation_score,
            "Sector Score": tender.sector_score,
            "Location Score": tender.location_score,
            "Budget Score": tender.budget_score,
            "Deadline Score": tender.deadline_score,
            "Experience Score": tender.experience_score,
            "Status": tender.status,
            "Shortlisted": tender.is_shortlisted,
            "Scraped At": tender.scraped_at,
            "Last Updated": tender.last_updated
        })
    
    df = pd.DataFrame(export_data)
    
    if format_type == "Excel (.xlsx)":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tenders')
        return output.getvalue()
    
    elif format_type == "CSV (.csv)":
        return df.to_csv(index=False).encode('utf-8')
    
    else:  # JSON
        return df.to_json(orient='records', date_format='iso').encode('utf-8')

def run_health_check():
    """Run comprehensive health check"""
    st.subheader("Health Check Results")
    
    checks = []
    
    # Database connectivity
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        checks.append(("Database Connection", "✅ OK", ""))
    except Exception as e:
        checks.append(("Database Connection", "❌ Failed", str(e)))
    
    # OpenAI API
    if Config.OPENAI_API_KEY:
        try:
            analyzer = DocumentAnalyzer()
            checks.append(("OpenAI API", "✅ Configured", ""))
        except Exception as e:
            checks.append(("OpenAI API", "❌ Error", str(e)))
    else:
        checks.append(("OpenAI API", "⚠️ Not Configured", "API key missing"))
    
    # Site credentials
    for site, creds in [
        ("Devex", (Config.DEVEX_EMAIL, Config.DEVEX_PASSWORD)),
        ("Tenders.gov.au", (Config.TENDERS_GOV_EMAIL, Config.TENDERS_GOV_PASSWORD))
    ]:
        if creds[0] and creds[1]:
            checks.append((f"{site} Credentials", "✅ Configured", ""))
        else:
            checks.append((f"{site} Credentials", "⚠️ Missing", "Login required sites won't work"))
    
    # File system
    for path_name, path in [("Export Path", Config.EXPORT_PATH), ("Attachment Path", Config.ATTACHMENT_PATH)]:
        if os.path.exists(path) and os.access(path, os.W_OK):
            checks.append((path_name, "✅ OK", path))
        else:
            checks.append((path_name, "❌ Not Accessible", path))
    
    # Display results
    for check_name, status, details in checks:
        col1, col2, col3 = st.columns([2, 1, 3])
        with col1:
            st.write(check_name)
        with col2:
            st.write(status)
        with col3:
            st.write(details)

if __name__ == "__main__":
    main()
