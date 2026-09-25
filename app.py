"""
Level 1 & Real-Web Auto-Vote Dashboard Controller
Web UI & API server for launching, controlling, and analyzing real website voting campaigns.
"""

from flask import Flask, render_template, request, jsonify
import asyncio
import threading
import json
import re
from urllib.parse import urljoin, urlparse
import requests
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from voter_engine import AutoVoterEngine, USER_AGENTS_POOL, extract_origin_referer

app = Flask(__name__, static_folder="static", template_folder="templates")

# Global Voter Engine instance
voter = AutoVoterEngine()
engine_thread = None
loop = None

def run_async_loop(async_loop, coro):
    asyncio.set_event_loop(async_loop)
    async_loop.run_until_complete(coro)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def get_status():
    stats = voter.stats.copy()
    stats["is_running"] = voter.is_running
    return jsonify(stats)

@app.route("/api/start", methods=["POST"])
def start_voting():
    global engine_thread, loop
    if voter.is_running:
        return jsonify({"status": "error", "message": "Voter engine is already running!"}), 400

    config = request.get_json(silent=True) or {}
    url = config.get("url")
    if not url:
        return jsonify({"status": "error", "message": "Target URL is required!"}), 400

    # Format payload
    payload_raw = config.get("payload", "")
    payload_type = config.get("payload_type", "json")
    payload = {}
    if payload_raw:
        if payload_type == "json":
            try:
                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except Exception as e:
                return jsonify({"status": "error", "message": f"Invalid JSON payload: {str(e)}"}), 400
        elif payload_type == "form":
            if isinstance(payload_raw, str):
                # Parse key=val&key2=val2 or JSON form string
                try:
                    payload = json.loads(payload_raw)
                except Exception:
                    payload = {}
                    for item in payload_raw.split("&"):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            payload[k.strip()] = v.strip()
            else:
                payload = payload_raw
        else:
            payload = payload_raw

    # Custom Headers
    headers_raw = config.get("custom_headers", "")
    custom_headers = {}
    if headers_raw and isinstance(headers_raw, str):
        for line in headers_raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                custom_headers[k.strip()] = v.strip()
    elif isinstance(headers_raw, dict):
        custom_headers = headers_raw

    # Parse Proxies list
    proxies_raw = config.get("proxies", "")
    proxies_list = []
    if isinstance(proxies_raw, str):
        proxies_list = [p.strip() for p in proxies_raw.splitlines() if p.strip()]
    elif isinstance(proxies_raw, list):
        proxies_list = proxies_raw

    voter_config = {
        "url": url,
        "method": config.get("method", "POST"),
        "payload_type": payload_type,
        "payload": payload,
        "custom_headers": custom_headers,
        "concurrency": int(config.get("concurrency", 5)),
        "delay_ms": int(config.get("delay_ms", 100)),
        "max_votes": int(config.get("max_votes", 0)),
        "rotate_ua": bool(config.get("rotate_ua", True)),
        "spoof_ip": bool(config.get("spoof_ip", False)),
        "expected_status": int(config.get("expected_status", 200)),
        "expected_keyword": config.get("expected_keyword", ""),
        "proxies": proxies_list,
        "fetch_csrf": bool(config.get("fetch_csrf", False)),
        "csrf_page_url": config.get("csrf_page_url", url),
        "csrf_param_name": config.get("csrf_param_name", "csrf_token"),
        "csrf_location": config.get("csrf_location", "body"),
        "csrf_regex": config.get("csrf_regex", ""),
        "verify_ssl": bool(config.get("verify_ssl", True)),
        "keep_cookies": bool(config.get("keep_cookies", False))
    }

    loop = asyncio.new_event_loop()
    engine_thread = threading.Thread(target=run_async_loop, args=(loop, voter.run(voter_config)), daemon=True)
    engine_thread.start()

    return jsonify({"status": "success", "message": "Real-Web Auto-vote campaign launched successfully!"})

@app.route("/api/stop", methods=["POST"])
def stop_voting():
    if not voter.is_running:
        return jsonify({"status": "error", "message": "Voter engine is not running."}), 400
    voter.stop()
    return jsonify({"status": "success", "message": "Stop signal sent to voter engine."})

