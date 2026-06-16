import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_bank_statement(filename="data/sample_corporate_statement.pdf"):
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Page setup
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom Styling
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=20, leading=24, textColor=colors.HexColor('#1A365D'), spaceAfter=6)
    meta_style = ParagraphStyle('MetaText', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#4A5568'))
    header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=9, leading=11, textColor=colors.white, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#2D3748'))
    
    # 1. Header Section
    story.append(Paragraph("APEX GLOBAL LOGISTICS SOLUTIONS PVT LTD", title_style))
    story.append(Paragraph("Corporate Banking Account Statement | Account Number: 910020048817263", meta_style))
    story.append(Paragraph("Statement Period: 01-May-2026 to 31-May-2026 | Currency: INR (₹)", meta_style))
    story.append(Spacer(1, 15))
    
    # 2. Financial Summary Cards
    summary_data = [
        [Paragraph("<b>Opening Balance (01-May):</b>", cell_style), Paragraph("₹ 14,85,200.50", cell_style),
         Paragraph("<b>Total Credits (Deposits):</b>", cell_style), Paragraph("₹ 42,10,000.00", cell_style)],
        [Paragraph("<b>Closing Balance (31-May):</b>", cell_style), Paragraph("₹ 21,12,050.50", cell_style),
         Paragraph("<b>Total Debits (Withdrawals):</b>", cell_style), Paragraph("₹ 35,83,150.00", cell_style)]
    ]
    summary_table = Table(summary_data, colWidths=[150, 120, 140, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # 3. Comprehensive High-Density Transaction Ledger
    story.append(Paragraph("<b>Detailed Transaction History</b>", ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#2B6CB0'), spaceAfter=8)))
    
    raw_txs = [
        ("02-May-2026", "NFT-INBOUND / STAR ENTERPRISES / INV-8821", "2,50,000.00", "0.00", "17,35,200.50"),
        ("04-May-2026", "CHQ-OUTBOUND / TAX AUTHORITY / GST-Q1", "0.00", "4,20,000.00", "13,15,200.50"),
        ("05-May-2026", "DIRECT DEBIT / HDFC_BANK_CORP_LOAN_EMI", "0.00", "1,85,000.00", "11,30,200.50"),
        ("08-May-2026", "CMS-COLLECTION / RECURRING ACCOUNTS RECV", "14,20,000.00", "0.00", "25,50,200.50"),
        ("12-May-2026", "IBFT-OUT / BULK SALARY DISBURSEMENT-MAY", "0.00", "18,40,000.00", "7,10,200.50"),
        ("15-May-2026", "NFT-INBOUND / ZEPHYR HOLDINGS PVT LTD", "8,90,000.00", "0.00", "16,00,200.50"),
        ("18-May-2026", "RAW MAT / VENDOR PAY / STEEL-SUPPLY-CORP", "0.00", "6,15,000.00", "9,85,200.50"),
        ("20-May-2026", "INT-RECEIVED / FIXED DEPOSIT REVENUE", "45,000.00", "0.00", "10,30,200.50"),
        ("22-May-2026", "CHQ-OUTBOUND / WAREHOUSE LEASE MANAGEMENT", "0.00", "2,50,000.00", "7,80,200.50"),
        ("25-May-2026", "CMS-COLLECTION / PAYU_GATEWAY_SETTLEMENT", "16,05,000.00", "0.00", "23,85,200.50"),
        ("27-May-2026", "DIRECT DEBIT / FUEL_CORP_FLEET_OPERATIONS", "0.00", "1,23,150.00", "22,62,050.50"),
        ("30-May-2026", "BANK CHARGES / CC_PROCESSING_FEE", "0.00", "1,50,000.00", "21,12,050.50")
    ]
    
    # Building Table Headers
    tx_table_data = [[
        Paragraph("<b>Date</b>", header_style),
        Paragraph("<b>Transaction Description</b>", header_style),
        Paragraph("<b>Credit (Deposit)</b>", header_style),
        Paragraph("<b>Debit (Withdrawal)</b>", header_style),
        Paragraph("<b>Running Balance</b>", header_style)
    ]]
    
    # Append Rows
    for date, desc, cr, dr, bal in raw_txs:
        tx_table_data.append([
            Paragraph(date, cell_style),
            Paragraph(desc, cell_style),
            Paragraph(f"₹ {cr}" if cr != "0.00" else "-", cell_style),
            Paragraph(f"₹ {dr}" if dr != "0.00" else "-", cell_style),
            Paragraph(f"₹ {bal}", cell_style)
        ])
        
    tx_table = Table(tx_table_data, colWidths=[70, 210, 85, 85, 90])
    tx_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A365D')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,1), (-1,-1), 6),
    ]))
    
    story.append(tx_table)
    
    # Building PDF
    doc.build(story)
    print(f" Success! Test statement generated perfectly at: {filename}")

if __name__ == "__main__":
    create_bank_statement()