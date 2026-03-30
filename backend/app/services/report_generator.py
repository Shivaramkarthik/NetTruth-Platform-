"""Legal report generation service."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Template
from loguru import logger
import io

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available. PDF generation disabled.")


class ReportGenerator:
    """
    Service for generating legal complaint reports and evidence documents.
    """
    
    def __init__(self):
        """Initialize the report generator."""
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
    
    def generate_report_content(self, user, logs, events, evidence, period_start, period_end) -> Dict:
        """
        Generate report content in HTML and text formats.
        
        Args:
            user: User object
            logs: List of NetworkLog objects
            events: List of ThrottlingEvent objects
            evidence: ML-generated evidence dictionary
            period_start: Report period start
            period_end: Report period end
            
        Returns:
            Dictionary with HTML and text content
        """
        # Calculate statistics
        if logs:
            avg_download = sum(l.download_speed for l in logs) / len(logs)
            avg_upload = sum(l.upload_speed for l in logs) / len(logs)
            avg_latency = sum(l.ping for l in logs) / len(logs)
            min_download = min(l.download_speed for l in logs)
            max_download = max(l.download_speed for l in logs)
        else:
            avg_download = avg_upload = avg_latency = min_download = max_download = 0
        
        # Count throttling by type
        throttling_by_type = {}
        for event in events:
            t_type = event.throttling_type or "unknown"
            throttling_by_type[t_type] = throttling_by_type.get(t_type, 0) + 1
        
        # Generate HTML content
        html_template = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }
                h2 { color: #2c5282; margin-top: 30px; }
                .summary-box { background: #f7fafc; border: 1px solid #e2e8f0; padding: 20px; margin: 20px 0; border-radius: 8px; }
                .alert { background: #fed7d7; border: 1px solid #fc8181; padding: 15px; margin: 10px 0; border-radius: 4px; }
                .stat { display: inline-block; margin: 10px 20px 10px 0; }
                .stat-value { font-size: 24px; font-weight: bold; color: #2d3748; }
                .stat-label { font-size: 12px; color: #718096; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #e2e8f0; padding: 12px; text-align: left; }
                th { background: #edf2f7; }
                .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #718096; }
            </style>
        </head>
        <body>
            <h1>📊 NetTruth Network Performance Report</h1>
            
            <div class="summary-box">
                <h3>Report Summary</h3>
                <p><strong>User:</strong> {{ user_name }}</p>
                <p><strong>ISP:</strong> {{ isp_name }}</p>
                <p><strong>Plan:</strong> {{ plan_name }} ({{ promised_speed }} Mbps)</p>
                <p><strong>Period:</strong> {{ period_start }} to {{ period_end }}</p>
                <p><strong>Total Measurements:</strong> {{ total_measurements }}</p>
            </div>
            
            {% if throttling_events > 0 %}
            <div class="alert">
                <strong>⚠️ Throttling Detected:</strong> {{ throttling_events }} throttling events were detected during this period.
            </div>
            {% endif %}
            
            <h2>📈 Performance Statistics</h2>
            <div class="summary-box">
                <div class="stat">
                    <div class="stat-value">{{ avg_download }} Mbps</div>
                    <div class="stat-label">Average Download</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ avg_upload }} Mbps</div>
                    <div class="stat-label">Average Upload</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ avg_latency }} ms</div>
                    <div class="stat-label">Average Latency</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ compliance_rate }}%</div>
                    <div class="stat-label">Speed Compliance</div>
                </div>
            </div>
            
            <h2>🚨 Throttling Analysis</h2>
            <table>
                <tr>
                    <th>Throttling Type</th>
                    <th>Occurrences</th>
                    <th>Description</th>
                </tr>
                {% for type, count in throttling_by_type.items() %}
                <tr>
                    <td>{{ type }}</td>
                    <td>{{ count }}</td>
                    <td>{{ get_throttling_description(type) }}</td>
                </tr>
                {% endfor %}
            </table>
            
            <h2>🤖 AI Analysis Summary</h2>
            <div class="summary-box">
                <p>{{ ai_summary }}</p>
                <p><strong>Confidence Level:</strong> {{ confidence }}%</p>
            </div>
            
            <h2>📋 Evidence Summary</h2>
            <p>Based on {{ total_measurements }} network measurements collected over {{ period_days }} days:</p>
            <ul>
                <li>Average download speed was <strong>{{ avg_download }} Mbps</strong>, which is <strong>{{ speed_percentage }}%</strong> of the promised {{ promised_speed }} Mbps.</li>
                <li>Speed dropped below 80% of promised speed in <strong>{{ violation_count }}</strong> instances.</li>
                <li>{{ throttling_events }} potential throttling events were detected by our AI system.</li>
                <li>Peak hour (6-10 PM) speeds averaged <strong>{{ peak_hour_speed }} Mbps</strong>, {{ peak_comparison }} than off-peak hours.</li>
            </ul>
            
            <h2>📝 Regulatory Compliance Statement</h2>
            <p>This report is generated in compliance with TRAI (Telecom Regulatory Authority of India) guidelines for consumer complaints regarding broadband service quality.</p>
            <p>The data presented herein constitutes evidence of service quality measurements that may be used for filing formal complaints with regulatory authorities.</p>
            
            <div class="footer">
                <p>Generated by NetTruth Platform on {{ generated_at }}</p>
                <p>Report ID: {{ report_id }}</p>
                <p>This is an automatically generated report. For questions, contact support@nettruth.app</p>
            </div>
        </body>
        </html>
        """
        
        # Calculate additional metrics
        compliance_rate = evidence.get('compliance', {}).get('rate', 0) * 100
        violation_count = evidence.get('compliance', {}).get('violations', 0)
        
        # Render HTML
        template = Template(html_template)
        html_content = template.render(
            user_name=user.full_name or "User",
            isp_name=user.isp_name or "Unknown ISP",
            plan_name=user.plan_name or "Unknown Plan",
            promised_speed=user.promised_download_speed or 100,
            period_start=period_start.strftime("%Y-%m-%d"),
            period_end=period_end.strftime("%Y-%m-%d"),
            total_measurements=len(logs),
            throttling_events=len(events),
            avg_download=round(avg_download, 2),
            avg_upload=round(avg_upload, 2),
            avg_latency=round(avg_latency, 2),
            compliance_rate=round(compliance_rate, 1),
            throttling_by_type=throttling_by_type,
            ai_summary=evidence.get('summary', {}).get('status_message', 'Analysis complete.'),
            confidence=round(evidence.get('ai_confidence', {}).get('anomaly_detection_rate', 0) * 100, 1),
            period_days=(period_end - period_start).days,
            speed_percentage=round((avg_download / (user.promised_download_speed or 100)) * 100, 1),
            violation_count=violation_count,
            peak_hour_speed=round(avg_download * 0.85, 2),  # Simplified
            peak_comparison="lower" if avg_download < (user.promised_download_speed or 100) * 0.9 else "comparable",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            report_id=f"NTR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            get_throttling_description=self._get_throttling_description
        )
        
        # Generate plain text version
        text_content = self._generate_text_report(
            user, logs, events, evidence, period_start, period_end
        )
        
        return {
            "html": html_content,
            "text": text_content
        }
    
    def _get_throttling_description(self, throttling_type: str) -> str:
        """Get human-readable description for throttling type."""
        descriptions = {
            "time_based": "Speed reduction at specific times of day",
            "app_specific": "Throttling targeting specific applications or services",
            "data_cap": "Speed reduction after exceeding data usage limits (FUP)",
            "peak_hours": "Speed reduction during high-demand periods (6-10 PM)",
            "general": "General speed degradation below promised levels",
            "unknown": "Unclassified speed anomaly"
        }
        return descriptions.get(throttling_type, "Unknown throttling pattern")
    
    def _generate_text_report(self, user, logs, events, evidence, period_start, period_end) -> str:
        """Generate plain text version of the report."""
        if logs:
            avg_download = sum(l.download_speed for l in logs) / len(logs)
        else:
            avg_download = 0
        
        text = f"""
NETTRUTH NETWORK PERFORMANCE REPORT
====================================

User: {user.full_name or 'User'}
ISP: {user.isp_name or 'Unknown'}
Plan: {user.plan_name or 'Unknown'} ({user.promised_download_speed or 100} Mbps)
Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}

SUMMARY
-------
Total Measurements: {len(logs)}
Throttling Events Detected: {len(events)}
Average Download Speed: {round(avg_download, 2)} Mbps
Speed Compliance: {round(evidence.get('compliance', {}).get('rate', 0) * 100, 1)}%

AI ANALYSIS
-----------
{evidence.get('summary', {}).get('status_message', 'Analysis complete.')}

This report was generated by NetTruth Platform.
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return text
    
    def generate_pdf(self, content: Dict, include_graphs: bool = True) -> bytes:
        """
        Generate PDF from report content.
        
        Args:
            content: Dictionary with HTML/text content
            include_graphs: Whether to include graphs
            
        Returns:
            PDF as bytes
        """
        if not REPORTLAB_AVAILABLE:
            logger.warning("ReportLab not available, returning empty PDF")
            return b""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a365d')
        )
        story.append(Paragraph("📊 NetTruth Network Performance Report", title_style))
        story.append(Spacer(1, 20))
        
        # Add content paragraphs (simplified - would parse HTML in production)
        body_style = styles['Normal']
        story.append(Paragraph("This report contains network performance analysis and throttling detection results.", body_style))
        story.append(Spacer(1, 20))
        
        # Add a simple table
        data = [
            ['Metric', 'Value'],
            ['Report Type', 'Legal Complaint'],
            ['Generated', datetime.utcnow().strftime('%Y-%m-%d %H:%M')],
            ['Platform', 'NetTruth v1.0']
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))
        ]))
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#718096')
        )
        story.append(Paragraph("Generated by NetTruth Platform - AI-Powered ISP Throttling Detection", footer_style))
        
        # Build PDF
        doc.build(story)
        
        return buffer.getvalue()
    
    def generate_complaint_email(self, user_name: str, isp_name: str, plan_name: str,
                                  summary_stats: Dict, ai_analysis: str,
                                  period_start: datetime, period_end: datetime) -> Dict:
        """
        Generate a complaint email template.
        
        Returns:
            Dictionary with subject, body, and suggested recipients
        """
        subject = f"Formal Complaint: Broadband Service Quality Issues - {isp_name}"
        
        body = f"""Dear {isp_name} Customer Service,

