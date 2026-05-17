"""Batch-upgrade all country topic files to the 22-query template.

Run from project root:
    python tools/batch_upgrade_topics.py
"""
from __future__ import annotations

from pathlib import Path

TOPICS_DIR = Path("topics")

# ── Country registry ───────────────────────────────────────────────────────
# code → (中文名, English name, filename, lang_mode, languages_yaml, special_notes, extra_queries)

COUNTRIES: list[dict] = [
    # ── South America (Spanish) ────────────────────────────────────────
    dict(
        code="mx", zh="墨西哥", en="Mexico", file="mexico_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：USMCA框架下三角贸易关系、中墨投资摩擦、锂矿开发竞争、边境移民议题",
        extra=[
            "USMCA Mexico Estados Unidos aranceles comercio",
            "Mexico litio minería China empresa EE.UU.",
            "Mexico frontera migración seguridad EE.UU.",
        ],
    ),
    dict(
        code="co", zh="哥伦比亚", en="Colombia", file="colombia_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：布埃纳文图拉港口中国投资、彼得罗政府对华/对美立场、毒品战争与美国反制",
        extra=[
            "Colombia Buenaventura puerto China empresa inversión",
            "Colombia Petro China EE.UU. política exterior diplomacia",
        ],
    ),
    dict(
        code="ar", zh="阿根廷", en="Argentina", file="argentina_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：BRI成员国（2022年加入）、锂三角、与中国人民币互换协议、IMF债务",
        extra=[
            "Argentina litio China empresa minería inversión",
            "Argentina yuan swap China reservas acuerdo",
            "Argentina BRI China préstamo infraestructura",
        ],
    ),
    dict(
        code="br", zh="巴西", en="Brazil", file="brazil_monitor.md",
        lang="pt", languages="[pt, es, en, zh]",
        note="重点关注：BRI成员国讨论、华为5G争议、中国最大贸易伙伴（大豆/铁矿石）、庞大华人社区",
        extra=[
            "China Brasil mineração ferro soja comércio energia",
            "Brasil China Huawei 5G tecnologia investimento",
            "Brasil EE.UU. China multipolaridade política exterior",
        ],
    ),
    dict(
        code="pe", zh="秘鲁", en="Peru", file="peru_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：钱凯港（中国国有企业建设，2024年开港）、中国矿业投资（铜/银/锌）",
        extra=[
            "Peru Chancay puerto China COSCO megaproyecto",
            "Peru cobre plata zinc minería China empresa inversión",
        ],
    ),
    dict(
        code="ve", zh="委内瑞拉", en="Venezuela", file="venezuela_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：中国石油贷款（以油还债）、美国制裁与中国规避、马杜罗政府外交立场",
        extra=[
            "Venezuela China petróleo deuda préstamo PDVSA acuerdo",
            "Venezuela sanciones EE.UU. China Maduro relaciones",
        ],
    ),
    dict(
        code="ec", zh="厄瓜多尔", en="Ecuador", file="ecuador_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：可可科多辛克莱大坝（中国建设，质量争议）、中国渔船过度捕捞争议、中国债务重组",
        extra=[
            "Ecuador China deuda préstamo infraestructura renegociación",
            "Ecuador pesca ilegal China flota pesquera Galápagos",
        ],
    ),
    dict(
        code="bo", zh="玻利维亚", en="Bolivia", file="bolivia_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：锂三角核心国（全球最大锂储量之一）、中国电池企业（CATL/BYD）投资竞争",
        extra=[
            "Bolivia litio China empresa CATL BYD acuerdo inversión",
            "Bolivia litio EE.UU. India empresa competencia",
        ],
    ),
    dict(
        code="uy", zh="乌拉圭", en="Uruguay", file="uruguay_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：南美洲最稳定民主国家；中乌农业贸易（大豆/牛肉）；自贸区谈判",
        extra=[],
    ),
    dict(
        code="py", zh="巴拉圭", en="Paraguay", file="paraguay_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="⚑ 南美洲唯一与台湾保持正式邦交的国家，重点监测维持/动摇的新进展及中方施压",
        extra=[
            "Paraguay Taiwan embajada acuerdo bilateral visita oficial",
            "Paraguay China presión reconocimiento diplomático",
        ],
    ),
    dict(
        code="gy", zh="圭亚那", en="Guyana", file="guyana_monitor.md",
        lang="en", languages="[en, es, zh]",
        note="重点关注：2015年起海上石油大发现（埃克森美孚），中国与美国竞争能源影响力，领土争端",
        extra=[
            "Guyana oil ExxonMobil China investment energy competition",
            "Guyana Venezuela border dispute US China",
        ],
    ),
    dict(
        code="sr", zh="苏里南", en="Suriname", file="suriname_monitor.md",
        lang="en", languages="[en, es, zh, pt]",
        note="重点关注：华裔人口占比高（约15%），中国移民社区，矿产/林业投资",
        extra=[
            "Suriname Chinese community investment mining timber",
            "Suriname oil offshore China US investment",
        ],
    ),
    # ── Central America (Spanish) ──────────────────────────────────────
    dict(
        code="gt", zh="危地马拉", en="Guatemala", file="guatemala_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="⚑ 中美洲最大的台湾邦交国，关注外交承认稳定性及中方施压；移民/安全与美国关系",
        extra=[
            "Guatemala Taiwan embajada acuerdo visita oficial diplomacia",
            "Guatemala China presión reconocimiento diplomático",
        ],
    ),
    dict(
        code="bz", zh="伯利兹", en="Belize", file="belize_monitor.md",
        lang="en", languages="[en, es, zh]",
        note="⚑ 台湾邦交国，英语国家；关注台湾援助/ICDF项目、中国渔业争议、旅游业",
        extra=[
            "Belize Taiwan ICDF cooperation aid fisheries",
            "Belize China fishing illegal maritime",
        ],
    ),
    dict(
        code="sv", zh="萨尔瓦多", en="El Salvador", file="el_salvador_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="2018年与台湾断交转与中国建交；比特币国家实验；美国制裁争议；布克勒政府立场",
        extra=[
            "El Salvador China inversión acuerdo Bitcoin Bukele",
            "El Salvador EE.UU. relaciones sanciones migración",
        ],
    ),
    dict(
        code="hn", zh="洪都拉斯", en="Honduras", file="honduras_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="2023年3月与台湾断交转与中国建交；关注首批中国投资协议落地、美洪关系降温",
        extra=[
            "Honduras China inversión acuerdo infraestructura primer año",
            "Honduras Taiwan ruptura consecuencias empresas proyectos",
        ],
    ),
    dict(
        code="ni", zh="尼加拉瓜", en="Nicaragua", file="nicaragua_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="2021年12月与台湾断交转与中国建交；奥尔特加威权政府；美国制裁；中尼大运河旧议题",
        extra=[
            "Nicaragua China inversión canal acuerdo Ortega relaciones",
            "Nicaragua EE.UU. sanciones relaciones Ortega dictadura",
        ],
    ),
    dict(
        code="cr", zh="哥斯达黎加", en="Costa Rica", file="costa_rica_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="2007年与台湾断交转与中国建交；中哥自贸协定（2011年）；绿色/可持续发展形象",
        extra=[
            "Costa Rica China TLC acuerdo comercial inversión energía",
        ],
    ),
    dict(
        code="pa", zh="巴拿马", en="Panama", file="panama_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="2017年与台湾断交转与中国建交；巴拿马运河地区港口争议（中美竞争）；金融中心",
        extra=[
            "Panama Canal China empresa puerto control seguridad EE.UU.",
            "Panama Canal EE.UU. Trump China Hutchison puertos",
        ],
    ),
    # ── Pacific Islands ────────────────────────────────────────────────
    dict(
        code="sb", zh="所罗门群岛", en="Solomon Islands", file="solomon_islands_monitor.md",
        lang="en", languages="[en, zh]",
        note="2019年与台湾断交转与中国建交；中所安全协定（2022年）引发美澳高度警惕；太平洋战略竞争",
        extra=[
            "Solomon Islands China security agreement police military",
            "Solomon Islands Taiwan US Australia Pacific competition",
            "Solomon Islands China port infrastructure investment",
        ],
    ),
    dict(
        code="ki", zh="基里巴斯", en="Kiribati", file="kiribati_monitor.md",
        lang="en", languages="[en, zh]",
        note="2019年与台湾断交转与中国建交；气候变化海平面上升；坎顿岛战略价值；太平洋岛国外交",
        extra=[
            "Kiribati China security agreement Canton Island military",
            "Kiribati Taiwan US Pacific climate sea level diplomacy",
        ],
    ),
    dict(
        code="nr", zh="瑙鲁", en="Nauru", file="nauru_monitor.md",
        lang="en", languages="[en, zh]",
        note="多次在台湾/中国之间切换建交；2024年1月与台湾断交转与中国建交；太平洋战略节点",
        extra=[
            "Nauru Taiwan recognition diplomatic relations 2024",
            "Nauru China Taiwan switch recognition Pacific",
        ],
    ),
    dict(
        code="mh", zh="马绍尔群岛", en="Marshall Islands",
        file="marshall_islands_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾邦交国；与美国自由联合协约（COFA）；比基尼核试验遗留问题；太平洋岛国论坛成员；气候变化前线",
        extra=[
            '"Marshall Islands" Taiwan embassy recognition diplomatic COFA',
            '"Marshall Islands" COFA compact US military Kwajalein base',
            '"Marshall Islands" China pressure diplomatic recognition Taiwan Pacific',
        ],
    ),
    dict(
        code="pw", zh="帕劳", en="Palau", file="palau_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾邦交国；与美国自由联合协约（COFA）；中国游客/旅游业争议；太平洋战略要地；海洋保护区",
        extra=[
            "Palau Taiwan embassy recognition diplomatic tourism cooperation",
            "Palau China tourism ban pressure diplomatic recognition",
            "Palau COFA compact US military base Pacific security",
        ],
    ),
    dict(
        code="tv", zh="图瓦卢", en="Tuvalu", file="tuvalu_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾邦交国；全球最小国家之一；海平面上升存亡危机；与澳大利亚Falepili联盟；太平洋岛国论坛",
        extra=[
            "Tuvalu Taiwan embassy recognition diplomatic cooperation aid",
            "Tuvalu China pressure diplomatic switch recognition Pacific",
            "Tuvalu Australia Falepili Union climate sea level sinking",
            "Tuvalu .tv domain revenue internet digital sovereignty",
        ],
    ),
    # ── Africa ────────────────────────────────────────────────────────
    dict(
        code="st", zh="圣多美和普林西比", en="Sao Tome and Principe",
        file="sao_tome_monitor.md",
        lang="pt", languages="[pt, en, zh, fr]",
        note="2016年与台湾断交转与中国建交；非洲唯一葡语岛国；石油开发；中非合作论坛",
        extra=[
            "São Tomé China petróleo cooperação investimento África",
            "São Tomé Taiwan ruptura consequências projetos",
        ],
    ),
    dict(
        code="bf", zh="布基纳法索", en="Burkina Faso",
        file="burkina_faso_monitor.md",
        lang="fr", languages="[fr, en, zh]",
        note="2018年与台湾断交转与中国建交；2022年军事政变；瓦格纳/俄罗斯/中国影响扩张；法国/美国基地撤出",
        extra=[
            "Burkina Faso AES Alliance Sahel Russie Wagner Chine sécurité",
            "Burkina Faso France États-Unis base militaire retrait",
            "Burkina Faso Taïwan rupture Chine reconnaissance conséquences",
        ],
    ),
    dict(
        code="sz", zh="斯威士兰", en="Eswatini", file="eswatini_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾在非洲唯一邦交国；绝对君主制；民主运动与镇压；HIV/AIDS高感染率；南非经济依存",
        extra=[
            "Eswatini Taiwan embassy recognition Africa last ally diplomatic",
            "Eswatini Swaziland China pressure diplomatic switch recognition",
            "Eswatini democracy protest King Mswati human rights crackdown",
            "Eswatini Taiwan ICDF medical agriculture sugar textile AGOA",
        ],
    ),
    # ── Caribbean ──────────────────────────────────────────────────────
    dict(
        code="ht", zh="海地", en="Haiti", file="haiti_monitor.md",
        lang="fr", languages="[fr, en, zh]",
        note="⚑ 台湾邦交国；加勒比最贫困国家；帮派暴力与政治危机；联合国维和；美国移民/援助依存度极高",
        extra=[
            "Haiti Taiwan ambassade reconnaissance diplomatique aide officielle",
            "Haiti gang violence crise politique ONU mission sécurité",
            "Haiti EE.UU. migration aide humanitaire réfugiés",
        ],
    ),
    dict(
        code="kn", zh="圣基茨和尼维斯", en="Saint Kitts and Nevis",
        file="saint_kitts_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾邦交国；加勒比小岛国；投资入籍计划（CBI）知名；旅游经济；气候脆弱国",
        extra=[
            '"Saint Kitts" Taiwan embassy recognition diplomatic official visit',
            '"Saint Kitts" CBI citizenship investment programme China',
            '"Saint Kitts" Nevis CARICOM Caribbean cooperation China Taiwan',
        ],
    ),
    dict(
        code="lc", zh="圣卢西亚", en="Saint Lucia",
        file="saint_lucia_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾邦交国（2007年复交）；曾在中台之间切换；加勒比旅游经济；气候脆弱小岛国；OECS成员",
        extra=[
            '"Saint Lucia" Taiwan embassy recognition diplomatic switch history',
            '"Saint Lucia" OECS CARICOM Caribbean cooperation China Taiwan',
            '"Saint Lucia" geothermal energy climate resilience infrastructure',
        ],
    ),
    dict(
        code="vc", zh="圣文森特和格林纳丁斯", en="Saint Vincent and the Grenadines",
        file="saint_vincent_monitor.md",
        lang="en", languages="[en, zh]",
        note="⚑ 台湾邦交国；加勒比小岛国；火山灾害（2021年苏弗里耶尔火山爆发）；ALBA成员；气候脆弱",
        extra=[
            '"Saint Vincent" Taiwan embassy recognition diplomatic cooperation aid',
            '"Saint Vincent" ALBA CARICOM Caribbean cooperation China Taiwan',
            '"Saint Vincent" volcano Soufriere disaster reconstruction aid',
        ],
    ),
    dict(
        code="do", zh="多米尼加", en="Dominican Republic", file="dominican_republic_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="2018年与台湾断交转与中国建交；加勒比地区最大经济体；中国投资基础设施/自贸区；美国移民/旅游依存度高",
        extra=[
            "República Dominicana China inversión zona franca infraestructura acuerdo",
            "República Dominicana Taiwan ruptura reconocimiento diplomático consecuencias",
            "República Dominicana EE.UU. migración remesas turismo relaciones",
        ],
    ),
    # ── Europe ────────────────────────────────────────────────────────
    dict(
        code="va", zh="梵蒂冈", en="Vatican", file="vatican_monitor.md",
        lang="en", languages="[en, zh, it]",
        note="⚑ 台湾在欧洲唯一邦交国；中梵临时协议（主教任命）持续谈判；教廷对华外交立场微妙；全球天主教影响力",
        extra=[
            "Vatican China provisional agreement bishop renewal 2024 2025",
            "Vatican Taiwan Holy See recognition diplomatic last Europe",
            "Vatican Pope Francis China policy religious persecution Uyghur",
            "Vaticano Cina accordo provvisorio vescovi Taiwan relazioni",
        ],
    ),
    # ── Chile (re-generated to add .tw section) ────────────────────────
    dict(
        code="cl", zh="智利", en="Chile", file="chile_monitor.md",
        lang="es", languages="[es, en, zh, pt]",
        note="重点关注：铜矿/锂矿（BRI重点）、Valparaíso/San Antonio港口布局、碳税制度、SOUTHCOM合作",
        extra=[
            "USMCA Chile EE.UU. cobre litio minería",
            "Chile litio China empresa CATL BYD inversión",
            "Chile cobre energía China empresa infraestructura",
        ],
    ),
]


