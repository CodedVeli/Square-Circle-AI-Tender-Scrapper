"""
Export Module for Square Circle Tender System
Handles CSV, Excel, and PDF exports of tender data
"""
import pandas as pd
import io
import json
from datetime import datetime
from typing import List, Dict
from models import Tender, SessionLocal
import streamlit as st

class TenderExporter:
    """Export tender data in various formats"""
    
    def __init__(self):
        """Initialize exporter"""
        pass
    
    def prepare_tender_data(self, tenders: List[Tender], include_scores: bool = True) -> pd.DataFrame:
        """Convert tender data to pandas DataFrame for export"""
        data = []
        
        for tender in tenders:
            row = {
                'ID': tender.id,
                'Title': tender.title or 'Untitled',
                'Source': tender.source_site,
                'URL': tender.url,
                'Deadline': tender.deadline.strftime('%Y-%m-%d') if tender.deadline else '',
                'Location': tender.location or '',
                'Sector': tender.sector or '',
                'Budget_Min': tender.budget_min or '',
                'Budget_Max': tender.budget_max or '',
                'Budget_Currency': tender.budget_currency or '',
                'Description': (tender.description or '')[:500],  # Truncate for export
                'Scraped_Date': tender.scraped_at.strftime('%Y-%m-%d %H:%M') if tender.scraped_at else '',
                'Last_Updated': tender.last_updated.strftime('%Y-%m-%d %H:%M') if tender.last_updated else ''
            }
            
            if include_scores and tender.evaluation_score:
                row.update({
                    'Evaluation_Score': round(tender.evaluation_score, 2),
                    'Priority': self.get_priority_label(tender.evaluation_score),
                    'Evaluation_Reasons': tender.evaluation_reasons or ''
                })
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def get_priority_label(self, score: float) -> str:
        """Get priority label based on score"""
        if score >= 4.0:
            return "High Priority"
        elif score >= 3.0:
            return "Medium Priority"
        elif score >= 2.0:
            return "Low Priority"
        else:
            return "Very Low Priority"
    
    def export_to_csv(self, tenders: List[Tender], filename: str = None) -> io.StringIO:
        """Export tenders to CSV format"""
        df = self.prepare_tender_data(tenders)
        
        # Create CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        return csv_buffer
    
    def export_to_excel(self, tenders: List[Tender], filename: str = None) -> io.BytesIO:
        """Export tenders to Excel format with multiple sheets"""
        df = self.prepare_tender_data(tenders)
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='All_Tenders', index=False)
            
            # High priority tenders
            high_priority = df[df['Evaluation_Score'] >= 3.0] if 'Evaluation_Score' in df.columns else pd.DataFrame()
            if not high_priority.empty:
                high_priority.to_excel(writer, sheet_name='Recommended_Tenders', index=False)
            
            # Summary by source
            if not df.empty:
                summary = df.groupby('Source').agg({
                    'ID': 'count',
                    'Evaluation_Score': ['mean', 'max', 'min'] if 'Evaluation_Score' in df.columns else 'count'
                }).round(2)
                summary.columns = ['Count', 'Avg_Score', 'Max_Score', 'Min_Score'] if 'Evaluation_Score' in df.columns else ['Count']
                summary.to_excel(writer, sheet_name='Summary_by_Source')
            
            # Timeline if deadlines exist
            timeline_data = df[df['Deadline'] != ''].copy() if not df.empty else pd.DataFrame()
            if not timeline_data.empty:
                timeline_data['Deadline'] = pd.to_datetime(timeline_data['Deadline'])
                timeline_data = timeline_data.sort_values('Deadline')
                timeline_data.to_excel(writer, sheet_name='Timeline', index=False)
        
        excel_buffer.seek(0)
        return excel_buffer
    
    def export_summary_report(self, tenders: List[Tender]) -> Dict:
        """Generate summary report data"""
        if not tenders:
            return {"error": "No tenders to analyze"}
        
        df = self.prepare_tender_data(tenders)
        
        # Basic stats
        total_tenders = len(tenders)
        evaluated_tenders = sum(1 for t in tenders if t.evaluation_score is not None)
        
        # Score distribution
        score_dist = {
            "high_priority": sum(1 for t in tenders if t.evaluation_score and t.evaluation_score >= 4.0),
            "medium_priority": sum(1 for t in tenders if t.evaluation_score and 3.0 <= t.evaluation_score < 4.0),
            "low_priority": sum(1 for t in tenders if t.evaluation_score and 2.0 <= t.evaluation_score < 3.0),
            "very_low_priority": sum(1 for t in tenders if t.evaluation_score and t.evaluation_score < 2.0)
        }
        
        # Source breakdown
        source_stats = df.groupby('Source').agg({
            'ID': 'count',
            'Evaluation_Score': 'mean' if 'Evaluation_Score' in df.columns else 'count'
        }).round(2).to_dict()
        
        # Top scoring tenders
        top_tenders = sorted(
            [t for t in tenders if t.evaluation_score],
            key=lambda x: x.evaluation_score,
            reverse=True
        )[:10]
        
        # Recent activity
        recent_tenders = sorted(
            tenders,
            key=lambda x: x.scraped_at or datetime.min,
            reverse=True
        )[:5]
        
        # Upcoming deadlines
        upcoming_deadlines = sorted(
            [t for t in tenders if t.deadline and t.deadline > datetime.now()],
            key=lambda x: x.deadline
        )[:10]
        
        return {
            "summary": {
                "total_tenders": total_tenders,
                "evaluated_tenders": evaluated_tenders,
                "evaluation_coverage": f"{(evaluated_tenders/total_tenders*100):.1f}%" if total_tenders > 0 else "0%"
            },
            "score_distribution": score_dist,
            "source_statistics": source_stats,
            "top_tenders": [
                {
                    "title": t.title,
                    "score": round(t.evaluation_score, 2),
                    "source": t.source_site,
                    "deadline": t.deadline.strftime('%Y-%m-%d') if t.deadline else None
                }
                for t in top_tenders
            ],
            "recent_activity": [
                {
                    "title": t.title,
                    "source": t.source_site,
                    "scraped": t.scraped_at.strftime('%Y-%m-%d') if t.scraped_at else None
                }
                for t in recent_tenders
            ],
            "upcoming_deadlines": [
                {
                    "title": t.title,
                    "deadline": t.deadline.strftime('%Y-%m-%d') if t.deadline else None,
                    "score": round(t.evaluation_score, 2) if t.evaluation_score else None,
                    "source": t.source_site
                }
                for t in upcoming_deadlines
            ]
        }

