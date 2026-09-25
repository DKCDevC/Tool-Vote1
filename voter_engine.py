"""
Level 1 & Real-Web Auto-Vote Engine
Handles isolated HTTP sessions, header rotation, proxy pools, dynamic CSRF token extraction,
and high-concurrency async voting for real-world target websites.
"""

import asyncio
import random
import time
import json
import re
import ssl
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
import aiohttp
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# Realistic modern User-Agents with aligned SEC-CH-UA metadata
USER_AGENTS_POOL = [
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "platform": '"Windows"',
        "mobile": "?0"
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "ch_ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
        "platform": '"Windows"',
        "mobile": "?0"
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "platform": '"macOS"',
        "mobile": "?0"
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "ch_ua": None,
        "platform": '"Windows"',
        "mobile": "?0"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "platform": '"Android"',
        "mobile": "?1"
    }
]

def generate_random_ip() -> str:
    """Generate a random public IPv4 address for header spoofing if requested."""
    first = random.choice([14, 27, 36, 42, 58, 103, 113, 125, 171, 180, 202, 210])
    return f"{first}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

def extract_origin_referer(url: str) -> tuple:
    """Derive default Origin and Referer headers from target URL."""
    try:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        referer = url
        return origin, referer
    except Exception:
        return "", ""

class ProxyManager:
    def __init__(self, proxies: List[str]):
        self.proxies = [p.strip() for p in proxies if p and p.strip()]
        self.index = 0
        self.lock = asyncio.Lock()

    def get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self.index % len(self.proxies)]
        self.index += 1
        if not proxy.startswith("http://") and not proxy.startswith("https://") and not proxy.startswith("socks"):
            proxy = "http://" + proxy
        return proxy