# ── Query templates per language mode ─────────────────────────────────────

def _queries_es(zh: str, en: str) -> list[str]:
    """Standard Spanish + Chinese + English queries."""
    return [
        # ── China line ──────────────────────────────────────────────────
        f"China {en} inversión comercio acuerdo diplomacia",
        f"China {en} puerto minería energía infraestructura",
        f"{en} empresa china infraestructura proyecto contrato",
        f"{zh} 中国 投资 贸易 合作 外交 协议",
        f"{zh} 中国 港口 矿产 能源 基础设施 企业",
        f"{en} China trade investment agreement diplomacy",
        # ── USA line ────────────────────────────────────────────────────
        f'"Estados Unidos" {en} acuerdo seguridad cooperación defensa',
        f"{en} EE.UU. arancel tarifa comercio suministro cadena",
        f"{zh} 美国 协议 安全 贸易 关税 援助 合作",
        f'{en} "United States" USAID agreement security trade tariff',
        # ── Taiwan line ─────────────────────────────────────────────────
        f"Taiwan {en} diplomacia visita ministro congreso cooperación",
        f"Taiwan {en} ICDF becas educación salud cooperación",
        f"{zh} 台湾 外交 访问 合作 奖学金 医疗 部长",
        f"Taiwan {en} carbon credits reforestation REDD forest hectares",
        f"{zh} 台湾 碳权 碳信用 造林 公顷 森林 合作",
        # ── Cross-topic ─────────────────────────────────────────────────
        f"{en} foro cumbre ONG organización evento internacional",
        f"{en} cambio climático carbono medio ambiente acuerdo política",
        f"{en} deporte intercambio cultural juventud cooperación",
        f"{en} salud pública cooperación médica donación hospital IA",
        f"{en} cooperación militar seguridad defensa armamento acuerdo",
        f"{en} comunidad china empresa crimen seguridad inmigrante",
        f"{zh} 论坛 峰会 体育 青年 环保 NGO 文化交流",
        f"{zh} 军事 安全 公卫 医疗 华人 华侨 社区",
        # ── Sentiment / risk ───────────────────────────────────────────
        f"{en} China protesta xenofobia rechazo invasión empresa china conflicto",
        f"{en} comunidad china crimen inseguridad persecución histórica disculpa",
        f"{zh} 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害",
    ]


