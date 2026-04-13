"""台湾政府网站数据爬取 —— 通过代理访问中选会/监察院/公督盟/立法院。"""
import json, re, time
from pathlib import Path
import httpx

PROXY = "http://127.0.0.1:18182"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUT = Path("people/data_collection/extracted")
OUT.mkdir(parents=True, exist_ok=True)


def _get(url, timeout=30):
    return httpx.Client(proxy=PROXY, timeout=timeout, follow_redirects=True, trust_env=False, headers=HEADERS).get(url)


# ═══════ 1. 中选会 2022 台北市长 12 区得票 ═══════
def scrape_cec_2022():
    """从中选会网站或维基百科抓取 2022 台北市长各行政区得票。"""
    # 中选会 API 端点（JSON格式）
    urls_to_try = [
        "https://db.cec.gov.tw/ElecTable/Election/ElecTickets?dataType=tickets&typeNo=ELC&subjectNo=T&legisId=00&areaNo=63&deptNo=000&liNo=0000",
        "https://zh.wikipedia.org/wiki/2022%E5%B9%B4%E4%B8%AD%E8%8F%AF%E6%B0%91%E5%9C%8B%E7%9B%B4%E8%BD%84%E5%B8%82%E9%95%B7%E5%8F%8A%E7%B8%A3%E5%B8%82%E9%95%B7%E9%81%B8%E8%88%89",
    ]

    results = {"source": "", "data": []}

    # 尝试中选会
    try:
        resp = _get("https://db.cec.gov.tw/ElecTable/Election?type=ELC", timeout=15)
        print(f"  中选会主页: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  中选会不可达: {e}")

    # 从维基百科抓取（更可靠）
    try:
        resp = _get("https://zh.wikipedia.org/w/api.php?action=parse&page=2022%E5%B9%B4%E4%B8%AD%E8%8F%AF%E6%B0%91%E5%9C%8B%E7%9B%B4%E8%BD%84%E5%B8%82%E9%95%B7%E5%8F%8A%E7%B8%A3%E5%B8%82%E9%95%B7%E9%81%B8%E8%88%89&prop=wikitext&section=0&format=json", timeout=20)
        if resp.status_code == 200:
            results["source"] = "wikipedia_api"
            results["raw_status"] = "fetched"
    except Exception as e:
        print(f"  维基API: {e}")

    # 备选：直接搜索带精确数字的页面
    try:
        url = "https://zh.wikipedia.org/w/api.php?action=parse&page=2022%E5%B9%B4%E8%87%BA%E5%8C%97%E5%B8%82%E5%B8%82%E9%95%B7%E9%81%B8%E8%88%89&prop=wikitext&format=json"
        resp = _get(url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
            # 提取得票数据
            results["source"] = "wikipedia_2022_taipei_mayor"
            results["wikitext_length"] = len(wikitext)
            # 保存原始 wikitext 供后续解析
            (OUT / "T0-02_wiki_raw.txt").write_text(wikitext, encoding="utf-8")
            print(f"  维基台北市长选举页: {len(wikitext)} chars")
    except Exception as e:
        print(f"  维基台北市长: {e}")

    return results


# ═══════ 2. 监察院财产申报 ═══════
def scrape_sunshine_assets():
    """监察院阳光法案主题网 - 财产申报查询。"""
    results = {"source": "sunshine.cy.gov.tw", "data": []}
    try:
        # 搜索蒋万安
        resp = _get("https://sunshine.cy.gov.tw/GipOpenWeb/wSite/ct?xItem=2&ctNode=345&mp=5", timeout=20)
        print(f"  监察院阳光法案: HTTP {resp.status_code}, {len(resp.text)} chars")
        results["page_size"] = len(resp.text)
        results["accessible"] = resp.status_code == 200

        # 尝试查询 API
        resp2 = _get("https://sunshine.cy.gov.tw/GipOpenWeb/wSite/public/Attachment/f1710000000.pdf", timeout=15)
        results["pdf_test"] = resp2.status_code
    except Exception as e:
        results["error"] = str(e)
        print(f"  监察院: {e}")
    return results


# ═══════ 3. 监察院政治献金 ═══════
def scrape_sunshine_donations():
    """监察院政治献金公开查阅。"""
    results = {"source": "sunshine.cy.gov.tw/politicaldonate", "data": []}
    try:
        resp = _get("https://ardata.cy.gov.tw/home", timeout=20)
        print(f"  政治献金平台: HTTP {resp.status_code}, {len(resp.text)} chars")
        results["accessible"] = resp.status_code == 200

        # 尝试搜索蒋万安
        resp2 = httpx.Client(proxy=PROXY, timeout=30, follow_redirects=True, trust_env=False, headers=HEADERS).post(
            "https://ardata.cy.gov.tw/api/v1/search",
            json={"keyword": "蒋万安", "type": "candidate"},
        )
        if resp2.status_code == 200:
            results["search_result"] = resp2.json()
            print(f"  政治献金搜索: {resp2.status_code}")
    except Exception as e:
        results["error"] = str(e)
        print(f"  政治献金: {e}")
    return results


# ═══════ 4. 立法院 ═══════
def scrape_ly_records():
    """立法院国会图书馆 - 委员提案查询。"""
    results = {"source": "lis.ly.gov.tw", "data": []}
    try:
        # 立法院 OPEN API
        resp = _get("https://data.ly.gov.tw/odw/openDatasetJson.action?id=20&selectTerm=all&term=10&name=%E8%94%A3%E8%90%AC%E5%AE%89", timeout=20)
        print(f"  立法院API: HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            results["data"] = data
            results["count"] = len(data) if isinstance(data, list) else "non-list"
    except Exception as e:
        results["error"] = str(e)
        print(f"  立法院: {e}")

    # 备选：npl.ly.gov.tw
    try:
        resp2 = _get("https://npl.ly.gov.tw/do/www/commissionerInfo?id=1756&expireBack=01&expire=10&act=exp&keyword=&orderBy=name&nameRecv=&partyRecv=", timeout=20)
        print(f"  立法院委员页: HTTP {resp2.status_code}, {len(resp2.text)} chars")
        results["npl_accessible"] = resp2.status_code == 200
        results["npl_size"] = len(resp2.text)
    except Exception as e:
        results["npl_error"] = str(e)

    return results


# ═══════ 5. 公督盟 ═══════
def scrape_ccw():
    """公民监督国会联盟评�的查询。"""
    results = {"source": "ccw.org.tw", "data": []}
    try:
        resp = _get("https://ccw.org.tw/legislator/%E8%94%A3%E8%90%AC%E5%AE%89", timeout=20)
        print(f"  公督盟: HTTP {resp.status_code}, {len(resp.text)} chars")
        results["accessible"] = resp.status_code == 200
        results["page_size"] = len(resp.text)
        if resp.status_code == 200:
            # 保存原始HTML
            (OUT / "T0-06_ccw_raw.html").write_text(resp.text, encoding="utf-8")
    except Exception as e:
        results["error"] = str(e)
        print(f"  公督盟: {e}")
    return results


# ═══════ Main ═══════
if __name__ == "__main__":
    print("=== 台湾政府网站爬取 ===\n")

    all_results = {}

    print("[1/5] 中选会...")
    all_results["cec"] = scrape_cec_2022()

    print("[2/5] 监察院财产...")
    all_results["sunshine_assets"] = scrape_sunshine_assets()

    print("[3/5] 政治献金...")
    all_results["sunshine_donations"] = scrape_sunshine_donations()

    print("[4/5] 立法院...")
    all_results["ly"] = scrape_ly_records()

    print("[5/5] 公督盟...")
    all_results["ccw"] = scrape_ccw()

    # 保存汇总
    out_file = OUT / "T0_taiwan_gov_raw.json"
    out_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n汇总 → {out_file}")
