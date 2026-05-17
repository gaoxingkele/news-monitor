"""
将所有人物的最新 word 文件搬到「人物7.3」专用目录下。
文件名格式：[人名]（政治身份）.docx
"""
import os
import shutil
import glob

OUTPUT_DIR = r"D:\aicoding\news-monitor\people\output"
TARGET_DIR = r"D:\aicoding\news-monitor\people\人物7.3"

# 政治身份映射表（截至 2026-04-20）
IDENTITY = {
    # 基准 + P0 新建
    "蒋万安": "台北市长",
    "侯友宜": "新北市长(即将卸任)",
    "李四川": "2026新北市长KMT候选人",
    "苏巧慧": "2026新北市长DPP候选人",
    "萧旭岑": "KMT副主席",
    "郑丽文": "KMT主席",
    "黄国昌": "TPP主席+2026新北市长候选人",
    "江启臣": "立法院副院长+2026台中市长KMT候选人",
    "郑丽君": "行政院副院长",
    "林俊宪": "DPP台南立委",
    "赖瑞隆": "2026高雄市长DPP候选人",
    # 批次 2 直辖市长+副总统
    "卢秀燕": "台中市长+2028总统潜在人选",
    "陈其迈": "高雄市长+2028潜在",
    "张善政": "桃园市长",
    "黄伟哲": "台南市长(即将卸任)",
    "萧美琴": "副总统",
    # 批次 3 台北绿营候选人群
    "吴思瑶": "DPP台北立委+2026北市长潜在",
    "沈伯洋": "DPP不分区立委+黑熊学院创办人",
    "林右昌": "前DPP秘书长+前基隆市长",
    "高嘉瑜": "前DPP台北立委",
    # 批次 4 南部绿营
    "陈亭妃": "2026台南市长DPP候选人",
    "邱议莹": "DPP高雄立委",
    "许智杰": "DPP高雄立委",
    "林岱桦": "DPP高雄立委(涉贪起诉)",
    # 批次 5 蓝营立委+县市长
    "谢龙介": "2026台南市长KMT候选人",
    "柯志恩": "2026高雄市长KMT候选人",
    "洪孟楷": "KMT新北立委",
    "牛煦庭": "KMT桃园立委+党发言人",
    "王惠美": "彰化县长(即将卸任)",
    "张丽善": "云林县长(即将卸任)",
    "徐榛蔚": "花莲县长(即将卸任)",
    "杨文科": "新竹县长(即将卸任)",
    "锺东锦": "苗栗县长(无党籍)",
    # 批次 6 绿白立委
    "何欣纯": "2026台中市长DPP候选人",
    "王世坚": "DPP台北立委",
    "王美惠": "DPP嘉义立委",
    "陈昭姿": "TPP不分区立委",
    # 批次 7 次要蓝营
    "颜宽恒": "前KMT台中立委",
    "陈以信": "前KMT台南立委",
    "杨琼璎": "KMT台中立委",
    "傅崐萁": "KMT立法院党团总召+花莲立委",
    # 批次 8 其他
    "吴怡农": "壮阔台湾联盟创办人+前DPP台北市党部主委",
    "苗博雅": "社民党台北市议员",
    "麦玉珍": "TPP不分区立委+2026台中市长候选人",
    "王定宇": "DPP台南立委",
    # 批次 9 战略
    "韩国瑜": "立法院长",
    "朱立伦": "前KMT主席",
    "柯文哲": "前TPP主席(司法案件中)",
    "黄珊珊": "前台北市副市长",
    # 批次 10 行政+立院
    "卓荣泰": "行政院长",
    "林佳龙": "外交部长+2028潜在",
    "顾立雄": "国防部长",
    "刘世芳": "内政部长",
    "潘孟安": "总统府秘书长",
    "吴钊燮": "国安会秘书长",
    "柯建铭": "DPP立法院党团总召",
    "罗智强": "KMT台北立委+前党主席候选人",
    # 批次 11 现任县市长
    "黄敏惠": "嘉义市长(即将卸任)",
    "高虹安": "新竹市长(TPP,复职中)",
    "谢国梁": "基隆市长",
    "周春米": "屏东县长",
    "翁章梁": "嘉义县长(即将卸任)",
    "饶庆铃": "台东县长(即将卸任)",
    "林姿妙": "宜兰县长(即将卸任,涉贪上诉)",
    "陈福海": "金门县长(无党籍)",
    # 批次 12 资深立委
    "赖士葆": "KMT资深台北立委",
    "王鸿薇": "KMT台北立委",
    "翁晓玲": "KMT不分区立委",
    "蔡其昌": "DPP台中立委+前立法院副院长",
    "赵天麟": "DPP高雄立委",
    "范云": "DPP不分区立委",
    # 批次 13 其他
    "吴欣岱": "台湾基进党政治人物",
    "赵少康": "中广董事长+2024副总统候选人",
    "王金平": "KMT老元老+前立法院长",
}

# 联合报告特殊处理
JOINT_REPORT = "2026新北市长选战"


def find_latest_docx(person_dir: str, person_name: str) -> str | None:
    """优先找 v1.8.1.docx，次选 v1.8.docx。"""
    # 候选路径
    candidates = [
        os.path.join(person_dir, f"{person_name}_政治人物分析报告_v1.8.1.docx"),
        os.path.join(person_dir, f"{person_name}_政治人物分析报告_v1.8.docx"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 备用：glob 匹配所有 v1.8* docx
    fallbacks = glob.glob(os.path.join(person_dir, "*_v1.8*.docx"))
    if fallbacks:
        # 按版本号排序取最新
        fallbacks.sort(reverse=True)
        return fallbacks[0]
    return None


def main():
    os.makedirs(TARGET_DIR, exist_ok=True)

    moved = []
    missing_identity = []
    missing_docx = []

    for entry in sorted(os.listdir(OUTPUT_DIR)):
        src_dir = os.path.join(OUTPUT_DIR, entry)
        if not os.path.isdir(src_dir):
            continue
        if entry in ("columns",):
            continue

        # 联合报告特殊处理
        if entry == JOINT_REPORT:
            src = os.path.join(src_dir, f"{entry}_李四川苏巧慧_联合评估报告_v1.8.1.docx")
            if os.path.exists(src):
                dst = os.path.join(TARGET_DIR, f"2026新北市长选战（李四川 vs 苏巧慧 联合评估报告）.docx")
                shutil.copy2(src, dst)
                moved.append((entry, os.path.basename(dst)))
            else:
                missing_docx.append(entry)
            continue

        # 一般人物
        person_name = entry
        identity = IDENTITY.get(person_name)
        if identity is None:
            missing_identity.append(person_name)
            continue

        src = find_latest_docx(src_dir, person_name)
        if src is None:
            missing_docx.append(person_name)
            continue

        # 新文件名：人名（身份）.docx
        new_name = f"{person_name}（{identity}）.docx"
        dst = os.path.join(TARGET_DIR, new_name)
        shutil.copy2(src, dst)
        moved.append((person_name, new_name))

    print(f"✅ 已复制 {len(moved)} 个文件到 {TARGET_DIR}")
    for name, new_name in moved[:10]:
        print(f"  - {name} → {new_name}")
    if len(moved) > 10:
        print(f"  ...（共 {len(moved)} 个）")

    if missing_identity:
        print(f"\n⚠️  缺身份映射的 {len(missing_identity)} 人：")
        for n in missing_identity:
            print(f"  - {n}")

    if missing_docx:
        print(f"\n⚠️  缺 v1.8 docx 的 {len(missing_docx)} 人：")
        for n in missing_docx:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