def _queries_pt(zh: str, en: str) -> list[str]:
    """Portuguese + Chinese + English queries (Brazil, São Tomé)."""
    return [
        # ── China line ──────────────────────────────────────────────────
        f"China {en} investimento comércio acordo diplomacia",
        f"China {en} porto mineração energia infraestrutura",
        f"{en} empresa chinesa infraestrutura projeto contrato",
        f"{zh} 中国 投资 贸易 合作 外交 协议",
        f"{zh} 中国 港口 矿产 能源 基础设施 企业",
        f"{en} China trade investment agreement diplomacy",
        # ── USA line ────────────────────────────────────────────────────
        f'"Estados Unidos" {en} acordo segurança cooperação defesa',
        f"{en} EUA tarifa comércio segurança acordo",
        f"{zh} 美国 协议 安全 贸易 关税 援助 合作",
        f'{en} "United States" USAID agreement security trade tariff',
        # ── Taiwan line ─────────────────────────────────────────────────
        f"Taiwan {en} diplomacia visita ministro cooperação",
        f"Taiwan {en} ICDF bolsas educação saúde cooperação",
        f"{zh} 台湾 外交 访问 合作 奖学金 医疗 部长",
        f"Taiwan {en} carbon credits reforestation REDD forest hectares",
        f"{zh} 台湾 碳权 碳信用 造林 公顷 森林 合作",
        # ── Cross-topic ─────────────────────────────────────────────────
        f"{en} fórum cúpula ONG organização evento internacional",
        f"{en} mudança climática carbono meio ambiente acordo política",
        f"{en} esporte intercâmbio cultural juventude cooperação",
        f"{en} saúde pública cooperação médica doação hospital IA",
        f"{en} cooperação militar segurança defesa armamento acordo",
        f"{en} comunidade chinesa empresa crime segurança imigração",
        f"{zh} 论坛 峰会 体育 青年 环保 NGO 文化交流",
        f"{zh} 军事 安全 公卫 医疗 华人 华侨 社区",
        # ── Sentiment / risk ───────────────────────────────────────────
        f"{en} China protesto xenofobia rejeição invasão empresa chinesa conflito",
        f"{en} comunidade chinesa crime insegurança perseguição histórica desculpa",
        f"{zh} 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害",
    ]


