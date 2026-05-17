"""
蒋万安 OSINT 政治人物分析报告 v1.8 → PDF 转换器
中文期刊论文格式（使用 reportlab）
"""
import re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus.flowables import KeepTogether

# ── Windows 中文字体注册 ──────────────────────────────
FONT_DIR = r"C:\Windows\Fonts"
FONT_MAP = {
    "宋体":   "simsun.ttc",
    "黑体":   "simhei.ttf",
    "楷体":   "simkai.ttf",
    "仿宋":   "simfang.ttf",
    "Courier": "cour.ttf",
}
for name, fname in FONT_MAP.items():
    fpath = os.path.join(FONT_DIR, fname)
    if os.path.exists(fpath):
        try:
            pdfmetrics.registerFont(TTFont(name, fpath))
            print(f"  ✅ 注册字体: {name} → {fname}")
        except Exception as e:
            print(f"  ⚠️  注册失败 {name}: {e}")
    else:
        print(f"  ❌ 字体文件不存在: {fpath}")

# ── 页面设置 ─────────────────────────────────────────
PAGESIZE = A4
MARGIN = 2.54 * cm

# ── 样式定义 ──────────────────────────────────────────
def make_styles():
    s = {}
    s["title"] = ParagraphStyle(
        "title", fontName="黑体", fontSize=20,
        leading=28, alignment=TA_CENTER,
        spaceAfter=24, spaceBefore=72,
        textColor=colors.black,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", fontName="楷体", fontSize=14,
        leading=20, alignment=TA_CENTER,
        spaceAfter=48,
    )
    s["meta_key"] = ParagraphStyle(
        "meta_key", fontName="楷体", fontSize=11,
        leading=18, alignment=TA_LEFT,
        spaceAfter=3,
    )
    s["meta_val"] = ParagraphStyle(
        "meta_val", fontName="宋体", fontSize=11,
        leading=18, alignment=TA_LEFT,
        spaceAfter=3,
    )
    s["h1"] = ParagraphStyle(
        "h1", fontName="黑体", fontSize=15,
        leading=22, alignment=TA_CENTER,
        spaceBefore=24, spaceAfter=10,
        textColor=colors.black,
    )
    s["h2"] = ParagraphStyle(
        "h2", fontName="黑体", fontSize=13,
        leading=20, alignment=TA_LEFT,
        spaceBefore=16, spaceAfter=8,
        textColor=colors.black,
    )
    s["h3"] = ParagraphStyle(
        "h3", fontName="楷体", fontSize=12,
        leading=18, alignment=TA_LEFT,
        spaceBefore=10, spaceAfter=6,
        textColor=colors.black,
    )
    s["body"] = ParagraphStyle(
        "body", fontName="宋体", fontSize=11,
        leading=18, alignment=TA_JUSTIFY,
        spaceAfter=8,
        firstLineIndent=22,
    )
    s["quote"] = ParagraphStyle(
        "quote", fontName="楷体", fontSize=10,
        leading=16, alignment=TA_LEFT,
        spaceBefore=4, spaceAfter=4,
        leftIndent=16,
    )
    s["table_hdr"] = ParagraphStyle(
        "table_hdr", fontName="宋体", fontSize=9,
        leading=14, alignment=TA_CENTER,
        textColor=colors.white,
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell", fontName="宋体", fontSize=8.5,
        leading=13, alignment=TA_LEFT,
    )
    s["ref"] = ParagraphStyle(
        "ref", fontName="宋体", fontSize=9,
        leading=14, alignment=TA_LEFT,
        spaceAfter=4,
    )
    return s

# ── markdown parser ────────────────────────────────────
def parse_inline(text):
    """处理 markdown 加粗/斜体/纯文本"""
    parts = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', text)
    result = []
    for p in parts:
        if p.startswith('**') and p.endswith('**'):
            result.append(('bold', p[2:-2]))
        elif p.startswith('*') and p.endswith('*'):
            result.append(('italic', p[1:-1]))
        else:
            result.append(('normal', p))
    return result

def md_to_paragraphs(text, style_name, styles):
    """将纯 markdown 文本转为 Paragraph list"""
    style = styles[style_name]
    lines = text.split('\n')
    paras = []
    for line in lines:
        line = line.strip()
        if not line:
            paras.append(Spacer(1, 4))
            continue
        inlines = parse_inline(line)
        runs = []
        for kind, txt in inlines:
            if kind == 'bold':
                runs.append(('bold', txt))
            elif kind == 'italic':
                runs.append(('italic', txt))
            else:
                runs.append(('normal', txt))
        # build paragraph from runs (simplified: use one style per para)
        para = Paragraph(line, style)
        paras.append(para)
    return paras