@app.route("/api/analyze", methods=["POST"])
def analyze_page():
    """Smart Target Analyzer: Fetches real webpage HTML and auto-detects voting forms, endpoints, and CSRF fields."""
    data = request.get_json(silent=True) or {}
    page_url = data.get("page_url", "").strip()
    if not page_url:
        return jsonify({"status": "error", "message": "Page URL is required!"}), 400

    headers = {
        "User-Agent": USER_AGENTS_POOL[0]["ua"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        resp = requests.get(page_url, headers=headers, timeout=10, verify=False)
        html = resp.text

        forms_found = []

        if HAS_BS4:
            soup = BeautifulSoup(html, "html.parser")
            forms = soup.find_all("form")

            for idx, form in enumerate(forms):
                action = form.get("action", "")
                method = (form.get("method") or "POST").upper()
                action_url = urljoin(page_url, action) if action else page_url

                inputs = {}
                radio_options = []
                csrf_token = None
                csrf_name = None

                for inp in form.find_all(["input", "select", "button"]):
                    inp_name = inp.get("name")
                    inp_type = (inp.get("type") or "text").lower()
                    inp_val = inp.get("value", "")

                    if not inp_name:
                        continue

                    # Check for CSRF token
                    if re.search(r"csrf|_token|nonce|authenticity", inp_name, re.I):
                        csrf_token = inp_val
                        csrf_name = inp_name

                    if inp_type == "radio":
                        # Look for label text
                        label_text = inp_val
                        if inp.get("id"):
                            label = soup.find("label", {"for": inp["id"]})
                            if label:
                                label_text = label.get_text(strip=True)
                        radio_options.append({"name": inp_name, "value": inp_val, "label": label_text})
                    else:
                        inputs[inp_name] = inp_val

                forms_found.append({
                    "form_index": idx + 1,
                    "action_url": action_url,
                    "method": method,
                    "inputs": inputs,
                    "radio_options": radio_options,
                    "csrf_detected": {"name": csrf_name, "value": csrf_token} if csrf_name else None
                })

        # Also search meta CSRF tags
        meta_csrf = None
        m = re.search(r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', html, re.I)
        if m:
            meta_csrf = m.group(1)

        origin, referer = extract_origin_referer(page_url)

        return jsonify({
            "status": "success",
            "page_url": page_url,
            "origin": origin,
            "referer": referer,
            "forms_count": len(forms_found),
            "forms": forms_found,
            "meta_csrf": meta_csrf,
            "html_snippet": html[:500]
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to fetch page: {str(e)}"}), 500

@app.route("/api/inspect", methods=["POST"])
def inspect_target():
    """Performs a single diagnostic test vote request and reports returned status & headers."""
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"status": "error", "message": "Target URL is required!"}), 400

    method = data.get("method", "POST").upper()
    payload_type = data.get("payload_type", "json")
    payload_raw = data.get("payload", "")

    origin, referer = extract_origin_referer(url)
    headers = {
        "User-Agent": USER_AGENTS_POOL[0]["ua"],
        "Accept": "application/json, text/plain, */*",
        "Origin": origin,
        "Referer": referer
    }

    req_kwargs = {"headers": headers, "timeout": 8, "verify": False}
    if method in ["POST", "PUT", "PATCH"] and payload_raw:
        if payload_type == "json":
            try:
                req_kwargs["json"] = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
            except Exception as e:
                return jsonify({"status": "error", "message": f"Invalid JSON payload: {str(e)}"}), 400
        elif payload_type == "form":
            req_kwargs["data"] = payload_raw
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            req_kwargs["data"] = payload_raw

    try:
        resp = requests.request(method, url, **req_kwargs)
        set_cookies = dict(resp.cookies)

        return jsonify({
            "status": "success",
            "http_code": resp.status_code,
            "response_preview": resp.text[:500],
            "cookies_set": set_cookies,
            "response_headers": dict(resp.headers),
            "analysis": f"Endpoint returned HTTP status {resp.status_code}. Server set {len(set_cookies)} cookies."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Target request failed: {str(e)}"}), 500

if __name__ == "__main__":
    print("==================================================================")
    print("[+] Real-Web Auto-Vote Dashboard Controller")
    print("    Open in browser: http://127.0.0.1:5000")
    print("==================================================================")
    app.run(host="127.0.0.1", port=5000, debug=False)