def _queries_fr(zh: str, en: str) -> list[str]:
    """French + Chinese + English queries (Burkina Faso)."""
    return [
        # ── China line ──────────────────────────────────────────────────
        f"Chine {en} investissement commerce accord diplomatie",
        f"Chine {en} port exploitation minerais énergie infrastructure",
        f"{en} entreprise chinoise infrastructure projet contrat",
        f"{zh} 中国 投资 贸易 合作 外交 协议",
        f"{zh} 中国 港口 矿产 能源 基础设施 企业",
        f"{en} China trade investment agreement diplomacy",
        # ── USA line ────────────────────────────────────────────────────
        f'"États-Unis" {en} accord sécurité coopération défense',
        f"{en} USA aide sanctions accord commerce",
        f"{zh} 美国 协议 安全 贸易 关税 援助 合作",
        f'{en} "United States" USAID agreement security cooperation',
        # ── Taiwan line ─────────────────────────────────────────────────
        f"Taïwan {en} diplomatie visite ministre coopération",
        f"Taïwan {en} ICDF bourses éducation santé coopération",
        f"{zh} 台湾 外交 访问 合作 奖学金 医疗 部长",
        f"Taiwan {en} carbon credits reforestation REDD forest hectares",
        f"{zh} 台湾 碳权 碳信用 造林 公顷 森林 合作",
        # ── Cross-topic ─────────────────────────────────────────────────
        f"{en} forum sommet ONG organisation événement international",
        f"{en} changement climatique carbone environnement accord politique",
        f"{en} sport échange culturel jeunesse coopération",
        f"{en} santé publique coopération médicale don hôpital IA",
        f"{en} coopération militaire sécurité défense armement accord",
        f"{en} communauté chinoise entreprise crime sécurité immigration",
        f"{zh} 论坛 峰会 体育 青年 环保 NGO 文化交流",
        f"{zh} 军事 安全 公卫 医疗 华人 华侨 社区",
        # ── Sentiment / risk ───────────────────────────────────────────
        f"{en} Chine protestation xénophobie rejet invasion entreprise chinoise conflit",
        f"{en} communauté chinoise crime insécurité persécution historique excuse",
        f"{zh} 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害",
    ]


