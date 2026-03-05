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
# 2. 检索逻辑 (已更新 pool_size 和 batch_size 逻辑)
# =================================================================
def fetch_from_api_with_retry(endpoint, params):
    max_retries = 3
    retry_delay = 5
    for i in range(max_retries):
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            # 💡 在 GitHub Actions 中建议增加小量延迟，防止请求过快
            time.sleep(1.5)
            return response.json().get("data", [])
        elif response.status_code == 429:
            print(f"⚠️ 触发频率限制，等待 {retry_delay} 秒后重试...")
            time.sleep(retry_delay)
            retry_delay *= 2
        else:
            print(f"❌ API 链路异常，错误码: {response.status_code}")
            return []
    return []

def fetch_elite_papers(query, pool_size=50, batch_size=50):
    """
    pool_size: 想要凑齐的候选池大小
    batch_size: 每次翻页请求的数量
    """
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    base_params = {
        "query": query, "limit": batch_size,
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

    # -----------------------------------------------------------------
    # 第一阶段：锁定顶会 (循环翻页直到凑够)
    # -----------------------------------------------------------------
    print(f"💎 正在扫描顶会数据 (凑齐 {pool_size} 篇候选)...")
    offset = 0
    while len(refined_list) < pool_size and offset < 1000:
        stage1_params = base_params.copy()
        stage1_params["venue"] = API_VENUES_STR
        stage1_params["offset"] = offset
        
        data = fetch_from_api_with_retry(endpoint, stage1_params)
        if not data: break
        
        for p in data:
            processed = process_and_score_paper(p)
            if processed: refined_list.append(processed)
        
        print(f"📡 顶会阶段 Offset={offset}，候选池进度: {len(refined_list)}/{pool_size}")
        offset += batch_size
        time.sleep(2) # 防封保护

    # -----------------------------------------------------------------
    # 第二阶段：补位逻辑
    # -----------------------------------------------------------------
    if len(refined_list) < pool_size:
        print(f"⚠️ 顶会池不足，开启全局搜索补位...")
        offset = 0
        while len(refined_list) < pool_size and offset < 1000:
            stage2_params = base_params.copy()
            stage2_params["offset"] = offset
            
            data = fetch_from_api_with_retry(endpoint, stage2_params)
            if not data: break
            
            for p in data:
                processed = process_and_score_paper(p)
                if processed: refined_list.append(processed)
            
            print(f"🌐 全局阶段 Offset={offset}，总进度: {len(refined_list)}/{pool_size}")
            offset += batch_size
            time.sleep(2)

    # 按分数全局排序，返回最高质量的候选
    refined_list.sort(key=lambda x: x['quality_score'], reverse=True)
    return refined_list[:pool_size]

# =================================================================
# 3. 分析与导出
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

                # 记录 ID
                with open(DB_PATH, "a") as f:
                    f.write(f"{p['paperId']}\n")

                success = True
                time.sleep(10)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    attempts += 1
                    wait_time = 35 + (attempts * 10)
                    print(f"⚠️ Gemini 限流，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ 解析失败: {e}")
                    break

    # 保存报告为文件
    date_str = datetime.now().strftime('%Y%m%d')
    save_path = os.path.join(REPORTS_DIR, f"Elite_Report_{date_str}.md")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(full_report)
    print(f"✅ 报告已保存至 {save_path}")
    
    # 💡 写入 REPORT_CONTENT.md 供 GitHub Actions 后续步骤读取
    with open("REPORT_CONTENT.md", "w", encoding="utf-8") as f:
        f.write(full_report)

# =================================================================
# 4. 执行入口 (用户配置区)
# =================================================================
if __name__ == "__main__":
    # 👇 [用户修改区] 学术关键词
    TOPIC = "LLM Agents planning reasoning"
    
    # 👇 [用户修改区] 每天最终分析几篇？(选出候选池中最强的 N 篇)
    TARGET_COUNT = 1 

    # 👇 [用户修改区] 候选池大小和每页抓取量
    POOL_SIZE = 50
    BATCH_SIZE = 50

    print(f"🔍 启动任务：从 {POOL_SIZE} 篇候选论文中筛选【{TOPIC}】精华...")
    
    # 运行多页检索
    candidate_pool = fetch_elite_papers(TOPIC, pool_size=POOL_SIZE, batch_size=BATCH_SIZE)
    
    # 从候选池中提取排名前 TARGET_COUNT 的论文进行 AI 分析
    final_selection = candidate_pool[:TARGET_COUNT]
    
    # 运行 AI 深度分析
    analyze_and_report(final_selection)