def process_file(filepath, styles):
    """将 markdown 文件转为 reportlab Story"""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    story = []
    lines = content.split('\n')
    i = 0
    in_table = False
    tbl_hdr = []
    tbl_rows = []

    def flush_table():
        nonlocal tbl_hdr, tbl_rows, in_table
        if not tbl_hdr or not tbl_rows:
            tbl_hdr = []
            tbl_rows = []
            in_table = False
            return
        data = [tbl_hdr] + tbl_rows
        col_count = len(tbl_hdr)
        col_w = (PAGESIZE[0] - 2*MARGIN) / col_count
        tw = [col_w] * col_count
        t = Table(data, colWidths=tw, repeatRows=1)
        ts = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2F5496')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), '宋体'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,1), (-1,-1), '宋体'),
            ('FONTSIZE', (0,1), (-1,-1), 8.5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#D6E4F0'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ])
        t.setStyle(ts)
        story.append(t)
        story.append(Spacer(1, 10))
        tbl_hdr = []
        tbl_rows = []
        in_table = False

    while i < len(lines):
        line = lines[i].rstrip()
        i += 1

        # 跳过空行
        if not line.strip():
            if in_table:
                pass
            else:
                story.append(Spacer(1, 6))
            continue

        # 跳过 markdown 标题行（单独处理）
        if re.match(r'^#{1,3}\s+\S', line):
            # 第一行 # 标题单独处理
            if line.startswith('# 蒋万安 OSINT'):
                continue
            continue

        # 跳过第一页元信息块（在后面处理）
        if line.startswith('**报告版本**') and 'OSINT' in line:
            meta_block = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith('#'):
                meta_block.append(lines[i].rstrip())
                i += 1
            # 标题页
            story.append(Paragraph("蒋万安 OSINT 政治人物全景分析报告", styles["title"]))
            story.append(Paragraph("（OSINT V7.2 全景分析体系）", styles["subtitle"]))
            story.append(Spacer(1, 16))
            for ml in meta_block:
                m = re.match(r'\*\*(.+?)\*\*[:：]\s*(.+)', ml.strip())
                if m:
                    k, v = m.groups()
                    story.append(Paragraph(
                        f"<b>{k.strip()}：</b> {v.strip()}",
                        styles["meta_key"]
                    ))
            story.append(PageBreak())
            continue

        # 一级标题 ## ■ ■ ■
        if line.startswith('## '):
            if in_table:
                flush_table()
            text = line[3:].strip()
            story.append(Spacer(1, 12))
            story.append(Paragraph(text, styles["h1"]))
            continue

        # 二级标题 ### ■ ■
        if line.startswith('### '):
            if in_table:
                flush_table()
            text = line[4:].strip()
            story.append(Spacer(1, 8))
            story.append(Paragraph(text, styles["h2"]))
            continue

        # 引用块
        if line.startswith('>'):
            text = line[1:].strip()
            story.append(Paragraph(text, styles["quote"]))
            continue

        # 表格行
        if line.startswith('|'):
            if '---' in line or re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not in_table:
                in_table = True
                tbl_hdr = cells
            else:
                tbl_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()

        # 普通正文
        if not line.strip():
            continue

        # 处理行内格式（加粗/斜体）
        inlines = parse_inline(line)
        runs = []
        for kind, txt in inlines:
            font = "宋体"
            bold = kind == 'bold'
            italic = kind == 'italic'
            if bold:
                runs.append(f"<b>{txt}</b>")
            elif italic:
                runs.append(f"<i>{txt}</i>")
            else:
                runs.append(txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        full_text = ''.join(runs)
        story.append(Paragraph(full_text, styles["body"]))

    if in_table:
        flush_table()

    return story

# ── 页眉页脚 ──────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # 页眉
    canvas.setFont("宋体", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(MARGIN, PAGESIZE[1] - 1.2*cm,
                      "蒋万安 OSINT 政治人物全景分析报告 V1.8 | OSINT V7.2 | 内部研究参考")
    canvas.drawRightString(PAGESIZE[0] - MARGIN, PAGESIZE[1] - 1.2*cm,
                           "未经授权禁止引用")
    # 页脚
    canvas.drawCentredString(PAGESIZE[0]/2, 1.2*cm, f"- {doc.page} -")
    canvas.restoreState()

# ── 主程序 ────────────────────────────────────────────
def main():
    src = r"D:\aicoding\news-monitor\people\output\蒋万安\蒋万安_政治人物分析报告_v1.8.md"
    out_pdf = r"D:\aicoding\news-monitor\people\output\蒋万安\蒋万安_政治人物分析报告_v1.8.pdf"

    print("📖 读取 markdown...")
    styles = make_styles()

    print("⚙️ 生成 PDF...")
    doc = SimpleDocTemplate(
        out_pdf,
        pagesize=PAGESIZE,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="蒋万安 OSINT 政治人物全景分析报告",
        author="OSINT V7.2 分析框架",
        subject="台湾政治人物分析",
    )

    story = process_file(src, styles)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    size = os.path.getsize(out_pdf)
    print(f"✅ PDF 已保存：{out_pdf}")
    print(f"   文件大小：{size:,} bytes ({size/1024:.1f} KB)")

if __name__ == '__main__':
    main()