def _queries_en(zh: str, en: str) -> list[str]:
    """English-primary + Chinese queries (Pacific islands, Guyana, Belize, Suriname)."""
    return [
        # ── China line ──────────────────────────────────────────────────
        f"{en} China investment trade agreement diplomacy",
        f"{en} China port mining energy infrastructure project",
        f"{en} Chinese company infrastructure contract construction",
        f"{zh} 中国 投资 贸易 合作 外交 协议",
        f"{zh} 中国 港口 矿产 能源 基础设施 企业",
        f"{en} China bilateral relations cooperation security",
        # ── USA line ────────────────────────────────────────────────────
        f"{en} United States agreement security cooperation defense",
        f"{en} US USAID aid trade agreement sanctions",
        f"{zh} 美国 协议 安全 贸易 关税 援助 合作",
        f"{en} US Pacific strategy security competition China",
        # ── Taiwan line ─────────────────────────────────────────────────
        f"Taiwan {en} diplomacy visit minister cooperation",
        f"Taiwan {en} ICDF scholarship education health cooperation",
        f"{zh} 台湾 外交 访问 合作 奖学金 医疗 部长",
        f"Taiwan {en} carbon credits reforestation REDD forest hectares",
        f"{zh} 台湾 碳权 碳信用 造林 公顷 森林 合作",
        # ── Cross-topic ─────────────────────────────────────────────────
        f"{en} forum summit NGO organization international event",
        f"{en} climate change carbon environment agreement policy",
        f"{en} sports cultural exchange youth cooperation",
        f"{en} public health medical cooperation donation hospital AI",
        f"{en} military security cooperation defense agreement",
        f"{en} Chinese community business crime security immigration",
        f"{zh} 论坛 峰会 体育 青年 环保 NGO 文化交流",
        f"{zh} 军事 安全 公卫 医疗 华人 华侨 社区",
        # ── Sentiment / risk ───────────────────────────────────────────
        f"{en} China protest xenophobia rejection invasion Chinese company conflict",
        f"{en} Chinese community crime insecurity persecution historical apology",
        f"{zh} 中国 抗议 排斥 仇外 冲突 安全 风险 华人 迫害",
    ]


