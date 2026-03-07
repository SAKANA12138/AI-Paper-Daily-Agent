import os
import time
import math
import random
import requests
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI

# =================================================================
# 1. 配置与全局计时器
# =================================================================
START_TIME = time.time()
MAX_TOTAL_TIME = 600  # 强制 10 分钟总限时 (秒)

# 从环境变量读取 API KEY
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("未找到 GOOGLE_API_KEY！请在 GitHub Secrets 中配置。")

# 目录配置
DATA_DIR = "data"
REPORTS_DIR = "reports"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "elite_processed_ids.txt")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)

# 目标会议
ELITE_VENUES = ["ICLR", "NeurIPS", "ICML", "AAAI", "IJCAI", "ACL", "CVPR", "Nature", "Science"]
API_VENUES_STR = ",".join(ELITE_VENUES)

# =================================================================
# 2. 核心辅助函数：监控时间与智能休眠
# =================================================================
def get_remaining_time():
    """计算剩余可用秒数"""
    return MAX_TOTAL_TIME - (time.time() - START_TIME)

def smart_sleep(attempt, cap=90, label="API"):
    """
    指数退避休眠
    attempt: 第几次重试
    cap: 最高休眠上限（Gemini 建议 90s，语义学者建议 30s）
    """
    remaining = get_remaining_time()
    if remaining <= 10: # 剩不到10秒就别睡了，直接放弃
        return False
    
    # 指数计算: 2^n + 抖动
    wait_time = min(math.pow(2, attempt) + random.uniform(0, 3), cap)
    # 确保不超出总限时
    actual_wait = min(wait_time, remaining - 5)
    
    if actual_wait > 0:
        print(f"💤 [{label}] 进入休眠: {int(actual_wait)}s (第 {attempt} 次重试，总剩余: {int(remaining)}s)")
        time.sleep(actual_wait)
        return True
    return False

# =================================================================
# 3. 语义学者 API 检索 (带死磕逻辑)
# =================================================================
def fetch_from_api_with_retry(endpoint, params):
    attempt = 0
    while get_remaining_time() > 0:
        try:
            response = requests.get(endpoint, params=params, timeout=20)
            if response.status_code == 200:
                return response.json().get("data", [])
            elif response.status_code == 429:
                attempt += 1
                if not smart_sleep(attempt, cap=30, label="Scholar_429"): break
            else:
                attempt += 1
                if not smart_sleep(attempt, cap=15, label="Scholar_Error"): break
        except Exception as e:
            attempt += 1
            if not smart_sleep(attempt, cap=15, label="Network_Error"): break
    return []

def fetch_elite_papers(query, pool_size=40):
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    base_params = {
        "query": query, "limit": 50,
        "fields": "title,venue,abstract,citationCount,influentialCitationCount,paperId",
        "year": "2024-2026"
    }

    # 读取历史记录
    history = set()
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            history = {line.strip() for line in f}

    refined_list = []
    seen_ids = set(history)
    offset = 0

    print(f"🔍 开始检索关键词: {query}")
    while len(refined_list) < pool_size and offset < 500:
        if get_remaining_time() < 60: break # 留一分钟给后续逻辑
        
        current_params = base_params.copy()
        current_params["offset"] = offset
        data = fetch_from_api_with_retry(endpoint, current_params)
        
        if not data: break
        
        for p in data:
            pid = p.get("paperId")
            if not p.get("abstract") or pid in seen_ids: continue
            
            # 简单的评分逻辑
            citations = p.get("citationCount", 0) or 0
            inf_citations = p.get("influentialCitationCount", 0) or 0
            score = citations + (inf_citations * 5)
            
            p['quality_score'] = score
            p['status'] = "🏆 顶级期刊" if any(v.lower() in (p.get("venue") or "").lower() for v in ELITE_VENUES) else "📄 普通"
            refined_list.append(p)
            seen_ids.add(pid)
            
        offset += 50
    
    refined_list.sort(key=lambda x: x['quality_score'], reverse=True)
    return refined_list[:pool_size]

# =================================================================
# 4. AI 深度分析 (带死磕逻辑)
# =================================================================
def analyze_and_report(papers):
    if not papers:
        print("📭 今日暂无符合标准的新论文。")
        return False

    full_report = f"# 💎 精英 AI 论文日报 ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    success_count = 0

    for p in papers:
        if get_remaining_time() < 40: # 剩下的时间不够一次 API 调用了
            print("⏰ 时间窗口关闭，收尾已完成部分。")
            break

        print(f"🚀 深度解析中: {p['title'][:50]}...")
        prompt = f"你是一位顶级科学家。请深度拆解论文《{p['title']}》，摘要如下：{p['abstract']}。请按范式转移、底层逻辑、技术关键、大牛视角、开发者手册五个维度分析。"
        
        success = False
        attempt = 0
        while not success:
            if get_remaining_time() < 30: break
            try:
                res = llm.invoke(prompt)
                report_piece = f"## 🏆 {p['title']}\n- **链接**: https://www.semanticscholar.org/paper/{p['paperId']}\n\n{res.content}\n\n---\n"
                full_report += report_piece
                
                # 记录已处理
                with open(DB_PATH, "a") as f:
                    f.write(f"{p['paperId']}\n")
                
                success = True
                success_count += 1
                print("✨ 解析成功！")
                time.sleep(2) # 避开极瞬时限流
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    attempt += 1
                    if not smart_sleep(attempt, cap=95, label="Gemini_429"): break
                else:
                    print(f"❌ Gemini 遇到非限流错误: {e}")
                    break

    if success_count > 0:
        # 同时保存到报告库和 GitHub Action 读取文件
        save_path = os.path.join(REPORTS_DIR, f"Report_{datetime.now().strftime('%Y%m%d')}.md")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(full_report)
        with open("REPORT_CONTENT.md", "w", encoding="utf-8") as f:
            f.write(full_report)
        print(f"✅ 成功生成 {success_count} 篇论文的深度报告。")
        return True
    return False

# =================================================================
# 5. 执行入口
# =================================================================
if __name__ == "__main__":
    # 如果今天已经有报告了，直接退出
    today_report = os.path.join(REPORTS_DIR, f"Report_{datetime.now().strftime('%Y%m%d')}.md")
    if os.path.exists(today_report):
        print("✅ 今日报告已存在，跳过任务。")
        exit(0)

    TOPIC = "LLM Agents planning reasoning"
    TARGET_COUNT = 1  # 免费版建议每天 1-3 篇，多了大概率超时

    # 1. 检索
    candidates = fetch_elite_papers(TOPIC, pool_size=30)
    
    # 2. 分析
    final_selection = candidates[:TARGET_COUNT]
    analyze_and_report(final_selection)
    
    print(f"🏁 脚本运行结束，总耗时: {int(time.time() - START_TIME)}s")
