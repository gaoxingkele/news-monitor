"""
政治人物分析报告 v1.8 → PDF
中文期刊格式：仿宋GB2312 四号 / 1.2行距 / 首行缩进 / 标题层级醒目
"""
import re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

FONT_DIR = r"C:\Windows\Fonts"
for fname, alias in [("simsun.ttc","宋体"),("simhei.ttf","黑体"),
                      ("simkai.ttf","楷体"),("simfang.ttf","仿宋")]:
    path = os.path.join(FONT_DIR, fname)
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(alias, path))
            print(f"  ✅ {alias}")
        except Exception as e:
            print(f"  ⚠️  {alias}: {e}")

BODY  = "仿宋"
HEAD  = "黑体"
SZ_BODY  = 14    # 四号
SZ_H1    = 18
SZ_H2    = 16
SZ_H3    = 14
SZ_TBL_H = 10
SZ_TBL_D = 9
W = A4[0]
H = A4[1]
MG = 3.18 * cm
INDENT = 0.74 * cm   # 首行缩进2字符

def S(name, font, size, bold=False, align=TA_JUSTIFY,
      sb=0, sa=6, lh=1.2, indent=None, color=colors.black, italic=False):
    s = ParagraphStyle(name, fontName=font, fontSize=size,
                       leading=size * lh,
                       alignment=align,
                       spaceBefore=sb, spaceAfter=sa,
                       textColor=color, italic=italic)
    if indent is not None:
        s.firstLineIndent = indent
    return s

STYLES = {
    "title":   S("title",   HEAD, 22, bold=True,  align=TA_CENTER,  sb=72, sa=24),
    "sub":     S("sub",     HEAD, 14, bold=True,  align=TA_CENTER,  sb=0,  sa=48),
    "meta":    S("meta",    BODY, 12, bold=False, align=TA_LEFT,    sb=2,  sa=2),
    "h1":      S("h1",      HEAD, SZ_H1, bold=True,  align=TA_CENTER,  sb=24, sa=12),
    "h2":      S("h2",      HEAD, SZ_H2, bold=True,  align=TA_LEFT,    sb=18, sa=8,  color=colors.HexColor('#000080')),
    "h3":      S("h3",      HEAD, SZ_H3, bold=True,  align=TA_LEFT,    sb=12, sa=6,  color=colors.HexColor('#505050')),
    "body":    S("body",    BODY, SZ_BODY, align=TA_JUSTIFY, sb=0,  sa=6, lh=1.2, indent=INDENT),
    "quote":   S("quote",   BODY, 12, italic=True, align=TA_JUSTIFY, sb=4, sa=4, indent=1*cm),
    "th":      S("th",      BODY, SZ_TBL_H, bold=True, align=TA_CENTER, color=colors.white),
    "td":      S("td",      BODY, SZ_TBL_D, align=TA_LEFT),
}

def strip_markdown(text):
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s*', '', text)
    return text

def md_bold_to_html(text):
    """保留内联 **bold** → ReportLab <b>…</b>；清理其他 md 符号。"""
    if text is None:
        return ''
    # 先 escape HTML 特殊字符
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # **bold** → <b>bold</b>
    text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
    # *italic* → <i>italic</i>（单 *，避免影响）
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
    # 去掉行首 #
    text = re.sub(r'^#{1,6}\s*', '', text)
    return text

def clean_cite(text):
    """只清除引用格式标注，保留其他括号内容"""
    text = re.sub(r'\[(?:A|B|C|D)级\s*,\s*[^]]{2,60}\]', '', text)
    text = re.sub(r'\[(?:\d{4}年?|\d+)\]', '', text)
    return text.strip()

