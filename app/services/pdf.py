"""Generación de PDF con reportlab (Python puro, compatible con Vercel)."""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .. import config

NAVY, BLUE, PURPLE = colors.HexColor("#0b1530"), colors.HexColor("#3b82f6"), colors.HexColor("#7c3aed")


def build_pdf(titulo, subtitulo, headers, rows, totales=None, extra=None):
    """rows: lista de listas de str. totales: lista de (etiqueta, valor). extra: lista de bloques [(titulo, headers, rows)]."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.8 * cm, title=f"{config.APP_NAME} - {titulo}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=20, alignment=0)
    sub = ParagraphStyle("sub", parent=ss["Normal"], textColor=colors.HexColor("#475569"), fontSize=9.5, leading=13)
    h2 = ParagraphStyle("h2", parent=ss["Heading3"], textColor=PURPLE)
    gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    story = [Paragraph(config.APP_NAME, ParagraphStyle("brand", parent=sub, textColor=BLUE, fontSize=11)),
             Paragraph(titulo, h1),
             Paragraph(f"{subtitulo}<br/>Fecha de generación: {gen}", sub), Spacer(1, 10)]

    def tabla(hd, rw):
        data = [hd] + (rw or [["Sin datos"] + [""] * (len(hd) - 1)])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2ff")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        return t

    story.append(tabla(headers, rows))
    for tit, hd, rw in (extra or []):
        story += [Spacer(1, 14), Paragraph(tit, h2), tabla(hd, rw)]
    if totales:
        story.append(Spacer(1, 12))
        tt = Table([[a, b] for a, b in totales], colWidths=[7 * cm, 5 * cm], hAlign="RIGHT")
        tt.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10),
                                ("LINEABOVE", (0, 0), (-1, 0), 1, PURPLE), ("ALIGN", (1, 0), (1, -1), "RIGHT")]))
        story.append(tt)

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(1.5 * cm, 1 * cm, config.COPYRIGHT)
        canvas.drawRightString(landscape(A4)[0] - 1.5 * cm, 1 * cm, f"Página {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