def _get_queries(lang: str, zh: str, en: str) -> list[str]:
    if lang == "pt":
        return _queries_pt(zh, en)
    if lang == "fr":
        return _queries_fr(zh, en)
    if lang == "en":
        return _queries_en(zh, en)
    return _queries_es(zh, en)


# ── Exclude keywords per language ──────────────────────────────────────────

_EXCLUDE_ES = """
- resultados
- clasificación
- gol
- marcador
- entretenimiento
- farándula
- espectáculo
- telenovela
- beisbol
- baseball
- WBC
- fútbol
- football
- encuesta
- sondeo
""".strip()

_EXCLUDE_PT = """
- resultados
- classificação
- gol
- entretenimento
- celebridade
- espetáculo
- futebol
- football
- beisebol
- WBC
- pesquisa
- sondagem
""".strip()

_EXCLUDE_FR = """
- résultats
- classement
- but
- divertissement
- célébrité
- football
- baseball
- WBC
- sondage
- enquête
""".strip()

_EXCLUDE_EN = """
- sports results
- standings
- entertainment
- celebrity
- baseball
- WBC
- football results
- poll
""".strip()


def _get_excludes(lang: str) -> str:
    return {"pt": _EXCLUDE_PT, "fr": _EXCLUDE_FR, "en": _EXCLUDE_EN}.get(lang, _EXCLUDE_ES)


