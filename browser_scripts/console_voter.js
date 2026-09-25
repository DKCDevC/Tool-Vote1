/**
 * Real-Web Browser Console Auto-Voter v2.1
 * Paste this script directly into F12 DevTools -> Console tab on ANY real voting webpage.
 * 
 * Features for Real Websites:
 * 1. Bypasses CORS by executing directly on the target website's origin.
 * 2. Auto-detects CSRF tokens & nonces from DOM (<input name="..."> or <meta name="...">).
 * 3. Supports JSON, x-www-form-urlencoded, and FormData payloads.
 * 4. Automatically clears localStorage, sessionStorage, and domain cookies between votes.
 * 5. Provides floating HUD progress overlay with INSTANT STOP BUTTON.
 */

(async function startRealWebConsoleVoter(userConfig = {}) {
    window.STOP_AUTO_VOTE = false; // Set to true to stop loop instantly

    const config = {
        maxVotes: userConfig.maxVotes || 50,
        delayMs: userConfig.delayMs || 300,
        url: userConfig.url || window.location.href,
        method: (userConfig.method || "POST").toUpperCase(),
        payloadType: userConfig.payloadType || "auto",
        payload: userConfig.payload || null,
        autoDetectCsrf: userConfig.autoDetectCsrf !== false,
        csrfParamName: userConfig.csrfParamName || "csrf_token"
    };

    console.clear();
    console.log("%c⚡ REAL-WEB BROWSER AUTO-VOTER LAUNCHED", "color: #38bdf8; font-size: 16px; font-weight: bold;");
    console.log(`[+] Target Endpoint: ${config.url}`);
    console.log(`[+] Method:          ${config.method}`);
    console.log(`[+] Max Votes:       ${config.maxVotes}`);
    console.log(`[+] Delay:           ${config.delayMs}ms`);
    console.log("%c[*] To stop script manually, type: STOP_AUTO_VOTE = true or press F5", "color: #facc15;");
    console.log("%c--------------------------------------------------", "color: #475569;");

    function getCsrfToken() {
        if (!config.autoDetectCsrf) return null;
        const meta = document.querySelector('meta[name*="csrf"], meta[name*="token"], meta[name="csrf-token"]');
        if (meta && meta.content) return { name: "X-CSRF-Token", val: meta.content, location: "header" };

        const inputs = document.querySelectorAll('input[type="hidden"], input[name*="csrf"], input[name*="token"], input[name*="nonce"]');
        for (let inp of inputs) {
            if (inp.name && inp.value) {
                return { name: inp.name, val: inp.value, location: "body" };
            }
        }
        return null;
    }

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

    // Create Floating HUD Overlay on Target Web Page with STOP BUTTON
    let hud = document.getElementById('auto-vote-hud');
    if (!hud) {
        hud = document.createElement('div');
        hud.id = 'auto-vote-hud';
        hud.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 999999;
            background: rgba(15, 23, 42, 0.95); color: #f8fafc; font-family: sans-serif;
            padding: 16px; border-radius: 12px; border: 1px solid #38bdf8;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5); min-width: 270px; font-size: 13px;
        `;
        document.body.appendChild(hud);
    }

    function updateHud(total, success, fail, status) {
        hud.innerHTML = `
            <div style="font-weight: bold; color: #38bdf8; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                <span>⚡ Real-Web Voter</span>
                <span style="color: ${status === 'DONE' ? '#4ade80' : (status === 'STOPPED' ? '#f87171' : '#f59e0b')}">${status}</span>
            </div>
            <div>Sent: <strong>${total}</strong> / ${config.maxVotes}</div>
            <div style="color: #4ade80;">Success: <strong>${success}</strong></div>
            <div style="color: #f87171;">Failed: <strong>${fail}</strong></div>
            ${status === 'RUNNING' ? `
                <button id="btn-stop-voter" style="margin-top: 10px; width: 100%; background: #ef4444; color: white; border: none; padding: 6px; border-radius: 6px; font-weight: bold; cursor: pointer;">
                    ⏹ DỪNG NGHAY LẬP TỨC
                </button>
            ` : ''}
        `;

        const stopBtn = document.getElementById('btn-stop-voter');
        if (stopBtn) {
            stopBtn.onclick = () => {
                window.STOP_AUTO_VOTE = true;
                console.warn("[!] User clicked STOP button.");
            };
        }
    }

    let successCount = 0;
    let failCount = 0;
    const basePayload = detectFormPayload();

    for (let i = 1; i <= config.maxVotes; i++) {
        if (window.STOP_AUTO_VOTE) {
            updateHud(i - 1, successCount, failCount, "STOPPED");
            console.log("%c⏹ AUTO-VOTE STOPPED BY USER.", "color: #ef4444; font-weight: bold;");
            return;
        }

        try { localStorage.clear(); sessionStorage.clear(); } catch (e) {}
        try {
            document.cookie.split(";").forEach(c => {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
        } catch (e) {}

        const currentPayload = Object.assign({}, basePayload);
        const csrfInfo = getCsrfToken();
        const headers = { "Accept": "application/json, text/plain, */*" };

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
    maxVotes: 50,
    delayMs: 300,
    payloadType: "auto"
});
