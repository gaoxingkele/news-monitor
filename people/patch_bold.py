"""
给 md 政治人物报告批量添加 **bold** 语法：
人名、政党派系、关键事件、分析框架、MBTI 类型、证据等级。

不修改已在 **...** 内的片段，不修改表格分隔符行、不修改代码块。
"""
import re
import sys
import os
import argparse


PERSONS = [
    # 已建档主要人物（长的放前面优先）
    "蒋万安", "侯友宜", "李四川", "苏巧慧", "萧旭岑", "萧美琴",
    "卢秀燕", "陈其迈", "张善政", "黄伟哲", "郑丽文", "黄国昌",
    "江启臣", "郑丽君", "林俊宪", "赖瑞隆",
    # 台湾政坛要角
    "赖清德", "蔡英文", "马英九", "陈水扁", "苏贞昌", "朱立伦",
    "韩国瑜", "柯文哲", "郝龙斌", "罗智强", "连战", "王金平",
    "陈菊", "林佳龙", "郑运鹏", "卓荣泰",
    # 绿营人物
    "陈亭妃", "邱议莹", "许智杰", "林岱桦", "王定宇", "陈唐山",
    "吴思瑶", "王世坚", "沈伯洋", "林右昌", "高嘉瑜", "吴怡农", "苗博雅",
    "何欣纯", "王美惠", "王义川", "何志伟", "张惇涵", "黄世杰",
    # 蓝营人物
    "谢龙介", "陈以信", "柯志恩", "杨琼璎", "洪孟楷", "牛煦庭",
    "颜宽恒", "麦玉珍", "傅崐萁", "陈昭姿", "锺东锦",
    "王惠美", "张丽善", "徐榛蔚", "杨文科", "蔡其昌",
    # 海外与学术
    "习近平", "宋涛", "王沪宁", "达克沃思", "苏利文", "蓬佩奥",
    "坎贝尔", "格里菲思", "图根哈特", "蕾斯曼", "麦卡锡", "佩洛西",
    "拜登", "特朗普", "陈文茜", "张荣恭", "李乾龙", "季麟连",
    "戴遐龄", "王光慈", "金溥聪", "蔡壁如", "陈哲男", "刘盛良",
    "赵少康", "周锡玮", "孙大千", "李永萍", "高虹安",
    "高思博", "林昶佐", "陈信瑜", "陈玉珍",
]

PARTIES_FACTIONS = [
    "中国国民党", "民主进步党", "台湾民众党", "时代力量",
    "国民党", "民进党", "民众党",
    "新潮流系", "新境界系", "英系", "正国会",
    "马家军", "连战系", "王金平系", "黄复兴党部",
    "新苏系", "苏系", "赖系",
    "海外台独联盟",
    "KMT", "DPP", "TPP",
]

EVENTS = [
    "九二共识", "一中各表", "太阳花运动", "野百合学运",
    "马习会", "蔡麦会", "大罢免", "郑丽文路线",
    "2026新北市长选战", "2024总统大选", "2020总统大选",
    "2026九合一", "反服贸", "白晓燕案", "京华城案",
    "台海危机", "陈哲男SOGO案", "SOGO案",
    "两年条款",
]

FRAMEWORKS = [
    "Hermann LTA", "Hermann领导特质分析", "Hermann 领导特质分析",
    "George操作码", "George 操作码",
    "Winter动机编码", "Winter 动机编码",
    "Barber类型学", "Barber 类型学", "Barber人格类型学",
    "MBTI 认知功能", "MBTI认知功能", "认知功能栈",
    "SBP 战略行为模式", "SBP战略行为模式", "战略行为模式",
    "Grip Theory", "Grip 理论",
    "Fi grip", "Se grip", "Ne grip", "Ti grip", "Fe grip", "Te grip",
    "Fi Grip", "Se Grip", "Ne Grip", "Ti Grip",
    "networkx 量化", "networkx量化",
    "贝叶斯三步", "三时期前后对照",
    "OSINT V7.3", "OSINT V7.2",
]

MBTI_TYPES = [
    "ENTJ", "INTJ", "ESTJ", "ISTJ",
    "INFJ", "ISFJ", "ENFJ", "ESFJ",
    "ENTP", "INTP", "ESTP", "ISTP",
    "ENFP", "INFP",
    "Active-Positive", "Active-Negative",
    "Passive-Positive", "Passive-Negative",
]