def process_file(src, person_name="政治人物"):
    with open(src, encoding='utf-8') as f:
        content = f.read()

    story = []
    lines = content.split('\n')
    i = 0
    in_tbl = False
    tbl_hdr, tbl_rows = [], []

    def flush_tbl():
        nonlocal tbl_hdr, tbl_rows, in_tbl
        if not tbl_hdr or not tbl_rows:
            tbl_hdr, tbl_rows, in_tbl = [], [], False
            return
        aw = (W - 2*MG) / len(tbl_hdr)
        # 表格单元以 Paragraph 包裹，支持内联 <b>bold</b>
        def _cell(text, style_name):
            return Paragraph(md_bold_to_html(text or ''), STYLES[style_name])
        data = [[_cell(c, 'th') for c in tbl_hdr]] + \
               [[_cell(c, 'td') for c in row] for row in tbl_rows]
        t = Table(data, colWidths=[aw]*len(tbl_hdr), repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,0), colors.HexColor('#2F5496')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), HEAD),
            ('FONTSIZE',    (0,0), (-1,0), SZ_TBL_H),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME',    (0,1), (-1,-1), BODY),
            ('FONTSIZE',    (0,1), (-1,-1), SZ_TBL_D),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [colors.HexColor('#D6E4F0'), colors.white]),
            ('GRID',        (0,0), (-1,-1), 0.5, colors.grey),
            ('TOPPADDING',  (0,0), (-1,-1), 4),
            ('BOTTOMPADDING',(0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING',(0,0), (-1,-1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))
        tbl_hdr, tbl_rows, in_tbl = [], [], False

    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        if not line.strip():
            continue

        # 版本头 → 标题页
        if line.startswith('**报告版本**') and 'OSINT' in line:
            meta = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith('#'):
                meta.append(lines[i].rstrip())
                i += 1
            story.append(Paragraph(f"{person_name} OSINT 政治人物全景分析报告", STYLES["title"]))
            story.append(Paragraph("（OSINT V7.2 全景分析体系）", STYLES["sub"]))
            story.append(Spacer(1, 12))
            for ml in meta:
                m = re.match(r'\*\*(.+?)\*\*[:：]\s*(.+)', ml.strip())
                if m:
                    k, v = m.groups()
                    story.append(Paragraph(
                        f"<b>{k.strip()}：</b> {v.strip()}", STYLES["meta"]))
            story.append(PageBreak())
            continue

        # 跳过独立的 markdown 标题行标记（## 已在 h1/h2/h3 中处理）
        if re.match(r'^#{1,3}\s+[^\s]', line) and not line.startswith('##'):
            continue

        # 一级标题 ## ■ ■ ■
        if line.startswith('## '):
            if in_tbl: flush_tbl()
            text = strip_markdown(line[3:].strip())
            story.append(Spacer(1, 12))
            story.append(Paragraph(text, STYLES["h1"]))
            story.append(HRFlowable(width="60%", thickness=1,
                                    color=colors.HexColor('#2F5496'),
                                    spaceAfter=12, spaceBefore=0))
            continue

        # 二级标题 ### ■ ■ / ●
        if line.startswith('### '):
            if in_tbl: flush_tbl()
            text = strip_markdown(line[4:].strip())
            if text.startswith('§') or any(k in text for k in ['模块','矩阵','量化','核查','总表','模式','交叉','分级','合规']):
                story.append(Spacer(1, 8))
                story.append(Paragraph("● " + text, STYLES["h3"]))
            else:
                story.append(Spacer(1, 10))
                story.append(Paragraph("■ " + text, STYLES["h2"]))
            continue

        # 引用块
        if line.startswith('>'):
            story.append(Paragraph(strip_markdown(line[1:].strip()), STYLES["quote"]))
            continue

        # 表格
        if line.startswith('|'):
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not in_tbl:
                in_tbl = True
                tbl_hdr = cells
            else:
                tbl_rows.append(cells)
            continue
        else:
            if in_tbl:
                flush_tbl()

        # 正文段落
        text = clean_cite(line)
        text = md_bold_to_html(text)
        if text:
            story.append(Paragraph(text, STYLES["body"]))

    if in_tbl:
        flush_tbl()
    return story


def make_on_page(person_name):
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("仿宋", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(MG, H - 1.2*cm,
                         f"{person_name} OSINT 政治人物全景分析报告 V1.8 | OSINT V7.2 | 内部研究参考")
        canvas.drawRightString(W - MG, H - 1.2*cm, "未经授权禁止引用")
        canvas.drawCentredString(W/2, 1.2*cm, f"— {doc.page} —")
        canvas.restoreState()
    return on_page

def main(src=None, out=None):
    if src is None:
        src = r"D:\aicoding\news-monitor\people\output\李四川\李四川_政治人物分析报告_v1.8.md"
    if out is None:
        out = os.path.splitext(src)[0] + ".pdf"
    print("📖 读取 markdown...")
    import re as RE
    with open(src, encoding="utf-8") as f:
        first = f.readline().strip()
    m = RE.match(r"^#\s+([^\s]+)\s+OSINT", first)
    person_name = m.group(1) if m else "政治人物"
    print(f"   检测到人物：{person_name}")
    story = process_file(src, person_name)
    print("⚙️ 生成 PDF...")
    on_fn = make_on_page(person_name)
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=MG, rightMargin=MG,
                            topMargin=MG, bottomMargin=MG,
                            title=f"{person_name} OSINT 政治人物全景分析报告",
                            author="OSINT V7.2", subject="台湾政治人物分析")
    doc.build(story, onFirstPage=on_fn, onLaterPages=on_fn)
    sz = os.path.getsize(out)
    print(f"✅ PDF 已保存：{out}")
    print(f"   大小：{sz:,} bytes ({sz/1024:.1f} KB)")

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", help="source markdown path")
    ap.add_argument("--out", help="output pdf path")
    args = ap.parse_args()
    main(src=args.src, out=args.out)