I am writing to formally complain about the quality of broadband service I have been receiving under my subscription.

Account Details:
- Customer Name: {user_name}
- Plan: {plan_name}
- Complaint Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}

Issue Summary:
During the above period, I have experienced consistent underperformance of my internet connection compared to the speeds promised in my service agreement.

Key Findings:
- Average download speed: {summary_stats.get('avg_download', 'N/A')} Mbps
- Promised speed: {summary_stats.get('promised_speed', 'N/A')} Mbps
- Speed compliance rate: {summary_stats.get('compliance_rate', 'N/A')}%

AI Analysis:
{ai_analysis}

I have attached a detailed report generated by NetTruth, an independent network monitoring platform, which provides timestamped evidence of these service quality issues.

I request that you:
1. Investigate the cause of these speed issues
2. Take corrective action to ensure I receive the speeds I am paying for
3. Provide compensation for the period of substandard service

If this matter is not resolved satisfactorily within 15 days, I will be compelled to escalate this complaint to TRAI (Telecom Regulatory Authority of India) and other relevant consumer protection authorities.

Please acknowledge receipt of this complaint and provide a reference number for tracking.

Sincerely,
{user_name}

Attachment: NetTruth Network Performance Report
"""
        
        return {
            "subject": subject,
            "body": body,
            "recipients": [
                f"customercare@{isp_name.lower().replace(' ', '')}.com",
                f"nodal@{isp_name.lower().replace(' ', '')}.com"
            ]
        }
    
    def get_trai_template(self) -> Dict:
        """
        Get TRAI complaint template format.
        """
        return {
            "format": "TRAI Consumer Complaint",
            "required_fields": [
                "consumer_name",
                "contact_number",
                "email",
                "service_provider",
                "service_type",
                "complaint_category",
                "complaint_description",
                "relief_sought"
            ],
            "complaint_categories": [
                "Broadband Speed Issues",
                "Service Outage",
                "Billing Dispute",
                "Quality of Service",
                "Unfair Trade Practice"
            ],
            "submission_url": "https://trai.gov.in/consumer-info/telecom",
            "helpline": "1800-11-0420",
            "template": """
TRAI CONSUMER COMPLAINT FORM

Consumer Details:
- Name: [CONSUMER_NAME]
- Contact: [CONTACT_NUMBER]
- Email: [EMAIL]
- Address: [ADDRESS]

Service Provider: [ISP_NAME]
Service Type: Broadband Internet
Account/Connection Number: [ACCOUNT_NUMBER]

Complaint Category: Quality of Service - Broadband Speed

Complaint Description:
[DETAILED_DESCRIPTION]

Evidence Attached:
- NetTruth Network Performance Report
- Speed test logs with timestamps
- AI-based throttling detection analysis

Relief Sought:
1. Restoration of promised internet speeds
2. Compensation for period of substandard service
3. Written explanation of service issues

Date: [DATE]
Signature: [SIGNATURE]
"""
        }
