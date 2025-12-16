"""
Monitor và Dashboard cho Rate Limits & Cache
Hiển thị real-time stats về API usage
"""
from flask import Blueprint, jsonify, render_template_string
import sys
from pathlib import Path

# Import utilities
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.rate_limiter import get_rate_limit_stats
from config.response_cache import get_all_cache_stats

# Blueprint
monitor_bp = Blueprint('monitor', __name__)


@monitor_bp.route('/api/stats')
def get_stats():
    """
    API endpoint để lấy stats
    """
    return jsonify({
        'rate_limits': get_rate_limit_stats(),
        'cache': get_all_cache_stats()
    })


@monitor_bp.route('/monitor')
def monitor_dashboard():
    """
    Dashboard hiển thị stats
    """
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>API Monitor Dashboard</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #fff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .section {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        .section h2 {
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }
        .stat-card {
            background: rgba(255,255,255,0.15);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-card h3 {
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #ffd700;
        }
        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .stat-item:last-child {
            border-bottom: none;
        }
        .stat-label {
            font-weight: 600;
        }
        .stat-value {
            font-weight: bold;
            color: #ffd700;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #00ccff);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85em;
            font-weight: bold;
        }
        .warning { color: #ffaa00 !important; }
        .danger { color: #ff4444 !important; }
        .success { color: #00ff88 !important; }
        .refresh-btn {
            background: rgba(255,255,255,0.2);
            border: 2px solid rgba(255,255,255,0.3);
            color: white;
            padding: 10px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            margin: 20px auto;
            display: block;
            transition: all 0.3s ease;
        }
        .refresh-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
        }
        .last-update {
            text-align: center;
            margin-top: 10px;
            opacity: 0.8;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 API Monitor Dashboard</h1>
        
        <div class="section">
            <h2>⏱️ Rate Limits - Gemini API</h2>
            <div class="stats-grid" id="gemini-stats"></div>
        </div>
        
        <div class="section">
            <h2>⏱️ Rate Limits - OpenAI</h2>
            <div class="stats-grid" id="openai-stats"></div>
        </div>
        
        <div class="section">
            <h2>💾 Response Cache</h2>
            <div class="stats-grid" id="cache-stats"></div>
        </div>
        
        <button class="refresh-btn" onclick="loadStats()">🔄 Refresh</button>
        <div class="last-update" id="last-update"></div>
    </div>
    
    <script>
        function loadStats() {
            fetch('/api/stats')
                .then(res => res.json())
                .then(data => {
                    renderGeminiStats(data.rate_limits.gemini);
                    renderOpenAIStats(data.rate_limits.openai);
                    renderCacheStats(data.cache);
                    
                    document.getElementById('last-update').textContent = 
                        'Last updated: ' + new Date().toLocaleString();
                })
                .catch(err => console.error('Error loading stats:', err));
        }
        
        function renderGeminiStats(gemini) {
            const container = document.getElementById('gemini-stats');
            container.innerHTML = '';
            
            Object.entries(gemini).forEach(([key, stats]) => {
                const card = document.createElement('div');
                card.className = 'stat-card';
                
                const usage = stats.usage_percentage;
                const statusClass = usage > 80 ? 'danger' : (usage > 60 ? 'warning' : 'success');
                
                card.innerHTML = `
                    <h3>${key.toUpperCase()}</h3>
                    <div class="stat-item">
                        <span class="stat-label">Current Requests:</span>
                        <span class="stat-value ${statusClass}">${stats.current_requests}/${stats.max_requests}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Available:</span>
                        <span class="stat-value success">${stats.available_requests}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Time Window:</span>
                        <span class="stat-value">${stats.time_window}s</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${usage}%">
                            ${usage.toFixed(1)}%
                        </div>
                    </div>
                `;
                
                container.appendChild(card);
            });
        }
        
        function renderOpenAIStats(openai) {
            const container = document.getElementById('openai-stats');
            const card = document.createElement('div');
            card.className = 'stat-card';
            
            const usage = openai.usage_percentage;
            const statusClass = usage > 80 ? 'danger' : (usage > 60 ? 'warning' : 'success');
            
            card.innerHTML = `
                <h3>OPENAI GPT-4O-MINI</h3>
                <div class="stat-item">
                    <span class="stat-label">Current Requests:</span>
                    <span class="stat-value ${statusClass}">${openai.current_requests}/${openai.max_requests}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Available:</span>
                    <span class="stat-value success">${openai.available_requests}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Time Window:</span>
                    <span class="stat-value">${openai.time_window}s</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${usage}%">
                        ${usage.toFixed(1)}%
                    </div>
                </div>
            `;
            
            container.innerHTML = '';
            container.appendChild(card);
        }
        
        function renderCacheStats(cache) {
            const container = document.getElementById('cache-stats');
            container.innerHTML = '';
            
            Object.entries(cache).forEach(([key, stats]) => {
                const card = document.createElement('div');
                card.className = 'stat-card';
                
                const hitRate = stats.hit_rate_percentage;
                const statusClass = hitRate > 70 ? 'success' : (hitRate > 40 ? 'warning' : 'danger');
                
                card.innerHTML = `
                    <h3>${key.toUpperCase()}</h3>
                    <div class="stat-item">
                        <span class="stat-label">Cache Size:</span>
                        <span class="stat-value">${stats.size}/${stats.max_size}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Cache Hits:</span>
                        <span class="stat-value success">${stats.hits}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Cache Misses:</span>
                        <span class="stat-value danger">${stats.misses}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Hit Rate:</span>
                        <span class="stat-value ${statusClass}">${hitRate}%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">TTL:</span>
                        <span class="stat-value">${stats.ttl_seconds}s</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${hitRate}%">
                            ${hitRate}%
                        </div>
                    </div>
                `;
                
                container.appendChild(card);
            });
        }
        
        // Auto refresh every 5 seconds
        loadStats();
        setInterval(loadStats, 5000);
    </script>
</body>
</html>
    """
    return render_template_string(html)


def register_monitor(app):
    """
    Register monitor blueprint vào Flask app
    
    Usage:
        from config.monitor import register_monitor
        register_monitor(app)
    """
    app.register_blueprint(monitor_bp)
    print("✅ Monitor Dashboard registered at /monitor")
