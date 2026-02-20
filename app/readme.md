# Gaming Database Flask App - Setup Instructions

## Prerequisites
- Python 3.8+
- PostgreSQL database
- Your gaming database already set up

## Installation Steps

### 1. Create project directory
```bash
mkdir gaming_app
cd gaming_app
```

### 2. Create virtual environment
```bash
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure database connection

Edit `app.py` line 8:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://USERNAME:PASSWORD@localhost/DATABASE_NAME'
```

Replace:
- `USERNAME` with your PostgreSQL username
- `PASSWORD` with your PostgreSQL password
- `DATABASE_NAME` with your database name (probably `gaming`)

### 5. Run the application
```bash
python app.py
```

### 6. Open in browser
Visit: http://localhost:5000

## Features

✅ **Games Management**
- View all games with pagination
- Filter by status, platform, perspective
- Create, edit, delete games
- Assign multiple tags to games

✅ **Platforms Management**
- View all platforms
- Create, edit, delete platforms
- See game count per platform

✅ **Perspectives Management**
- View all perspectives
- Create, edit, delete perspectives
- See game count per perspective

✅ **Tags Management**
- View all category tags
- Create, edit, delete tags
- See game count per tag

✅ **Statistics**
- Total games count
- Finished games count
- Total playtime
- Completion rate
- Games by platform/perspective

✅ **Search**
- Search games by name or category

## Database Connection Issues?

If you get connection errors:

1. Check PostgreSQL is running
2. Verify database credentials
3. Ensure database exists
4. Check firewall settings

## Production Deployment

For production use:
1. Change `SECRET_KEY` to a random string
2. Set `debug=False` in app.py
3. Use a production WSGI server (gunicorn, uWSGI)
4. Set up proper environment variables for sensitive data