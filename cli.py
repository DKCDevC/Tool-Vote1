"""
Level 1 & Real-Web Auto-Vote CLI Tool
High-speed command-line interface for real website auto-voting with proxy rotation & CSRF token extraction.

Usage example:
    python cli.py --url https://target-site.com/api/vote --method POST --payload '{"option_id":"option_1"}' --threads 10 --proxies proxies.txt
"""

import argparse
import asyncio
import json
import os
import sys
from colorama import init, Fore, Style
from voter_engine import AutoVoterEngine

init(autoreset=True)

def print_banner():
    banner = f"""
==================================================================
   ⚡ REAL-WEB AUTO-VOTE CLI TOOL (Proxy & CSRF Token Enabled)
==================================================================
    """
    print(banner)

async def main_cli():
    parser = argparse.ArgumentParser(description="Real-Web Auto-Vote Tool with Proxy Rotation & CSRF Token Auto-Fetcher")
    parser.add_argument("--url", "-u", required=True, help="Target Vote Endpoint URL (e.g. https://site.com/api/vote)")
    parser.add_argument("--method", "-m", default="POST", choices=["POST", "GET", "PUT", "PATCH"], help="HTTP Method (default: POST)")
    parser.add_argument("--payload", "-p", default="{}", help='Request Payload string or JSON (e.g. \'{"option_id": "1"}\')')
    parser.add_argument("--payload-type", default="json", choices=["json", "form", "raw"], help="Payload type (default: json)")
    parser.add_argument("--threads", "-t", type=int, default=5, help="Number of concurrent worker threads (default: 5)")
    parser.add_argument("--delay", "-d", type=int, default=100, help="Delay between requests per thread in ms (default: 100)")
    parser.add_argument("--count", "-c", type=int, default=0, help="Target vote count (0 for infinite, default: 0)")
    parser.add_argument("--expected-status", type=int, default=200, help="Expected HTTP status code for success (default: 200)")
    parser.add_argument("--expected-keyword", default="", help="Keyword required in response text to count as success")
    parser.add_argument("--proxies", help="Path to text file containing proxy list (one proxy per line) or comma-separated proxies")
    parser.add_argument("--fetch-csrf", action="store_true", help="Enable automatic GET CSRF token extraction before POST vote")
    parser.add_argument("--csrf-page-url", help="Page URL to fetch CSRF token from (defaults to target URL)")
    parser.add_argument("--csrf-param-name", default="csrf_token", help="CSRF form input/meta field name (default: csrf_token)")
    parser.add_argument("--csrf-location", default="body", choices=["body", "header"], help="Where to inject CSRF token (default: body)")
    parser.add_argument("--no-ua-rotate", action="store_true", help="Disable User-Agent rotation")
    parser.add_argument("--spoof-ip", action="store_true", help="Enable X-Forwarded-For random IP header spoofing")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification")
    parser.add_argument("--keep-cookies", action="store_true", help="Keep session cookies between requests")

    args = parser.parse_args()
    print_banner()

    # Parse payload
    payload_data = args.payload
    if args.payload_type == "json" and args.payload:
        try:
            payload_data = json.loads(args.payload)
        except Exception as e:
            print(f"{Fore.RED}[!] Invalid JSON payload: {str(e)}{Style.RESET_ALL}")
            sys.exit(1)
    elif args.payload_type == "form" and args.payload:
        try:
            payload_data = json.loads(args.payload)
        except Exception:
            payload_data = {}
            for item in args.payload.split("&"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    payload_data[k.strip()] = v.strip()

    # Parse Proxies
    proxies_list = []
    if args.proxies:
        if os.path.isfile(args.proxies):
            with open(args.proxies, "r", encoding="utf-8", errors="ignore") as f:
                proxies_list = [line.strip() for line in f if line.strip()]
        else:
            proxies_list = [p.strip() for p in args.proxies.split(",") if p.strip()]

    config = {
        "url": args.url,
        "method": args.method,
        "payload_type": args.payload_type,
        "payload": payload_data,
        "concurrency": args.threads,
        "delay_ms": args.delay,
        "max_votes": args.count,
        "rotate_ua": not args.no_ua_rotate,
        "spoof_ip": args.spoof_ip,
        "expected_status": args.expected_status,
        "expected_keyword": args.expected_keyword,
        "proxies": proxies_list,
        "fetch_csrf": args.fetch_csrf,
        "csrf_page_url": args.csrf_page_url or args.url,
        "csrf_param_name": args.csrf_param_name,
        "csrf_location": args.csrf_location,
        "verify_ssl": not args.insecure,
        "keep_cookies": args.keep_cookies,
        "custom_headers": {}
    }

    print(f"{Fore.CYAN}[+] Target Endpoint: {Style.BRIGHT}{args.url}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[+] Method: {args.method} | Threads: {args.threads} | Delay: {args.delay}ms{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[+] Proxies Loaded: {len(proxies_list)}{Style.RESET_ALL}")
    if args.fetch_csrf:
        print(f"{Fore.YELLOW}[*] CSRF Auto-Fetch: Enabled (Field: '{args.csrf_param_name}' -> {args.csrf_location}){Style.RESET_ALL}")
    print(f"{Fore.GREEN}[*] Launching Real-Web Engine...{Style.RESET_ALL}\n")

    voter = AutoVoterEngine()

    async def stats_monitor():
        last_count = 0
        while voter.is_running:
            await asyncio.sleep(1)
            total = voter.stats["total_sent"]
            success = voter.stats["success_count"]
            fail = voter.stats["fail_count"]
            speed = total - last_count
            last_count = total

            sys.stdout.write(
                f"\r{Fore.CYAN}[STATUS] Sent: {Fore.WHITE}{Style.BRIGHT}{total}{Style.RESET_ALL} | "
                f"{Fore.GREEN}Success: {Fore.WHITE}{Style.BRIGHT}{success}{Style.RESET_ALL} | "
                f"{Fore.RED}Failed: {Fore.WHITE}{Style.BRIGHT}{fail}{Style.RESET_ALL} | "
                f"{Fore.YELLOW}Speed: {speed} v/s{Style.RESET_ALL}   "
            )
            sys.stdout.flush()

    try:
        monitor_task = asyncio.create_task(stats_monitor())
        await voter.run(config)
        monitor_task.cancel()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Campaign stopped by user (Ctrl+C).{Style.RESET_ALL}")
        voter.stop()

    print(f"\n\n{Fore.GREEN}==================================================================")
    print(f"  CAMPAIGN SUMMARY")
    print(f"  Total Sent: {voter.stats['total_sent']}")
    print(f"  Successful: {voter.stats['success_count']}")
    print(f"  Failed:     {voter.stats['fail_count']}")
    print(f"=================================================================={Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main_cli())
