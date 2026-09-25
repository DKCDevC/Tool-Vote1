document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const voteForm = document.getElementById('voteForm');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const inspectBtn = document.getElementById('inspectBtn');
    const runAnalyzeBtn = document.getElementById('runAnalyzeBtn');
    const analyzeResult = document.getElementById('analyzeResult');

    const valTotal = document.getElementById('valTotal');
    const valSuccess = document.getElementById('valSuccess');
    const valFailed = document.getElementById('valFailed');
    const valSpeed = document.getElementById('valSpeed');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    const logTerminal = document.getElementById('logTerminal');
    const clearLogsBtn = document.getElementById('clearLogsBtn');
    const autoscrollCheck = document.getElementById('autoscrollCheck');

    const inspectorBox = document.getElementById('inspectorBox');
    const inspectorBody = document.getElementById('inspectorBody');
    const closeInspector = document.getElementById('closeInspector');
    const copySnippetBtn = document.getElementById('copySnippetBtn');

    let pollInterval = null;
    let lastTotalCount = 0;

    // Tab Switching Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const targetEl = document.getElementById(targetTab);
            if (targetEl) targetEl.classList.add('active');
        });
    });

    // Close Inspector
    closeInspector.addEventListener('click', () => {
        inspectorBox.classList.add('hidden');
    });

    // Clear Logs
    clearLogsBtn.addEventListener('click', () => {
        logTerminal.innerHTML = '<div class="log-entry info">[SYSTEM] nhật ký đã được xóa.</div>';
    });

    // Smart Web Analyzer
    runAnalyzeBtn.addEventListener('click', async () => {
        const pageUrl = document.getElementById('analyzePageUrl').value.trim();
        if (!pageUrl) return alert("Vui lòng nhập URL trang web bình chọn mục tiêu!");

        runAnalyzeBtn.disabled = true;
        runAnalyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tải trang HTML & quét form...';
        analyzeResult.classList.remove('hidden');
        analyzeResult.innerHTML = '<p class="text-cyan"><i class="fa-solid fa-spinner fa-spin"></i> Đang quét cấu trúc HTML và tìm Endpoint vote...</p>';

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ page_url: pageUrl })
            });
            const data = await res.json();
            runAnalyzeBtn.disabled = false;
            runAnalyzeBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Phân Tích & Tự Động Điền Cấu Hình';

            if (!res.ok || data.status === 'error') {
                analyzeResult.innerHTML = `<p class="text-red">Lỗi phân tích: ${escapeHtml(data.message || 'Thất bại')}</p>`;
                return;
            }

            let html = `<div>
                <h4 style="color:#a855f7; margin-bottom:8px;"><i class="fa-solid fa-square-check"></i> Đã quét xong trang Web!</h4>
                <p><strong>Tìm thấy Form Vote:</strong> ${data.forms_count}</p>
                <p><strong>Origin:</strong> ${escapeHtml(data.origin)}</p>`;

            if (data.meta_csrf) {
                html += `<p style="color:#4ade80;"><strong>Meta CSRF Token:</strong> ${escapeHtml(data.meta_csrf)}</p>`;
            }

            if (data.forms && data.forms.length > 0) {
                data.forms.forEach((form, i) => {
                    html += `<div class="form-option-card mt-2">
                        <p><strong>Form #${i+1}:</strong> Method <code>${form.method}</code> -> <code>${escapeHtml(form.action_url)}</code></p>`;
                    
                    if (form.csrf_detected && form.csrf_detected.name) {
                        html += `<p style="color:#4ade80;"><strong>CSRF Field:</strong> ${escapeHtml(form.csrf_detected.name)} = "${escapeHtml(form.csrf_detected.value || '')}"</p>`;
                    }

                    if (form.radio_options && form.radio_options.length > 0) {
                        html += `<p class="mt-1"><strong>Tùy chọn bình chọn (Options):</strong></p><ul>`;
                        form.radio_options.forEach(opt => {
                            html += `<li>Option: <strong>${escapeHtml(opt.label || opt.value)}</strong> (name="${escapeHtml(opt.name)}", value="${escapeHtml(opt.value)}")</li>`;
                        });
                        html += `</ul>`;
                    }

                    html += `<button type="button" class="btn-autofill" data-action="${escapeHtml(form.action_url)}" data-method="${form.method}" data-csrf="${form.csrf_detected ? escapeHtml(form.csrf_detected.name || '') : ''}" data-radios='${JSON.stringify(form.radio_options || [])}' data-inputs='${JSON.stringify(form.inputs || {})}'>
                        <i class="fa-solid fa-bolt"></i> Tự Động Điền Form #${i+1} Về Cấu Hình Vote
                    </button></div>`;
                });
            } else {
                html += `<p class="text-yellow mt-2">Không tìm thấy thẻ &lt;form&gt; chuẩn. Bạn có thể sử dụng URL trang web làm Endpoint hoặc dùng Script F12 Console.</p>`;
            }

            html += `</div>`;
            analyzeResult.innerHTML = html;

            // Attach listeners to Auto-Fill buttons
            document.querySelectorAll('.btn-autofill').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const action = btn.getAttribute('data-action');
                    const method = btn.getAttribute('data-method');
                    const csrfName = btn.getAttribute('data-csrf');
                    const radios = JSON.parse(btn.getAttribute('data-radios') || '[]');
                    const inputs = JSON.parse(btn.getAttribute('data-inputs') || '{}');

                    document.getElementById('url').value = action;
                    document.getElementById('method').value = method || 'POST';

                    // Build payload
                    const payloadObj = {};
                    if (radios.length > 0) {
                        payloadObj[radios[0].name] = radios[0].value;
                    }
                    Object.assign(payloadObj, inputs);

                    document.getElementById('payloadType').value = 'form';
                    document.getElementById('payload').value = JSON.stringify(payloadObj, null, 2);

                    if (csrfName) {
                        document.getElementById('fetchCsrf').checked = true;
                        document.getElementById('csrfPageUrl').value = pageUrl;
                        document.getElementById('csrfParamName').value = csrfName;
                    }

                    // Switch to Target tab
                    document.querySelector('.tab-btn[data-tab="tab-target"]').click();
                    alert("✅ Đã tự động điền Endpoint, Method, Payload và CSRF Token vào cấu hình!");
                });
            });

        } catch (err) {
            runAnalyzeBtn.disabled = false;
            runAnalyzeBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Phân Tích & Tự Động Điền Cấu Hình';
            analyzeResult.innerHTML = `<p class="text-red">Lỗi kết nối phân tích: ${escapeHtml(err.message)}</p>`;
        }
    });

    // Copy Browser DevTools Console Snippet
    copySnippetBtn.addEventListener('click', () => {
        const url = document.getElementById('url').value;
        const payload = document.getElementById('payload').value;
        const maxVotes = document.getElementById('maxVotes').value || 50;
        const delayMs = document.getElementById('delayMs').value || 300;
        const payloadType = document.getElementById('payloadType').value;

        const snippet = `// REAL-WEB AUTO-VOTER FOR BROWSER F12 CONSOLE
(async function autoVoteRealWeb(maxVotes = ${maxVotes}, delayMs = ${delayMs}) {
    console.log("🚀 Starting Real-Web Browser Console Auto-Vote...");
    const targetUrl = "${url}";
    const payload = ${payload || '{}'};
    const payloadType = "${payloadType}";

    function getCsrfToken() {
        const meta = document.querySelector('meta[name*="csrf"], meta[name*="token"]');
        if (meta && meta.content) return { name: "X-CSRF-Token", val: meta.content, loc: "header" };
        const inp = document.querySelector('input[type="hidden"], input[name*="csrf"], input[name*="token"], input[name*="nonce"]');
        if (inp && inp.name && inp.value) return { name: inp.name, val: inp.value, loc: "body" };
        return null;
    }

    for (let i = 1; i <= maxVotes; i++) {
        try { localStorage.clear(); sessionStorage.clear(); } catch(e){}
        try {
            document.cookie.split(";").forEach(c => {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
        } catch(e){}

        const reqPayload = Object.assign({}, payload);
        const csrf = getCsrfToken();
        const headers = { "Accept": "application/json, text/plain, */*" };

        if (csrf) {
            if (csrf.loc === "header") headers[csrf.name] = csrf.val;
            else reqPayload[csrf.name] = csrf.val;
        }

        try {
            const reqOpt = { method: "POST", headers, credentials: "same-origin" };
            if (payloadType === "form") {
                headers["Content-Type"] = "application/x-www-form-urlencoded";
                reqOpt.body = new URLSearchParams(reqPayload).toString();
            } else {
                headers["Content-Type"] = "application/json";
                reqOpt.body = JSON.stringify(reqPayload);
            }

            const res = await fetch(targetUrl, reqOpt);
            console.log(\`[Vote #\${i}/\${maxVotes}] Status: \${res.status}\`);
        } catch (err) {
            console.error(\`[Vote #\${i}] Error:\`, err.message);
        }
        await new Promise(r => setTimeout(r, delayMs));
    }
    console.log("✅ Auto-Vote Loop Completed!");
})();`;

        navigator.clipboard.writeText(snippet);
        alert("✅ Đã copy Script JavaScript vào Clipboard! Hãy mở trang web bình chọn thật, nhấn F12 -> tab Console và dán vào.");
    });

    // Form Submit -> Start Auto-Vote
    voteForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const config = {
            url: document.getElementById('url').value,
            method: document.getElementById('method').value,
            payload_type: document.getElementById('payloadType').value,
            payload: document.getElementById('payload').value,
            concurrency: parseInt(document.getElementById('concurrency').value) || 5,
            delay_ms: parseInt(document.getElementById('delayMs').value) || 100,
            max_votes: parseInt(document.getElementById('maxVotes').value) || 0,
            expected_status: parseInt(document.getElementById('expectedStatus').value) || 200,
            rotate_ua: document.getElementById('rotateUa').checked,
            spoof_ip: document.getElementById('spoofIp').checked,
            custom_headers: document.getElementById('customHeaders').value,
            expected_keyword: document.getElementById('expectedKeyword').value,
            proxies: document.getElementById('proxies').value,
            fetch_csrf: document.getElementById('fetchCsrf').checked,
            csrf_page_url: document.getElementById('csrfPageUrl').value,
            csrf_param_name: document.getElementById('csrfParamName').value,
            csrf_location: document.getElementById('csrfLocation').value,
            csrf_regex: document.getElementById('csrfRegex').value,
            verify_ssl: document.getElementById('verifySsl').checked,
            keep_cookies: document.getElementById('keepCookies').checked
        };

        try {
            const res = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            const data = await res.json();
            if (res.ok) {
                setUIState(true);
                startPolling();
            } else {
                alert(data.message || "Failed to start campaign.");
            }
        } catch (err) {
            alert("Connection error: " + err.message);
        }
    });

    // Stop Campaign
    stopBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
            setUIState(false);
            stopPolling();
        } catch (err) {
            console.error("Stop error:", err);
        }
    });

    // Inspect Target Button (1 Vote Test)
    inspectBtn.addEventListener('click', async () => {
        const url = document.getElementById('url').value;
        if (!url) return alert("Vui lòng nhập Target URL trước.");

        inspectorBody.innerHTML = '<p><i class="fa-solid fa-spinner fa-spin"></i> Đang gửi 1 vote kiểm thử tới web mục tiêu...</p>';
        inspectorBox.classList.remove('hidden');

        try {
            const res = await fetch('/api/inspect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    method: document.getElementById('method').value,
                    payload_type: document.getElementById('payloadType').value,
                    payload: document.getElementById('payload').value
                })
            });
            const data = await res.json();

            let html = `<div>
                <p><strong>HTTP Status Code:</strong> <span class="${data.http_code === 200 ? 'text-green' : 'text-red'}">${data.http_code}</span></p>
                <p><strong>Phân tích Server:</strong> ${escapeHtml(data.analysis || '')}</p>
                <p class="mt-2"><strong>Cookies Server Trả Về:</strong></p>
                <pre>${JSON.stringify(data.cookies_set || {}, null, 2)}</pre>
                <p class="mt-2"><strong>Xem Trước Phản Hồi (Response Body):</strong></p>
                <pre>${escapeHtml(data.response_preview || '')}</pre>
            </div>`;
            inspectorBody.innerHTML = html;
        } catch (err) {
            inspectorBody.innerHTML = `<p class="text-red">Inspection failed: ${escapeHtml(err.message)}</p>`;
        }
    });

    function setUIState(isRunning) {
        if (isRunning) {
            startBtn.classList.add('hidden');
            stopBtn.classList.remove('hidden');
            statusDot.classList.add('running');
            statusText.innerText = "RUNNING";
            statusText.style.color = "#4ade80";
        } else {
            startBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            statusDot.classList.remove('running');
            statusText.innerText = "IDLE";
            statusText.style.color = "#94a3b8";
        }
    }

    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(fetchStatus, 800);
        fetchStatus();
    }

    function stopPolling() {
        if (pollInterval) clearInterval(pollInterval);
    }

    async function fetchStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            const speed = data.total_sent - lastTotalCount;
            lastTotalCount = data.total_sent;

            valTotal.innerText = (data.total_sent || 0).toLocaleString();
            valSuccess.innerText = (data.success_count || 0).toLocaleString();
            valFailed.innerText = (data.fail_count || 0).toLocaleString();
            valSpeed.innerText = `${speed > 0 ? speed : 0} v/s`;

            if (data.is_running !== (statusText.innerText === "RUNNING")) {
                setUIState(data.is_running);
            }

            if (data.logs && data.logs.length > 0) {
                renderLogs(data.logs);
            }

            if (!data.is_running && data.total_sent > 0) {
                stopPolling();
            }
        } catch (err) {
            console.error("Status poll error:", err);
        }
    }

    function renderLogs(logs) {
        logTerminal.innerHTML = '';
        logs.forEach(log => {
            const div = document.createElement('div');
            div.className = `log-entry ${log.status}`;
            div.innerText = `[${log.timestamp}] [${log.status}] ${log.message}`;
            logTerminal.appendChild(div);
        });

        if (autoscrollCheck.checked) {
            logTerminal.scrollTop = logTerminal.scrollHeight;
        }
    }

    function escapeHtml(text) {
        if (typeof text !== 'string') return '';
        return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    fetchStatus();
});
