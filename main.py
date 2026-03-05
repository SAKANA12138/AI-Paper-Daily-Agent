import os, time, requests
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI

# =================================================================
# 1. 配置与环境：适应 GitHub Actions 环境
# =================================================================
# 从环境变量读取 API KEY（在 GitHub Secrets 中配置）
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("未找到 GOOGLE_API_KEY 环境变量！")

# 将路径改为相对路径，存放在仓库的 data 和 reports 文件夹下
DATA_DIR = "data"
REPORTS_DIR = "reports"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "elite_processed_ids.txt")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)


ELITE_VENUES = [
    "ICLR", "International Conference on Learning Representations",
    "NeurIPS", "Neural Information Processing Systems", "NIPS",
    "ICML", "International Conference on Machine Learning",
    "AAAI", "Conference on Artificial Intelligence",
    "IJCAI", "International Joint Conference on Artificial Intelligence",
    "ACL", "Association for Computational Linguistics",
    "EMNLP", "Empirical Methods in Natural Language Processing",
    "NAACL", "North American Chapter of the Association for Computational Linguistics",
    "TACL", "Transactions of the Association for Computational Linguistics",
    "CVPR", "Computer Vision and Pattern Recognition",
    "ICCV", "International Conference on Computer Vision",
    "ECCV", "European Conference on Computer Vision",
    "PAMI", "Pattern Analysis and Machine Intelligence",
    "IJCV", "International Journal of Computer Vision",
    "Nature", "Science", "Scientific Reports"
]
API_VENUES_STR = "ICLR,NeurIPS,NIPS,ICML,AAAI,IJCAI,ACL,EMNLP,NAACL,CVPR,ICCV,ECCV,Nature,Science"

# =================================================================
# 2. 检索逻辑 
# =================================================================
def fetch_from_api_with_retry(endpoint, params):
    max_retries = 3
    retry_delay = 5
    for i in range(max_retries):
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 429:
            print(f"⚠️ 触发频率限制，等待 {retry_delay} 秒后重试...")
            time.sleep(retry_delay)
            retry_delay *= 2
        else:
            print(f"❌ API 链路异常，错误码: {response.status_code}")
            return []
    return []

def fetch_elite_papers(query, target_count=1, search_limit=100):
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    base_params = {
        "query": query, "limit": search_limit,
        "fields": "title,venue,year,abstract,citationCount,influentialCitationCount,externalIds,authors,publicationVenue",
        "year": "2023-2026"
    }

    history = set()
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            history = set(line.strip() for line in f)

    refined_list = []
    seen_ids = set(history)

    def process_and_score_paper(p):
        pid = p.get("paperId")
        if not p.get("abstract") or pid in seen_ids:
            return None
        venue_str = p.get("venue") or ""
        pub_info = p.get("publicationVenue") or {}
        full_venue_text = f"{venue_str} {pub_info.get('name', '')} {' '.join(pub_info.get('alternate_names', []))}"
        
        citations = p.get("citationCount", 0) or 0
        inf_citations = p.get("influentialCitationCount", 0) or 0
        score = citations + (inf_citations * 5)

        is_elite = any(v.lower() in full_venue_text.lower() for v in ELITE_VENUES)
        if is_elite:
            score += 20
            p['status'] = f"🏆 顶级期刊: {venue_str if venue_str else 'Top Venue'}"
        else:
            p['status'] = "📄 普通期刊/其他"

        p['quality_score'] = score
        seen_ids.add(pid)
        return p

    print("💎 正在扫描学术金字塔顶端数据 (第一阶段：锁定顶会)...")
    stage1_params = base_params.copy()
    stage1_params["venue"] = API_VENUES_STR
    stage1_data = fetch_from_api_with_retry(endpoint, stage1_params)
    for p in stage1_data:
        processed_p = process_and_score_paper(p)
        if processed_p:
            refined_list.append(processed_p)

    refined_list.sort(key=lambda x: x['quality_score'], reverse=True)
    if len(refined_list) >= target_count:
        print(f"✅ 第一轮检索达标！共找到 {len(refined_list)} 篇。")
        return refined_list[:target_count]

    print(f"⚠️ 顶会论文数量不足，开启全局图谱搜索作为替补...")
    stage2_data = fetch_from_api_with_retry(endpoint, base_params)
    for p in stage2_data:
        processed_p = process_and_score_paper(p)
        if processed_p:
            refined_list.append(processed_p)
            
    refined_list.sort(key=lambda x: x['quality_score'], reverse=True)
    print(f"✅ 两轮检索完成。池内新论文: {len(refined_list)} 篇")
    return refined_list[:target_count]

