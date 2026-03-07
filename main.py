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
MAX_TOTAL_TIME = 600  # 强制 10 分钟总限时

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

# 初始化 Gemini 模型
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.1)

# 目标顶级会议/期刊
ELITE_VENUES = ["ICLR", "NeurIPS", "ICML", "AAAI", "IJCAI", "ACL", "CVPR", "Nature", "Science"]

# =================================================================
# 2. 核心辅助函数：监控时间与“深蹲”休眠
# =================================================================
def get_remaining_time():
    """计算剩余可用秒数"""
    return MAX_TOTAL_TIME - (time.time() - START_TIME)

def smart_sleep(attempt, label="API"):
    """
    针对免费版 API 的专项休眠策略
    """
    remaining = get_remaining_time()
    if remaining <= 15: # 剩不到15秒就别睡了，准备收网
        return False
    
    if "Gemini" in label:
        # 💡 核心优化：Gemini 免费版限流通常按分钟计。
        # 一旦 429，与其 2s, 4s 地试，不如直接睡 65s 彻底跨过分钟线。
        wait_time = 65 + random.uniform(2, 7)
    else:
        # 语义学者 API 相对宽松，使用普通指数退避
        wait_time = min(pow(2, attempt) + random.uniform(1, 3), 30)
    
    # 确保不超出总限时
    actual_wait = min(wait_time, remaining - 10)
    
    if actual_wait > 0:
        print(f"💤 [{label}] 触发限流，强制深蹲 {int(actual_wait)}s (总剩余: {int(remaining)}s)")
        time.sleep(actual_wait)
        return True
    return False

# =================================================================
# 3. 语义学者 API 检索
# =================================================================
def fetch_from_api_with_retry(endpoint, params):
    attempt = 0
    while get_remaining_time() > 50: # 至少留50秒给 AI
        try:
            response = requests.get(endpoint, params=params, timeout=20)
            if response.status_code == 200:
                return response.json().get("data", [])
            elif response.status_code == 429:
                attempt += 1
                if not smart_sleep(attempt, label="Scholar_429"): break
            else:
                break
        except Exception:
            attempt += 1
            if not smart_sleep(attempt, label="Network"): break
    return []

def fetch_elite_papers(query, pool_size=30):
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    base_params = {
        "query": query, "limit": 50,
        "fields": "title,venue,abstract,citationCount,influentialCitationCount,paperId",
        "year": "2024-2026"
    }

    history = set()
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r") as f:
            history = {line.strip() for line in f}

    refined_list = []
    seen_ids = set(history)
    offset = 0

    print(f"🔍 开始检索关键词: {query}")
    while len(refined_list) < pool_size and offset < 300:
        if get_remaining_time() < 100: break
        
        current_params = base_params.copy()
        current_params["offset"] = offset
        data = fetch_from_api_with_retry(endpoint, current_params)
        
        if not data: break
        
        for p in data:
            pid = p.get("paperId")
            if not p.get("abstract") or pid in seen_ids: continue
            
            citations = p.get("citationCount", 0) or 0
            inf_citations = p.get("influentialCitationCount", 0) or 0
            p['quality_score'] = citations + (inf_citations * 5)
            refined_list.append(p)
            seen_ids.add(pid)
            
        offset += 50
    
    refined_list.sort(key=lambda x: x['quality_score'], reverse=True)
    return refined_list[:pool_size]

# =================================================================
# 4. AI 深度分析 (针对 429 进行专项加固)
# =================================================================
def analyze_and_report(papers):
    if not papers:
        print("📭 今日暂无符合标准的新论文。")
        return False

    full_report = f"# 💎 精英 AI 论文日报 ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    success_count = 0

    for p in papers:
        # 检查剩余时间是否足够进行一次完整的“深蹲+请求”
        if get_remaining_time() < 70: 
            print("⏰ 时间不足，正在保存已解析的内容...")
            break

        print(f"🚀 深度解析中: {p['title'][:50]}...")
        prompt = f"""
        你是一位顶级科学家。请深度拆解论文《{p['title']}》，摘要：{p['abstract']}。
        要求：使用中文，输出包含：范式转移、底层逻辑、技术关键、大牛视角、开发者手册。
        """
        
        success = False
        attempt = 0
        while not success and get_remaining_time() > 10:
            try:
                # 💡 成功调用
                res = llm.invoke(prompt)
                report_piece = f"## 🏆 {p['title']}\n- **链接**: https://www.semanticscholar.org/paper/{p['paperId']}\n\n{res.content}\n\n---\n"
                full_report += report_piece
                
                # 写入历史避免重复
                with open(DB_PATH, "a") as f:
                    f.write(f"{p['paperId']}\n")
                
                success = True
                success_count += 1
                print("✨ 解析成功！")
                # 成功后稍微歇一下，防止连续请求触发更严厉的封锁
                time.sleep(5) 
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    attempt += 1
                    if not smart_sleep(attempt, label="Gemini_429"): break
                else:
                    print(f"❌ 遇到非限流错误: {err_str}")
                    break

    if success_count > 0:
        save_path = os.path.join(REPORTS_DIR, f"Report_{datetime.now().strftime('%Y%m%d')}.md")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(full_report)
        with open("REPORT_CONTENT.md", "w", encoding="utf-8") as f:
            f.write(full_report)
        print(f"✅ 完成！今日产出 {success_count} 篇报告。")
        return True
    return False

# =================================================================
# 5. 主程序
# =================================================================
if __name__ == "__main__":
    # 幂等检查
    today_str = datetime.now().strftime('%Y%m%d')
    if os.path.exists(os.path.join(REPORTS_DIR, f"Report_{today_str}.md")):
        print("✅ 今日已成功运行过，跳过。")
        exit(0)

    # 🔍 核心配置
    TOPIC = "LLM Agents planning reasoning"
    TARGET_COUNT = 2  # 免费版建议目标设为 2 篇，保稳

    # 执行
    candidates = fetch_elite_papers(TOPIC, pool_size=15)
    analyze_and_report(candidates[:TARGET_COUNT])
    
    print(f"🏁 任务结束，总耗时: {int(time.time() - START_TIME)}s")
