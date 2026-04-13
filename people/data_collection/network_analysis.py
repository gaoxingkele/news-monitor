"""networkx 网络图谱构建与量化分析。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from people.data_collection.config import EXTRACTED_DIR

try:
    import networkx as nx
except ImportError:
    print("Installing networkx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "networkx", "-q"])
    import networkx as nx

OUT = EXTRACTED_DIR


def build_graph():
    """从已有事实构建蒋万安权力网络图。"""
    G = nx.DiGraph()

    # 核心节点
    G.add_node("蒋万安", type="target", party="KMT", role="台北市长")

    # 从提取事实中构建边
    relationships = [
        # (source, target, relation, weight, evidence)
        ("蒋万安", "蒋经国", "祖孙（非婚生脉络）", 0.9, "B级"),
        ("蒋万安", "蒋孝严", "父子", 1.0, "A级"),
        ("蒋万安", "马英九", "政治盟友/站台背书", 0.8, "B级"),
        ("蒋万安", "朱立伦", "党主席+首都市长互补", 0.7, "B级"),
        ("蒋万安", "侯友宜", "潜在2028竞争者", 0.5, "B级"),
        ("蒋万安", "卢秀燕", "中生代竞争/合作", 0.5, "B级"),
        ("蒋万安", "韩国瑜", "立法院长/蓝营协调", 0.6, "B级"),
        ("蒋万安", "郑丽文", "党内路线竞争", 0.4, "B级"),
        ("蒋万安", "洪秀柱", "深蓝路线差异", 0.3, "C级"),
        ("蒋万安", "张亚中", "深蓝统派张力", 0.3, "C级"),
        ("蒋万安", "连战", "元老间接背书", 0.3, "C级"),
        ("蒋万安", "林奕华", "核心幕僚/前副市长", 0.9, "B级"),
        ("蒋万安", "民进党", "对抗（市府vs中央）", 0.6, "B级"),
        ("蒋万安", "民众党", "第三势力竞争", 0.4, "B级"),
        ("蒋万安", "AIT", "城市外交接触", 0.5, "B级"),
        ("蒋万安", "东京都", "城市外交合作", 0.4, "B级"),
        ("蒋万安", "黄复兴党部", "军系票仓", 0.4, "C级"),
        ("蒋万安", "台北市议会KMT团", "法案护航", 0.7, "B级"),
        ("蒋万安", "宾大法学院", "学术人脉", 0.4, "B级"),
        ("蒋万安", "台北不动产公会", "政商网络", 0.3, "C级"),
        # 二级关系
        ("马英九", "朱立伦", "党内合作", 0.5, "B级"),
        ("朱立伦", "侯友宜", "新北系合作", 0.6, "B级"),
        ("韩国瑜", "卢秀燕", "地方执政协调", 0.5, "B级"),
        ("蒋孝严", "马英九", "世代连接", 0.4, "B级"),
    ]

    for src, tgt, rel, weight, evidence in relationships:
        G.add_edge(src, tgt, relation=rel, weight=weight, evidence=evidence)
        # 确保节点存在
        if src not in G.nodes:
            G.add_node(src)
        if tgt not in G.nodes:
            G.add_node(tgt)

    return G, relationships


def compute_metrics(G):
    """计算网络量化指标。"""
    # 转为无向图计算部分指标
    UG = G.to_undirected()

    metrics = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": round(nx.density(G), 4),
    }

    # 度中心性
    dc = nx.degree_centrality(G)
    metrics["degree_centrality"] = {k: round(v, 4) for k, v in sorted(dc.items(), key=lambda x: -x[1])[:10]}

    # 中介中心性(betweenness)
    bc = nx.betweenness_centrality(UG)
    metrics["betweenness_centrality"] = {k: round(v, 4) for k, v in sorted(bc.items(), key=lambda x: -x[1])[:10]}

    # 接近中心性
    try:
        cc = nx.closeness_centrality(UG)
        metrics["closeness_centrality"] = {k: round(v, 4) for k, v in sorted(cc.items(), key=lambda x: -x[1])[:10]}
    except Exception:
        metrics["closeness_centrality"] = {}

    # 结构洞识别（constraint）
    try:
        constraint = nx.constraint(UG)
        metrics["structural_holes_constraint"] = {k: round(v, 4) for k, v in sorted(constraint.items(), key=lambda x: x[1])[:10] if v > 0}
    except Exception:
        metrics["structural_holes_constraint"] = {}

    # k-core
    try:
        kcore = nx.core_number(UG)
        metrics["k_core"] = {k: v for k, v in sorted(kcore.items(), key=lambda x: -x[1])[:10]}
    except Exception:
        metrics["k_core"] = {}

    # 桥接节点
    bridges = []
    try:
        for u, v in nx.bridges(UG):
            bridges.append(f"{u}—{v}")
    except Exception:
        pass
    metrics["bridges"] = bridges

    return metrics


def export_node_edge_list(G, relationships):
    """输出节点-边格式。"""
    nodes = []
    for n, data in G.nodes(data=True):
        nodes.append({"id": n, **data})

    edges = []
    for src, tgt, rel, weight, evidence in relationships:
        edges.append({"source": src, "target": tgt, "relation": rel, "weight": weight, "evidence": evidence})

    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    G, rels = build_graph()
    metrics = compute_metrics(G)
    ne_list = export_node_edge_list(G, rels)

    result = {"metrics": metrics, "network": ne_list}
    out_file = OUT / "network_analysis.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Nodes: {metrics['nodes']}, Edges: {metrics['edges']}, Density: {metrics['density']}")
    print(f"Top degree centrality: {list(metrics['degree_centrality'].items())[:5]}")
    print(f"Top betweenness: {list(metrics['betweenness_centrality'].items())[:5]}")
    print(f"Bridges: {metrics['bridges']}")
    print(f"→ {out_file}")