# =================================================================
# 3. 分析与导出 (为了能在 GitHub Actions 中调用，我们让它返回 Markdown 文本)
# =================================================================
def analyze_and_report(papers):
    if not papers:
        print("📭 今日暂无符合标准的新论文。")
        return None

    full_report = f"# 💎 全球精英 AI 论文日报 ({datetime.now().strftime('%Y-%m-%d')})\n\n"

    for p in papers:
        print(f"🚀 正在启动深度解析: {p['title'][:60]}... (Score: {p['quality_score']})")
        prompt = f"""
你是一位任职于 OpenAI/DeepMind 的首席科学家（Principal Researcher）。
现在请你以极度严苛且敏锐的学术眼光，深度解剖这篇发表在 [{p.get('venue', 'Unknown')}] 的顶级论文：
标题：{p['title']}
摘要：{p['abstract']}

请按以下维度进行深度拆解（使用中文，保持专业、犀利、启发性）：
1. **【范式转移：解决痛点】**
2. **【第一性原理：底层逻辑】**
3. **【技术解剖：关键机制】**
4. **【批判性思考：大牛视角】**
5. **【开发者行动手册：LangGraph/Agent 落地】**
请用 Markdown 格式输出。
"""
        success = False
        attempts = 0
        while not success and attempts < 3:
            try:
                res = llm.invoke(prompt)
                content = f"## 🏆 今日深度解剖：{p['title']}\n"
                content += f"- **级别**: {p['status']} | **总引用**: {p['citationCount']} | **高影响力引用**: {p['influentialCitationCount']}\n"
                content += f"- **阅读链接**: https://www.semanticscholar.org/paper/{p['paperId']}\n\n"
                content += f"{res.content}\n\n---\n"
                
                full_report += content

                # 追加写入黑名单
                with open(DB_PATH, "a") as f:
                    f.write(f"{p['paperId']}\n")

                success = True
                time.sleep(10)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    attempts += 1
                    time.sleep(35 + (attempts * 10))
                else:
                    print(f"❌ 解析失败: {e}")
                    break

    # 保存报告为文件
    date_str = datetime.now().strftime('%Y%m%d')
    save_path = os.path.join(REPORTS_DIR, f"Elite_Report_{date_str}.md")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(full_report)
    print(f"✅ 报告已保存至 {save_path}")
    
    # 将报告内容写入 GitHub Actions 的环境变量中，方便下一步发布 Issue
    with open("REPORT_CONTENT.md", "w", encoding="utf-8") as f:
        f.write(full_report)

# =================================================================
# 4. 执行入口 (用户配置区)
# =================================================================
if __name__ == "__main__":
    # 👇 [用户修改区] 在这里填入你想追踪的学术关键词
    TOPIC = "LLM Agents planning reasoning"
    
    # 👇 [用户修改区] 每天你想看几篇论文？(建议 1-3 篇,过多的论文会触发ai的限流)
    TARGET_COUNT = 1

    print(f"🔍 启动任务：搜索【{TOPIC}】领域的顶级论文...")
    
    # 运行图谱检索
    top_papers = fetch_elite_papers(TOPIC, target_count=TARGET_COUNT)
    
    # 运行 AI 深度分析并导出报告
    analyze_and_report(top_papers)