class AutoVoterEngine:
    def __init__(self):
        self.is_running = False
        self.stats = {
            "total_sent": 0,
            "success_count": 0,
            "fail_count": 0,
            "start_time": 0,
            "end_time": 0,
            "active_threads": 0,
            "logs": []
        }
        self.target_config = {}
        self._stop_event = asyncio.Event()

    def add_log(self, status: str, message: str, details: Optional[Dict] = None):
        log_entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "status": status,
            "message": message,
            "details": details or {}
        }
        self.stats["logs"].append(log_entry)
        if len(self.stats["logs"]) > 400:
            self.stats["logs"] = self.stats["logs"][-400:]

    def reset_stats(self):
        self.stats = {
            "total_sent": 0,
            "success_count": 0,
            "fail_count": 0,
            "start_time": 0,
            "end_time": 0,
            "active_threads": 0,
            "logs": []
        }

    async def fetch_csrf_token(self, session: aiohttp.ClientSession, config: Dict[str, Any], proxy: Optional[str]) -> Optional[str]:
        """Fetch target page HTML and extract dynamic CSRF token/nonce."""
        csrf_page_url = config.get("csrf_page_url") or config["url"]
        csrf_param_name = config.get("csrf_param_name", "csrf_token")
        csrf_regex = config.get("csrf_regex", "")

        try:
            req_kwargs = {
                "timeout": aiohttp.ClientTimeout(total=8),
                "allow_redirects": True
            }
            if proxy:
                req_kwargs["proxy"] = proxy
            if not config.get("verify_ssl", True):
                req_kwargs["ssl"] = False

            async with session.get(csrf_page_url, **req_kwargs) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

                # Strategy 1: Regex
                if csrf_regex:
                    match = re.search(csrf_regex, html)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)

                # Strategy 2: BeautifulSoup DOM parsing
                if HAS_BS4:
                    soup = BeautifulSoup(html, "html.parser")
                    # Check meta tags
                    meta = soup.find("meta", {"name": re.compile(rf"{csrf_param_name}|csrf", re.I)})
                    if meta and meta.get("content"):
                        return meta["content"]
                    # Check input tags
                    inp = soup.find("input", {"name": re.compile(rf"{csrf_param_name}|csrf|_token|nonce", re.I)})
                    if inp and inp.get("value"):
                        return inp["value"]

                # Strategy 3: Fallback Regex for input / meta tags
                patterns = [
                    rf'name=["\']?{re.escape(csrf_param_name)}["\']?\s+value=["\']([^"\']+)["\']',
                    rf'value=["\']([^"\']+)["\']\s+name=["\']?{re.escape(csrf_param_name)}["\']',
                    r'name=["\'](?:csrf_token|_token|nonce|authenticity_token)["\']\s+value=["\']([^"\']+)["\']',
                    r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']'
                ]
                for p in patterns:
                    m = re.search(p, html, re.I)
                    if m:
                        return m.group(1)

        except Exception as e:
            self.add_log("WARNING", f"CSRF fetch failed: {str(e)}")
        return None

    async def single_vote_request(
        self,
        session: aiohttp.ClientSession,
        config: Dict[str, Any],
        proxy_mgr: Optional[ProxyManager]
    ) -> bool:
        """Executes a single vote request with real-web browser emulation."""
        url = config["url"]
        method = config.get("method", "POST").upper()
        payload_type = config.get("payload_type", "json")
        payload = config.get("payload", {})
        custom_headers = config.get("custom_headers", {})
        rotate_ua = config.get("rotate_ua", True)
        spoof_ip = config.get("spoof_ip", False)
        expected_status = config.get("expected_status", 200)
        expected_keyword = config.get("expected_keyword", "")
        verify_ssl = config.get("verify_ssl", True)

        # Select User-Agent profile
        ua_profile = random.choice(USER_AGENTS_POOL) if rotate_ua else USER_AGENTS_POOL[0]
        
        # Derive Origin / Referer
        default_origin, default_referer = extract_origin_referer(url)

        headers = {
            "User-Agent": ua_profile["ua"],
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }

        if default_origin:
            headers["Origin"] = default_origin
        if default_referer:
            headers["Referer"] = default_referer

        if ua_profile["ch_ua"]:
            headers["sec-ch-ua"] = ua_profile["ch_ua"]
            headers["sec-ch-ua-mobile"] = ua_profile["mobile"]
            headers["sec-ch-ua-platform"] = ua_profile["platform"]

        if spoof_ip:
            ip = generate_random_ip()
            headers["X-Forwarded-For"] = ip
            headers["Client-IP"] = ip
            headers["X-Real-IP"] = ip

        # Handle Dynamic CSRF Token
        csrf_token = None
        if config.get("fetch_csrf", False):
            proxy_for_csrf = proxy_mgr.get_proxy() if proxy_mgr else None
            csrf_token = await self.fetch_csrf_token(session, config, proxy_for_csrf)
            if csrf_token:
                csrf_loc = config.get("csrf_location", "body")
                csrf_param = config.get("csrf_param_name", "csrf_token")
                if csrf_loc == "header":
                    headers["X-CSRF-Token"] = csrf_token
                    headers["X-XSRF-TOKEN"] = csrf_token
                elif isinstance(payload, dict):
                    payload[csrf_param] = csrf_token

        # Merge user custom headers (takes precedence)
        if custom_headers:
            headers.update(custom_headers)

        proxy = proxy_mgr.get_proxy() if proxy_mgr else None

        req_kwargs = {
            "headers": headers,
            "timeout": aiohttp.ClientTimeout(total=12),
            "allow_redirects": True
        }
        if proxy:
            req_kwargs["proxy"] = proxy
        if not verify_ssl:
            req_kwargs["ssl"] = False

        # Apply payload based on payload_type
        if method in ["POST", "PUT", "PATCH"]:
            if payload_type == "json":
                req_kwargs["json"] = payload if isinstance(payload, (dict, list)) else json.loads(payload or "{}")
            elif payload_type == "form":
                req_kwargs["data"] = payload if isinstance(payload, dict) else payload
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                req_kwargs["data"] = payload

        t0 = time.time()
        try:
            async with session.request(method, url, **req_kwargs) as resp:
                status_code = resp.status
                latency = int((time.time() - t0) * 1000)
                text = await resp.text()

                is_success = False
                # Accept expected status or 2xx range if 200 specified
                if status_code == expected_status or (expected_status == 200 and 200 <= status_code < 300):
                    if expected_keyword:
                        if expected_keyword.lower() in text.lower():
                            is_success = True
                    else:
                        is_success = True

                self.stats["total_sent"] += 1
                proxy_label = f" via Proxy [{proxy}]" if proxy else ""

                if is_success:
                    self.stats["success_count"] += 1
                    self.add_log(
                        "SUCCESS",
                        f"Vote #{self.stats['total_sent']} Succeeded [{status_code}]{proxy_label} ({latency}ms)",
                        {"status": status_code, "latency": latency, "preview": text[:150], "proxy": proxy}
                    )
                else:
                    self.stats["fail_count"] += 1
                    self.add_log(
                        "FAIL",
                        f"Vote #{self.stats['total_sent']} Returned [{status_code}] (expected {expected_status}){proxy_label}",
                        {"status": status_code, "latency": latency, "preview": text[:150], "proxy": proxy}
                    )
                return is_success

        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            self.stats["total_sent"] += 1
            self.stats["fail_count"] += 1
            proxy_label = f" via Proxy [{proxy}]" if proxy else ""
            self.add_log("ERROR", f"Vote #{self.stats['total_sent']} Failed: {str(e)}{proxy_label}", {"latency": latency})
            return False

    async def _worker(self, worker_id: int, config: Dict[str, Any], proxy_mgr: Optional[ProxyManager]):
        delay_ms = config.get("delay_ms", 100)
        max_votes = config.get("max_votes", 0)

        # Isolated cookie jar per request or per session
        keep_session_cookies = config.get("keep_cookies", False)

        while not self._stop_event.is_set():
            if max_votes > 0 and self.stats["total_sent"] >= max_votes:
                break

            if keep_session_cookies:
                cookie_jar = aiohttp.CookieJar()
            else:
                cookie_jar = aiohttp.DummyCookieJar()

            async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
                await self.single_vote_request(session, config, proxy_mgr)

            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

    async def run(self, config: Dict[str, Any]):
        self.is_running = True
        self.reset_stats()
        self.target_config = config
        self.stats["start_time"] = time.time()
        self._stop_event.clear()

        proxies = config.get("proxies", [])
        proxy_mgr = ProxyManager(proxies) if proxies else None

        concurrency = config.get("concurrency", 5)
        self.stats["active_threads"] = concurrency

        proxy_info = f" with {len(proxy_mgr.proxies)} rotated proxies" if proxy_mgr and proxy_mgr.proxies else " (Direct IP)"
        self.add_log("INFO", f"[START] Started Auto-Voter: {concurrency} workers{proxy_info}")

        tasks = [asyncio.create_task(self._worker(i, config, proxy_mgr)) for i in range(concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)

        self.stats["end_time"] = time.time()
        self.is_running = False
        duration = round(self.stats["end_time"] - self.stats["start_time"], 2)
        self.add_log("INFO", f"[DONE] Campaign completed in {duration}s. Sent: {self.stats['total_sent']}, Success: {self.stats['success_count']}, Failed: {self.stats['fail_count']}")

    def stop(self):
        self._stop_event.set()
        self.is_running = False
        self.add_log("WARNING", "[STOP] Stop signal received.")
