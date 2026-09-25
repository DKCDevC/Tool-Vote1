"""
Mock Level 1 Voting Server
Provides a realistic test endpoint that blocks repeat votes using Cookie/Session.
Run this server to test the Auto-Vote tool locally!
"""

from flask import Flask, request, jsonify, make_response, render_template_string
import time

app = Flask(__name__)

# In-memory vote counts
vote_counts = {
    "option_1": 0,
    "option_2": 0,
    "option_3": 0
}

VOTE_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Level 1 Test Voting Site</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; text-align: center; padding: 40px 20px; }
        .card { max-width: 500px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; margin-bottom: 8px; }
        p { color: #94a3b8; font-size: 0.95rem; }
        .vote-btn { background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; margin: 10px; transition: all 0.2s; }
        .vote-btn:hover { background: #2563eb; transform: translateY(-2px); }
        .counter { font-size: 2.5rem; font-weight: 800; color: #4ade80; margin: 15px 0; }
        .badge { display: inline-block; background: #334155; padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; color: #cbd5e1; }
        .clear-btn { background: #ef4444; margin-top: 15px; }
        .clear-btn:hover { background: #dc2626; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔒 Target Voting System (Level 1)</h1>
        <p>This site tracks votes using <code>Cookie</code> & <code>LocalStorage</code>.</p>
        
        <div class="counter" id="totalVotes">0</div>
        <p>Total Level 1 Votes Received</p>

        <div>
            <button class="vote-btn" onclick="vote('option_1')">Vote Option A</button>
            <button class="vote-btn" onclick="vote('option_2')">Vote Option B</button>
        </div>

        <p><span class="badge" id="statusBadge">Status: Ready to vote</span></p>

        <button class="vote-btn clear-btn" onclick="clearLocalState()">Manual Cookie & LocalStorage Clear</button>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('totalVotes').innerText = data.total_votes;
                });
        }

        function vote(optionId) {
            if (localStorage.getItem('has_voted') === 'true') {
                document.getElementById('statusBadge').innerText = 'Blocked by LocalStorage!';
                document.getElementById('statusBadge').style.background = '#991b1b';
                alert('You have already voted (LocalStorage detected)!');
                return;
            }

            fetch('/api/vote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ option_id: optionId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    localStorage.setItem('has_voted', 'true');
                    document.getElementById('statusBadge').innerText = 'Vote Counted!';
                    document.getElementById('statusBadge').style.background = '#166534';
                    updateStats();
                } else {
                    document.getElementById('statusBadge').innerText = 'Blocked by Cookie!';
                    document.getElementById('statusBadge').style.background = '#991b1b';
                    alert(data.message);
                }
            });
        }

        function clearLocalState() {
            localStorage.clear();
            document.cookie = "voted_cookie=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            document.getElementById('statusBadge').innerText = 'State cleared! You can vote again.';
            document.getElementById('statusBadge').style.background = '#334155';
        }

        setInterval(updateStats, 1000);
        updateStats();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(VOTE_PAGE_HTML)

@app.route("/api/stats", methods=["GET"])
def stats():
    total = sum(vote_counts.values())
    return jsonify({"total_votes": total, "breakdown": vote_counts})

@app.route("/api/vote", methods=["POST"])
def api_vote():
    # Check if request has the Level 1 cookie
    voted_cookie = request.cookies.get("voted_cookie")
    if voted_cookie == "true":
        return jsonify({
            "status": "error",
            "message": "LEVEL 1 BLOCK: Cookie 'voted_cookie=true' found! Repeat vote rejected."
        }), 400

    # Read vote option
    data = request.get_json(silent=True) or {}
    option_id = data.get("option_id", "option_1")
    
    if option_id not in vote_counts:
        vote_counts[option_id] = 0
    vote_counts[option_id] += 1

    total = sum(vote_counts.values())
    
    response = make_response(jsonify({
        "status": "success",
        "message": f"Vote registered successfully for {option_id}!",
        "total_votes": total,
        "option_votes": vote_counts[option_id]
    }), 200)

    # Set Level 1 Cookie to block future requests from same browser session
    response.set_cookie("voted_cookie", "true", max_age=86400)
    return response

@app.route("/api/reset", methods=["POST"])
def reset_votes():
    for key in vote_counts:
        vote_counts[key] = 0
    return jsonify({"status": "success", "message": "Votes reset to 0"})

if __name__ == "__main__":
    print("==================================================================")
    print("[+] Mock Level 1 Target Voting Site is running!")
    print("    URL: http://127.0.0.1:8080")
    print("    Vote Endpoint: http://127.0.0.1:8080/api/vote")
    print("==================================================================")
    app.run(host="127.0.0.1", port=8080, debug=False)