EVIDENCE_BRACKETS = [
    r"\[E-Hermann LTA\]", r"\[E-George OpCode\]",
    r"\[E-Hermann\]", r"\[E-George\]", r"\[E-Winter\]", r"\[E-Barber\]",
    r"\[E-MBTI\]", r"\[E-Composite\]", r"\[E-Source\]",
    r"\[A/B 级来源\]", r"\[A/B/C 级来源\]",
    r"\[A 级来源\]", r"\[B 级来源\]", r"\[C 级来源\]", r"\[D 级来源\]", r"\[E 级推断\]",
    r"\[A 级\]", r"\[B 级\]", r"\[C 级\]", r"\[D 级\]", r"\[E 级\]",
    r"\[A/B 级\]", r"\[B/C 级\]", r"\[B/E 级\]", r"\[C/D 级\]", r"\[A/B/C/E 级综合\]",
    r"\[A级\]", r"\[B级\]", r"\[C级\]", r"\[D级\]", r"\[E级\]",
]


def build_pattern(terms, as_regex=False):
    """按长度从大到小排序，组装为 OR 正则。"""
    if as_regex:
        sorted_terms = sorted(terms, key=lambda s: -len(s))
        return re.compile("|".join(sorted_terms))
    sorted_terms = sorted(set(terms), key=lambda s: -len(s))
    escaped = [re.escape(t) for t in sorted_terms]
    return re.compile("|".join(escaped))


def apply_bold_outside_existing(text, pattern):
    """在 text 中对未加粗片段（不在 **...** 内）应用 pattern 并用 **...** 包裹匹配结果。"""
    if not text or "**" not in text and not any(True for _ in pattern.finditer(text)):
        return pattern.sub(lambda m: f"**{m.group(0)}**", text)

    # 按 **...** 拆段：偶数位为普通文本，奇数位为已加粗（含两端标记）
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    out = []
    for idx, p in enumerate(parts):
        if idx % 2 == 1:
            out.append(p)
        else:
            out.append(pattern.sub(lambda m: f"**{m.group(0)}**", p))
    return "".join(out)


def should_skip_line(line):
    """是否跳过此行（不加粗）。"""
    s = line.strip()
    if not s:
        return True
    if s.startswith("|-") or re.match(r"^\|[\s\-:|]+\|$", s):
        return True  # 表格分隔符
    if s.startswith("```"):
        return True  # 代码块边界
    if s.startswith("http://") or s.startswith("https://"):
        return True
    return False


def patch_file(path, dry_run=False):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # 一次性构建所有 pattern（名字类用非正则 escape，证据括号已是正则）
    person_pat = build_pattern(PERSONS)
    party_pat = build_pattern(PARTIES_FACTIONS)
    event_pat = build_pattern(EVENTS)
    frame_pat = build_pattern(FRAMEWORKS)
    mbti_pat = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in sorted(MBTI_TYPES, key=lambda x: -len(x))) + r")(?![A-Za-z])")
    evidence_pat = re.compile("|".join(EVIDENCE_BRACKETS))

    in_code = False
    out_lines = []
    for raw in content.splitlines():
        line = raw
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            out_lines.append(line)
            continue
        if in_code or should_skip_line(line):
            out_lines.append(line)
            continue

        # 依次应用多个 pattern（顺序很重要：长、罕见优先以减少互相干扰）
        line = apply_bold_outside_existing(line, frame_pat)   # 框架/专有短语最先
        line = apply_bold_outside_existing(line, event_pat)   # 事件名（含「案」字）
        line = apply_bold_outside_existing(line, party_pat)   # 政党派系
        line = apply_bold_outside_existing(line, person_pat)  # 人名
        line = apply_bold_outside_existing(line, mbti_pat)    # MBTI 类型（词边界保护）
        line = apply_bold_outside_existing(line, evidence_pat)  # 证据等级括号
        out_lines.append(line)

    result = "\n".join(out_lines)
    # 保留原始文件末尾换行行为
    if content.endswith("\n") and not result.endswith("\n"):
        result += "\n"

    if dry_run:
        print(f"[DRY] {path}: {len(content)} → {len(result)} chars (diff {len(result) - len(content):+d})")
        return

    with open(path, "w", encoding="utf-8") as f:
        f.write(result)
    print(f"✅ {os.path.basename(path)}: {len(content)} → {len(result)} chars (+{len(result) - len(content)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="md paths to patch")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for p in args.files:
        if not os.path.exists(p):
            print(f"❌ not found: {p}")
            continue
        patch_file(p, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
