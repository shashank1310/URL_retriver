# Shareable Link Click Tracker

This is a Flask-based web app that lets you generate shareable links and tracks user locations when clicked. It logs and stores user geolocation (from browser GPS or IP) in a SQLite database.

## 🌟 Features
- Generate unique shareable links
- Track link click counts
- Retrieve user geolocation (browser GPS + IP fallback)
- Store detailed location data with addresses
- Real-time admin dashboard
- Multiple geolocation API fallbacks

## 🚀 Live Demo
*Add your deployment URL here after hosting*

## 📱 How It Works
1. Create a shareable link
2. When someone clicks it:
   - Requests browser location (GPS)
   - Falls back to IP geolocation if denied
   - Resolves full street address
   - Logs everything to database
   - Redirects to YouTube

## 🛠️ Local Development

### Prerequisites
- Python 3.8+
- pip

### Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd <your-repo-name>

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Visit [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 🌐 Deployment

### Railway.app (Recommended)
1. Push code to GitHub
2. Visit [railway.app](https://railway.app)
3. Connect GitHub and select repo
4. Automatic deployment!

### Render.com
1. Visit [render.com](https://render.com)
2. Create new Web Service
3. Connect GitHub repo
4. Build: `pip install -r requirements.txt`
5. Start: `gunicorn wsgi:app`

### Other Options
- **Fly.io:** `flyctl launch && flyctl deploy`
- **PythonAnywhere:** Upload files + create web app
- **Heroku:** `git push heroku main` (requires paid plan)

## 🗂️ Project Structure
```
├── app.py              # Main Flask application
├── wsgi.py             # WSGI entry point
├── requirements.txt    # Python dependencies
├── Procfile           # Deployment configuration
├── runtime.txt        # Python version
├── events.db          # SQLite database (auto-created)
└── README.md          # This file
```

## 🔧 Configuration

### Environment Variables
- `PORT` - Server port (auto-set by hosting platforms)
- `RAILWAY_ENVIRONMENT` - Detected automatically on Railway
- `RENDER` - Detected automatically on Render

### Database
- **Development:** `events.db` (local file)
- **Production:** Auto-configured per platform

## 📊 Admin Dashboard
Visit `/events` to see:
- All location events
- IP addresses and locations
- Browser GPS vs IP geolocation data
- Full street addresses
- Real-time updates

## 🛡️ Privacy & Security
- Location data stored locally in your database
- User consent required for precise GPS location
- IP-based fallback for users who decline
- No external data sharing

## 🆓 Free Hosting Options
1. **Railway.app** - $5 monthly credit (recommended)
2. **Render.com** - Always free with sleep mode
3. **Fly.io** - 256MB RAM free tier
4. **PythonAnywhere** - Basic free hosting

## 🔗 APIs Used
- **reallyfreegeoip.org** - Primary IP geolocation
- **ip-api.com** - Backup IP geolocation
- **ipapi.co** - Secondary backup
- **OpenStreetMap Nominatim** - Address resolution

## 📝 License
MIT License - Feel free to use and modify!

---
**Note:** This is a proof-of-concept app. For production use with high traffic, consider upgrading to paid hosting and a more robust database. 