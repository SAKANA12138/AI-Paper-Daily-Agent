import time
import random
import requests

def fetch_from_api_with_retry(endpoint, params=None, headers=None,
                              session=None,
                              initial_delay=5,
                              max_delay=300,
                              max_total_wait=None,
                              timeout=30):
    """
    持续重试直到成功或达到 max_total_wait（秒）。
    - endpoint: 请求 URL
    - params: 请求参数
    - headers: 请求头
    - session: requests.Session() 可复用连接
    - initial_delay: 初始等待秒数
    - max_delay: 指数退避最大等待秒数
    - max_total_wait: 总等待上限（秒），None 表示无限制（谨慎）
    - timeout: 单次请求超时（秒）
    返回: 成功时返回 data 列表，失败或遇不可重试错误返回 []
    """
    if session is None:
        session = requests.Session()

    start_time = time.time()
    delay = initial_delay
    attempt = 0

    while True:
        attempt += 1
        try:
            resp = session.get(endpoint, params=params, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            elapsed = time.time() - start_time
            print(f"⚠️ 网络异常（{e}），第 {attempt} 次重试，已耗时 {int(elapsed)}s，等待 {int(delay)}s 后重试...")
            if max_total_wait and elapsed + delay > max_total_wait:
                print("❌ 达到最大等待时间，放弃重试（网络异常）")
                return []
            time.sleep(delay + random.uniform(0, 1.5))
            delay = min(delay * 2, max_delay)
            continue

        # 成功
        if resp.status_code == 200:
            try:
                data = resp.json().get("data", [])
            except ValueError:
                print("⚠️ 返回非 JSON，尝试返回空列表")
                data = []
            time.sleep(1.5)  # Actions 中稍作延迟，防止短时间内连续请求
            return data

        # 限流处理 429
        if resp.status_code == 429:
            retry_after = None
            if 'Retry-After' in resp.headers:
                try:
                    retry_after = int(resp.headers['Retry-After'])
                except Exception:
                    retry_after = None

            wait = retry_after if retry_after is not None else delay
            wait = wait + random.uniform(0, 1.5)  # jitter
            elapsed = time.time() - start_time
            print(f"⚠️ 触发频率限制 (429)，第 {attempt} 次重试，等待 {int(wait)} 秒后重试...")
            if max_total_wait and elapsed + wait > max_total_wait:
                print("❌ 达到最大等待时间，放弃重试（429）")
                return []
            time.sleep(wait)
            delay = min(delay * 2, max_delay)
            continue

        # 服务器短期错误 5xx 也重试
        if 500 <= resp.status_code < 600:
            elapsed = time.time() - start_time
            print(f"⚠️ 服务器错误 {resp.status_code}，第 {attempt} 次重试，等待 {int(delay)} 秒后重试...")
            if max_total_wait and elapsed + delay > max_total_wait:
                print(f"❌ 达到最大等待时间，放弃重试（{resp.status_code}）")
                return []
            time.sleep(delay + random.uniform(0, 1.5))
            delay = min(delay * 2, max_delay)
            continue

        # 其他客户端错误（如 400/401/403 等）通常不重试，打印 body 便于排查
        print(f"❌ API 链路异常，错误码: {resp.status_code}, body: {resp.text[:300]}")
        return []