# ── Taiwan .tw domain queries (universal, appended to all countries) ────────
# site: operator works in SerpAPI/Google; returns 0 results in NewsData.io (harmless)

def _queries_tw_domain(zh: str, en: str) -> list[str]:
    """4 queries targeting Taiwan-side publications directly."""
    return [
        # Taiwan MOFA official site — official foreign affairs announcements
        f'site:mofa.gov.tw "{en}"',
        # Taiwan ICDF — bilateral cooperation projects (education/health/environment/carbon)
        f'site:icdf.org.tw "{en}"',
        # Taiwan Central News Agency (CNA) — Taiwan's official newswire
        f'site:cna.com.tw "{en}"',
        # Chinese-language search for Taiwan government statements (works in both APIs)
        f"{zh} 台湾 外交部 ICDF 声明 合作 公告 计划",
    ]


# ── File generator ─────────────────────────────────────────────────────────

def generate(c: dict) -> str:
    zh, en, code = c["zh"], c["en"], c["code"]
    lang = c["lang"]
    languages = c["languages"]
    note = c["note"]
    extra = c.get("extra", [])

    lang_label = {"pt": "葡语", "fr": "法语", "en": "英语"}.get(lang, "西班牙语")
    excludes_block = _get_excludes(lang)

    # Build queries split into named sections
    # indices: 0-5=China, 6-9=USA, 10-14=Taiwan, 15-22=cross, 23-25=sentiment
    base = _get_queries(lang, zh, en)
    china_q     = base[0:6]
    usa_q       = base[6:10]
    taiwan_q    = base[10:15]
    cross_q     = base[15:23]
    sentiment_q = base[23:26]
    tw_dom_q    = _queries_tw_domain(zh, en)

    def bullets(qs: list[str]) -> str:
        return "\n".join(f"- {q}" for q in qs)

    extra_block = ("\n\n### ── 国别专项补充查询 ────────────────────────────────────────\n\n"
                   + bullets(extra)) if extra else ""

    return f"""---
name: {zh}动态监测
countries: [{code}]
watch_countries: [tw, cn, us]
search_global: true
skip_sources: [newsapi_ai]
languages: {languages}
time_range_hours: 168
time_mode: last_week
max_articles: 20
enabled: true
---

# {zh}动态监测

{note}

涵盖12个主题维度：外交政治 / 经贸投资 / 港口航运 / 矿产能源 / 教育文化 /
公卫医疗 / NGO论坛展会 / 体育青年 / 环保气候碳权 / 军事安全 / LGBT政策 / 当地华人社区

查询语言：{lang_label} + 中文 + 英文（三语并行，SerpAPI/NewsData 各语言独立命中）
台湾侧深挖：mofa.gov.tw / icdf.org.tw / cna.com.tw（site: 查询，SerpAPI 有效，NewsData 跳过）

## 搜索查询

### ── 关系线1：{zh} × 中国 ────────────────────────────────────────

{bullets(china_q)}

### ── 关系线2：{zh} × 美国 ────────────────────────────────────────

{bullets(usa_q)}

### ── 关系线3：{zh} × 台湾 ────────────────────────────────────────

{bullets(taiwan_q)}

### ── 关系线3附：台湾侧主动发布（.tw 域名深挖）────────────────────────────
# site: 查询在 SerpAPI/Google 生效；NewsData.io 不支持 site: 语法，返回空（无副作用）
# 覆盖：台湾外交部(MOFA) / ICDF国际合作基金 / 中央社(CNA)

{bullets(tw_dom_q)}

### ── 跨议题（三条关系线共用）────────────────────────────────────────

{bullets(cross_q)}

### ── 对华舆情与风险信号 ────────────────────────────────────────

{bullets(sentiment_q)}{extra_block}

## 排除关键词

{excludes_block}

## 检测结果分类

1. {zh}与台湾（外交 / 教育文化 / 公卫 / 体育 / 环保碳权 / ICDF）
2. {zh}与中国（外交经贸 / 港口矿能 / 中资企业 / 华人社区）
3. {zh}与美国（外交安全 / 经贸关税 / USAID / 军事）
4. 对华舆情（排华情绪 / 中资企业冲突 / 华人安全 / 历史迫害 / 社区摩擦）
"""


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    TOPICS_DIR.mkdir(exist_ok=True)

    skip: set[str] = set()

    updated = []
    for c in COUNTRIES:
        if c["code"] in skip:
            print(f"  SKIP  {c['code']:3}  {c['zh']} (already upgraded)")
            continue

        content = generate(c)
        path = TOPICS_DIR / c["file"]
        path.write_text(content, encoding="utf-8")

        # Quick verify
        import sys
        sys.path.insert(0, "src")
        from news_monitor.topics.loader import _parse_topic_md
        topic = _parse_topic_md(path)
        n_queries = len(topic.get("query_groups", []))
        updated.append((c["code"], c["zh"], n_queries))
        print(f"  OK    {c['code']:3}  {c['zh']:12}  {n_queries} queries → {path.name}")

    print(f"\nDone. Updated {len(updated)} files, skipped {len(skip)}")
    print(f"  Query counts: {[n for _, _, n in updated]}")


if __name__ == "__main__":
    main()