def get_all_tenders():
    """Get all tenders from database"""
    db = SessionLocal()
    try:
        return db.query(Tender).all()
    finally:
        db.close()

def create_export_interface():
    """Create Streamlit interface for exports"""
    st.subheader("📤 Export Tenders")
    
    # Load data
    tenders = get_all_tenders()
    
    if not tenders:
        st.warning("No tenders found to export.")
        return
    
    st.info(f"Found {len(tenders)} tenders in database")
    
    # Export options
    export_format = st.selectbox(
        "Select Export Format:",
        ["CSV", "Excel (XLSX)", "Summary Report"]
    )
    
    # Filter options
    st.subheader("🔍 Filter Options")
    col1, col2 = st.columns(2)
    
    with col1:
        # Source filter
        sources = list(set(t.source_site for t in tenders if t.source_site))
        selected_sources = st.multiselect("Filter by Source:", sources, default=sources)
        
        # Score filter
        min_score = st.slider("Minimum Score:", 0.0, 5.0, 0.0, 0.1)
    
    with col2:
        # Date range
        has_deadlines = [t for t in tenders if t.deadline]
        if has_deadlines:
            min_date = min(t.deadline for t in has_deadlines).date()
            max_date = max(t.deadline for t in has_deadlines).date()
            
            date_range = st.date_input(
                "Deadline Range:",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
        
        # Include evaluated only
        only_evaluated = st.checkbox("Only evaluated tenders", value=True)
    
    # Apply filters
    filtered_tenders = tenders
    
    if selected_sources:
        filtered_tenders = [t for t in filtered_tenders if t.source_site in selected_sources]
    
    if min_score > 0:
        filtered_tenders = [t for t in filtered_tenders if t.evaluation_score and t.evaluation_score >= min_score]
    
    if only_evaluated:
        filtered_tenders = [t for t in filtered_tenders if t.evaluation_score is not None]
    
    if has_deadlines and 'date_range' in locals() and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_tenders = [
            t for t in filtered_tenders 
            if t.deadline and start_date <= t.deadline.date() <= end_date
        ]
    
    st.info(f"Filtered to {len(filtered_tenders)} tenders")
    
    # Export button
    if st.button("📤 Generate Export", type="primary"):
        if not filtered_tenders:
            st.error("No tenders match the selected criteria.")
            return
        
        exporter = TenderExporter()
        
        try:
            if export_format == "CSV":
                csv_data = exporter.export_to_csv(filtered_tenders)
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data.getvalue(),
                    file_name=f"tenders_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
            elif export_format == "Excel (XLSX)":
                excel_data = exporter.export_to_excel(filtered_tenders)
                
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data.getvalue(),
                    file_name=f"tenders_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            elif export_format == "Summary Report":
                report = exporter.export_summary_report(filtered_tenders)
                
                # Display summary
                st.subheader("📊 Summary Report")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Tenders", report["summary"]["total_tenders"])
                with col2:
                    st.metric("Evaluated", report["summary"]["evaluated_tenders"])
                with col3:
                    st.metric("Coverage", report["summary"]["evaluation_coverage"])
                
                # Score distribution
                st.subheader("Priority Distribution")
                score_dist = report["score_distribution"]
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🔴 High Priority", score_dist["high_priority"])
                with col2:
                    st.metric("🟡 Medium Priority", score_dist["medium_priority"])
                with col3:
                    st.metric("🟠 Low Priority", score_dist["low_priority"])
                with col4:
                    st.metric("⚫ Very Low", score_dist["very_low_priority"])
                
                # Top tenders
                if report["top_tenders"]:
                    st.subheader("🏆 Top Scoring Tenders")
                    for i, tender in enumerate(report["top_tenders"], 1):
                        st.write(f"{i}. **{tender['title']}** - Score: {tender['score']}/5.0 ({tender['source']})")
                
                # Export JSON
                st.download_button(
                    label="📥 Download Full Report (JSON)",
                    data=json.dumps(report, indent=2, default=str),
                    file_name=f"tender_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
                
        except Exception as e:
            st.error(f"Export failed: {str(e)}")

if __name__ == "__main__":
    create_export_interface()
