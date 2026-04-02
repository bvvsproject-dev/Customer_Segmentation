import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def add_header_footer(canvas, doc):
    canvas.saveState()
    # Header
    canvas.setFont('Helvetica-Bold', 14)
    canvas.setFillColor(colors.HexColor("#4F8CFF"))
    canvas.drawString(inch, doc.pagesize[1] - 0.5 * inch, "AI Customer Segmentation")
    canvas.setFont('Helvetica', 10)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(doc.pagesize[0] - inch, doc.pagesize[1] - 0.5 * inch, "Confidential Report")
    
    # Line under header
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setLineWidth(1)
    canvas.line(inch, doc.pagesize[1] - 0.6 * inch, doc.pagesize[0] - inch, doc.pagesize[1] - 0.6 * inch)
    
    # Footer
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(colors.grey)
    canvas.drawString(inch, 0.5 * inch, "Generated automatically by SaaS Platform")
    canvas.drawRightString(doc.pagesize[0] - inch, 0.5 * inch, f"Page {doc.page}")
    
    # Line above footer
    canvas.line(inch, 0.7 * inch, doc.pagesize[0] - inch, 0.7 * inch)
    canvas.restoreState()

def create_pdf_report(payload):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=inch, leftMargin=inch,
        topMargin=inch, bottomMargin=inch
    )
    
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    title_style.textColor = colors.HexColor("#1F2937")
    
    h2_style = ParagraphStyle('Heading2', parent=styles['Heading2'], textColor=colors.HexColor("#4F8CFF"), spaceAfter=12)
    h3_style = ParagraphStyle('Heading3', parent=styles['Heading3'], textColor=colors.HexColor("#111827"), spaceAfter=6, spaceBefore=12)
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 14
    
    Story = []
    
    # PAGE 1: SUMMARY
    Story.append(Paragraph("Customer Insights Report", title_style))
    Story.append(Spacer(1, 0.2 * inch))
    
    Story.append(Paragraph("1. Executive Summary", h2_style))
    stats = payload.get('stats', {})
    
    summary_data = [
        ["Total Customers", "Average Income", "Average Age", "Total Clusters"],
        [str(stats.get('total', 0)), f"${stats.get('income', 0)}k", str(stats.get('age', 0)), str(stats.get('cluster_count', 0))]
    ]
    
    t = Table(summary_data, colWidths=[1.5*inch]*4)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F3F4F6")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#111827")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#E5E7EB"))
    ]))
    Story.append(t)
    Story.append(Spacer(1, 0.3 * inch))
    
    # Insights
    insights = payload.get('insights', [])
    if insights:
        Story.append(Paragraph("AI Strategic Insights", h3_style))
        for cluster in insights:
            Story.append(Paragraph(f"<b>{cluster.get('label', 'Unknown')}</b>", normal_style))
            Story.append(Paragraph(f"Explanation: {cluster.get('explanation', '')}", normal_style))
            Story.append(Paragraph(f"Strategy: {cluster.get('strategy', '')}", normal_style))
            Story.append(Spacer(1, 0.1 * inch))

    Story.append(PageBreak())

    # PAGE 2: GRAPHS
    Story.append(Paragraph("2. Visual Analytics", h2_style))
    charts = payload.get('charts', {})
    
    for chart_label, key in [('Cluster Distribution (Scatter)', 'scatter'), 
                           ('Elbow Method (WCSS)', 'elbow'), 
                           ('Silhouette Scores', 'silhouette')]:
        b64_str = charts.get(key)
        if b64_str:
            try:
                if ',' in b64_str:
                    b64_str = b64_str.split(',')[1]
                img_data = base64.b64decode(b64_str)
                img_io = io.BytesIO(img_data)
                
                Story.append(Paragraph(chart_label, h3_style))
                
                img = Image(img_io)
                max_width = 6.5 * inch
                max_height = 3.0 * inch
                
                aspect = img.imageWidth / float(img.imageHeight)
                if aspect > (max_width / max_height):
                    img.drawWidth = max_width
                    img.drawHeight = max_width / aspect
                else:
                    img.drawHeight = max_height
                    img.drawWidth = max_height * aspect
                    
                img.hAlign = 'CENTER'
                Story.append(img)
                Story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                Story.append(Paragraph(f"Error loading {key} chart: {str(e)}", normal_style))
                
    Story.append(PageBreak())

    # PAGE 3+: CLUSTER DETAILS
    Story.append(Paragraph("3. Segment Database (Top Samples)", h2_style))
    
    clusters = payload.get('clusters', {})
    
    for cid, cdata in clusters.items():
        Story.append(Paragraph(f"Cluster ID: {cid} | Label: {cdata.get('label', '')}", h3_style))
        
        # Cluster Stats
        c_stats = [
            ["Size", "Avg Age", "Avg Income", "Avg Score"],
            [
                str(cdata.get('size', 0)), 
                f"{cdata.get('avg_age', 0):.1f}", 
                f"${cdata.get('avg_income', 0):.1f}k", 
                f"{cdata.get('avg_score', 0):.1f}"
            ]
        ]
        stat_t = Table(c_stats, colWidths=[1.5*inch]*4)
        stat_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EEF2FF")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#4F8CFF")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#E5E7EB"))
        ]))
        Story.append(stat_t)
        Story.append(Spacer(1, 0.15 * inch))
        
        # Points Table
        pts = cdata.get('points', [])
        if pts:
            # Table Header
            table_data = [["Gender", "Age", "Annual Income (k$)", "Spending Score"]]
            for pt in pts:
                table_data.append([
                    str(pt.get('gender', '')), 
                    str(pt.get('age', '')), 
                    f"${float(pt.get('x', 0)):.1f}k", 
                    str(pt.get('y', ''))
                ])
                
            pt_table = Table(table_data, colWidths=[1.5*inch]*4)
            pt_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F9FAFB")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#4B5563")),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#FCFCFC")])
            ]))
            Story.append(pt_table)
            
            note_style = ParagraphStyle('Note', parent=normal_style, fontSize=8, textColor=colors.grey, fontName='Helvetica-Oblique')
            Story.append(Spacer(1, 0.05 * inch))
            Story.append(Paragraph(f"* Showing first {len(pts)} records of {cdata.get('size', 0)} total.", note_style))
        
        Story.append(Spacer(1, 0.3 * inch))

    doc.build(Story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    buffer.seek(0)
    return buffer
