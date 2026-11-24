import sys, io
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, PageBreak, Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter
from content import CHAPTERS

SRC, OUT = sys.argv[1], sys.argv[2]
FD = "/usr/share/fonts/truetype/crosextra/"
for n, f in [("Carlito","Regular"),("Carlito-Bold","Bold"),("Carlito-Italic","Italic"),("Carlito-BoldItalic","BoldItalic")]:
    pdfmetrics.registerFont(TTFont(n, FD+f"Carlito-{f}.ttf"))
addMapping("Carlito",0,0,"Carlito"); addMapping("Carlito",1,0,"Carlito-Bold")
addMapping("Carlito",0,1,"Carlito-Italic"); addMapping("Carlito",1,1,"Carlito-BoldItalic")

BLUE = colors.Color(.121569,.227451,.372549)
GREY = colors.Color(.466667,.466667,.466667)
LIGHT = colors.Color(.933333,.94902,.972549)
# stili ricavati dal PDF originale (posizioni nei content stream)
chap = ParagraphStyle("chap", fontName="Carlito-Bold", fontSize=15, leading=19, textColor=colors.white,
                      backColor=BLUE, borderPadding=(5,6,5,6), spaceAfter=12)
h2 = ParagraphStyle("h2", fontName="Carlito-Bold", fontSize=12.5, leading=16, textColor=BLUE, spaceBefore=10, spaceAfter=4)
atl = ParagraphStyle("atl", fontName="Carlito-Italic", fontSize=9, leading=11, textColor=GREY, spaceAfter=4)
body = ParagraphStyle("body", fontName="Carlito", fontSize=10.5, leading=14.2, alignment=TA_JUSTIFY, spaceAfter=5)
link = ParagraphStyle("link", parent=body, alignment=0, backColor=LIGHT, borderPadding=(4,5,4,5), spaceAfter=6)
ftitle = ParagraphStyle("ftitle", fontName="Carlito-Bold", fontSize=10.5, leading=13.5, textColor=BLUE)
fitem = ParagraphStyle("fitem", parent=body, fontSize=10, leading=13, spaceAfter=0, leftIndent=14, bulletIndent=0, bulletFontName="Carlito-Bold")

W = A4[0] - 2*56.69291
def frasi(items):
    rows = [[Paragraph("Le tre frasi da esame.", ftitle)]] + \
           [[Paragraph(t, fitem, bulletText=f"{i}.")] for i, t in enumerate(items, 1)]
    t = Table(rows, colWidths=[W])
    t.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.75,BLUE),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1),
        ("TOPPADDING",(0,0),(-1,0),4),("BOTTOMPADDING",(0,-1),(-1,-1),5)]))
    t.spaceBefore, t.spaceAfter = 2, 5
    return t

story = []
for ci, (title, sections, links) in enumerate(CHAPTERS):
    if ci: story.append(PageBreak())
    story.append(Paragraph(title, chap))
    for head, atlante, summary, items in sections:
        story.append(Paragraph(head, h2))
        if atlante: story.append(Paragraph(atlante, atl))
        story.append(Paragraph("<b>Riassunto concettuale.</b> " + summary, body))
        story.append(frasi(items))
    for l in links: story.append(Paragraph(l, link))

buf = io.BytesIO()
doc = BaseDocTemplate(buf, pagesize=A4)
frame = Frame(56.69291, 56.69291, W, A4[1]-51.02362-56.69291, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate("p", [frame])])
doc.build(story)
new = PdfReader(io.BytesIO(buf.getvalue()))
src = PdfReader(SRC)
FIRST, LAST = 10, 13          # pagine sostituite (1-based)
n_new = len(new.pages)
shift = n_new - (LAST - FIRST + 1)
print("pagine nuove:", n_new, "shift:", shift)

def stamp(num):
    """Numeri di pagina come nell'originale: Helvetica 10, in alto, in basso al centro e a destra."""
    b = io.BytesIO(); c = canvas.Canvas(b, pagesize=A4); c.setFont("Helvetica", 10)
    s = str(num); w = pdfmetrics.stringWidth(s, "Helvetica", 10)
    c.drawString(A4[0]/2 - w/2, 809.8898, s); c.drawString(A4[0]/2 - w/2, 30, s)
    c.drawString(572.8356 - w, 417.61155, s); c.save()
    return PdfReader(io.BytesIO(b.getvalue())).pages[0]

import re
from pypdf.generic import ContentStream, NameObject
def renumber(page, old, newn):
    data = page.get_contents().get_data().decode("latin1")
    oldhex = str(old).encode().hex(); s = str(newn)
    w_old = pdfmetrics.stringWidth(str(old),"Helvetica",10); w_new = pdfmetrics.stringWidth(s,"Helvetica",10)
    def fix(m):
        x = float(m.group(1)); y = m.group(2)
        x = x + (w_old - w_new)/2 if abs(float(y)-417.61155) > 1 else x + (w_old - w_new)
        return f"1 0 0 1 {x:.4f} {y} Tm\n/helv 10 Tf [<{s.encode().hex()}>]TJ"
    data2, k = re.subn(r"1 0 0 1 ([\d.]+) ([\d.]+) Tm\n/helv 10 Tf \[<%s>\]TJ" % oldhex, fix, data)
    assert k == 3, (old, k)
    from pypdf.generic import DecodedStreamObject
    st = DecodedStreamObject(); st.set_data(data2.encode("latin1"))
    page.replace_contents(st)

w = PdfWriter()
for i in range(FIRST-1): w.add_page(src.pages[i])
for j, p in enumerate(new.pages):
    p.merge_page(stamp(FIRST + j)); w.add_page(p)
for i in range(LAST, len(src.pages)):
    p = w.add_page(src.pages[i])
    if shift: renumber(p, i+1, i+1+shift)
w.add_metadata(src.metadata)
with open(OUT, "wb") as f: w.write(f)
print("scritto", OUT, len(w.pages), "pagine")
