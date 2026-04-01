from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
import os
import json
from datetime import datetime
import redis as redis_lib
import anthropic

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
try:
    redis_client = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
except redis_lib.exceptions.ConnectionError as e:
    print(f"Warning: Could not connect to Redis at startup: {e}")
    redis_client = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# Flask/SQLAlchemy app setup
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a4f8c2e6b9d1f5a7c3e8b2d6f1a9c4e7b5d2f8a6c1e9b3d7f2a5c8e4b1d6f9a3')
db = SQLAlchemy(app)

# --- Authentication ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

_LOGIN_USERNAME = os.getenv('LOGIN_USERNAME', '')
_LOGIN_PASSWORD_HASH = generate_password_hash(os.getenv('LOGIN_PASSWORD', ''))

class AppUser(UserMixin):
    def get_id(self):
        return 'admin'

_app_user = AppUser()

@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return _app_user
    return None

@app.before_request
def require_login():
    if not current_user.is_authenticated and request.endpoint not in ('login', 'static'):
        return redirect(url_for('login', next=request.path))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == _LOGIN_USERNAME and _LOGIN_USERNAME and check_password_hash(_LOGIN_PASSWORD_HASH, password):
            login_user(_app_user)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/') or next_page.startswith('//'):
                next_page = url_for('index')
            return redirect(next_page)
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))
# --- End Authentication ---


# Claude model config
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")


# Database Models
class Game(db.Model):
    __tablename__ = 'games'
    
    game_id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    started_at = db.Column(db.Date)
    finished_at = db.Column(db.Date)
    perspective_id = db.Column(db.Integer, db.ForeignKey('perspectives.perspective_id'), nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('platforms.platform_id'), nullable=False)
    finished = db.Column(db.Boolean, default=False, nullable=False)
    playtime = db.Column(db.Numeric)
    release_year = db.Column(db.SmallInteger)
    played_year = db.Column(db.SmallInteger)
    comments = db.Column(db.Text)
    personal_score = db.Column(db.SmallInteger)
    personal_review = db.Column(db.Text)
    
    # Relationships
    perspective = db.relationship('Perspective', backref='games')
    platform = db.relationship('Platform', backref='games')
    tags = db.relationship('CategoryTag', secondary='game_category_tags', backref='games')


class Perspective(db.Model):
    __tablename__ = 'perspectives'
    
    perspective_id = db.Column(db.Integer, primary_key=True)
    perspective_name = db.Column(db.String(50), unique=True)


class Platform(db.Model):
    __tablename__ = 'platforms'
    
    platform_id = db.Column(db.Integer, primary_key=True)
    platform_name = db.Column(db.String(50), unique=True)


class CategoryTag(db.Model):
    __tablename__ = 'category_tags'
    
    tag_id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(50), unique=True)


class GameCategoryTag(db.Model):
    __tablename__ = 'game_category_tags'
    
    tag_id = db.Column(db.Integer, db.ForeignKey('category_tags.tag_id'), primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.game_id'), primary_key=True)


# Routes - Games
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filters
    finished_filter = request.args.get('finished', '')
    platform_filter = request.args.get('platform', '')
    perspective_filter = request.args.get('perspective', '')
    tag_filter = request.args.get('tag', '')
    release_year_filter = request.args.get('release_year', '')
    played_year_filter = request.args.get('played_year', '')
    
    # Sorting
    sort_by = request.args.get('sort', 'game_id')
    sort_order = request.args.get('order', 'desc')
    
    query = Game.query
    
    if finished_filter == 'yes':
        query = query.filter(Game.finished == True)
    elif finished_filter == 'no':
        query = query.filter(Game.finished == False)
    
    if platform_filter:
        query = query.filter(Game.platform_id == platform_filter)
    
    if perspective_filter:
        query = query.filter(Game.perspective_id == perspective_filter)
    
    if tag_filter:
        query = query.join(Game.tags).filter(CategoryTag.tag_id == tag_filter)

    if release_year_filter:
        query = query.filter(Game.release_year == release_year_filter)

    if played_year_filter:
        query = query.filter(Game.played_year == played_year_filter)

    # Apply sorting
    if sort_by == 'name':
        order_column = Game.name
    elif sort_by == 'playtime':
        order_column = Game.playtime
    elif sort_by == 'finished':
        order_column = Game.finished
    elif sort_by == 'finished_at':
        order_column = Game.finished_at
    elif sort_by == 'started_at':
        order_column = Game.started_at
    elif sort_by == 'release_year':
        order_column = Game.release_year
    elif sort_by == 'played_year':
        order_column = Game.played_year
    elif sort_by == 'platform':
        query = query.join(Platform)
        order_column = Platform.platform_name
    elif sort_by == 'perspective':
        query = query.join(Perspective)
        order_column = Perspective.perspective_name
    else:  # default to game_id
        order_column = Game.game_id
    
    if sort_order == 'asc':
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())
    
    games = query.paginate(page=page, per_page=per_page, error_out=False)
    
    platforms = Platform.query.all()
    perspectives = Perspective.query.all()
    tags = CategoryTag.query.order_by(CategoryTag.tag_name).all()
    release_years = [r[0] for r in db.session.query(Game.release_year).filter(Game.release_year.isnot(None)).distinct().order_by(Game.release_year.asc()).all()]
    played_years = [r[0] for r in db.session.query(Game.played_year).filter(Game.played_year.isnot(None)).distinct().order_by(Game.played_year.asc()).all()]

    return render_template('index.html',
                         games=games,
                         platforms=platforms,
                         perspectives=perspectives,
                         tags=tags,
                         release_years=release_years,
                         played_years=played_years,
                         finished_filter=finished_filter,
                         platform_filter=platform_filter,
                         perspective_filter=perspective_filter,
                         tag_filter=tag_filter,
                         release_year_filter=release_year_filter,
                         played_year_filter=played_year_filter,
                         sort_by=sort_by,
                         sort_order=sort_order)


@app.route('/game/<int:id>')
def view_game(id):
    game = Game.query.get_or_404(id)
    ai_info = None
    try:
        cached = redis_client.get(f"game_info:{game.game_id}")
        if cached:
            ai_info = json.loads(cached)
    except redis_lib.exceptions.ConnectionError:
        pass
    return render_template('view_game.html', game=game, ai_info=ai_info)


@app.route('/game/create', methods=['GET', 'POST'])
def create_game():
    if request.method == 'POST':
        # Parse started_at date
        started_at_str = request.form.get('started_at')
        started_at = None
        if started_at_str:
            try:
                started_at = datetime.strptime(started_at_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
                return redirect(url_for('create_game'))

        # Parse finished_at date
        finished_at_str = request.form.get('finished_at')
        finished_at = None
        if finished_at_str:
            try:
                finished_at = datetime.strptime(finished_at_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
                return redirect(url_for('create_game'))
        
        game = Game(
            name=request.form.get('name'),
            started_at=started_at,
            finished_at=finished_at,
            perspective_id=request.form.get('perspective_id'),
            platform_id=request.form.get('platform_id'),
            finished=request.form.get('finished') == 'on',
            playtime=request.form.get('playtime') if request.form.get('playtime') else None,
            release_year=request.form.get('release_year') if request.form.get('release_year') else None,
            played_year=request.form.get('played_year') if request.form.get('played_year') else None,
            comments=request.form.get('comments') if request.form.get('comments') else None,
            personal_score=request.form.get('personal_score') if request.form.get('personal_score') else None,
            personal_review=request.form.get('personal_review') if request.form.get('personal_review') else None
        )
        
        db.session.add(game)
        db.session.flush()
        
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            game_tag = GameCategoryTag(game_id=game.game_id, tag_id=tag_id)
            db.session.add(game_tag)
        
        db.session.commit()
        flash('Game created successfully!', 'success')
        return redirect(url_for('view_game', id=game.game_id))
    
    platforms = Platform.query.all()
    perspectives = Perspective.query.all()
    tags = CategoryTag.query.all()
    
    return render_template('create_game.html', platforms=platforms, perspectives=perspectives, tags=tags)


@app.route('/game/edit/<int:id>', methods=['GET', 'POST'])
def edit_game(id):
    game = Game.query.get_or_404(id)
    
    if request.method == 'POST':
        # Parse started_at date
        started_at_str = request.form.get('started_at')
        started_at = None
        if started_at_str:
            try:
                started_at = datetime.strptime(started_at_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
                return redirect(url_for('edit_game', id=id))

        # Parse finished_at date
        finished_at_str = request.form.get('finished_at')
        finished_at = None
        if finished_at_str:
            try:
                finished_at = datetime.strptime(finished_at_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD', 'danger')
                return redirect(url_for('edit_game', id=id))
        
        game.name = request.form.get('name')
        game.started_at = started_at
        game.finished_at = finished_at
        game.perspective_id = request.form.get('perspective_id')
        game.platform_id = request.form.get('platform_id')
        game.finished = request.form.get('finished') == 'on'
        game.playtime = request.form.get('playtime') if request.form.get('playtime') else None
        game.release_year = request.form.get('release_year') if request.form.get('release_year') else None
        game.played_year = request.form.get('played_year') if request.form.get('played_year') else None
        game.comments = request.form.get('comments') if request.form.get('comments') else None
        game.personal_score = request.form.get('personal_score') if request.form.get('personal_score') else None
        game.personal_review = request.form.get('personal_review') if request.form.get('personal_review') else None
                
        GameCategoryTag.query.filter_by(game_id=game.game_id).delete()
        
        tag_ids = request.form.getlist('tags')
        for tag_id in tag_ids:
            game_tag = GameCategoryTag(game_id=game.game_id, tag_id=tag_id)
            db.session.add(game_tag)
        
        db.session.commit()
        flash('Game updated successfully!', 'success')
        return redirect(url_for('view_game', id=id))
    
    platforms = Platform.query.all()
    perspectives = Perspective.query.all()
    tags = CategoryTag.query.all()
    current_tag_ids = [gt.tag_id for gt in GameCategoryTag.query.filter_by(game_id=game.game_id).all()]
    
    return render_template('edit_game.html', game=game, platforms=platforms, perspectives=perspectives, tags=tags, current_tag_ids=current_tag_ids)


@app.route('/game/delete/<int:id>', methods=['POST'])
def delete_game(id):
    game = Game.query.get_or_404(id)
    GameCategoryTag.query.filter_by(game_id=id).delete()
    db.session.delete(game)
    db.session.commit()
    flash('Game deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/search')
def search():
    """Search games."""
    query = request.args.get('q', '')
    
    if query:
        games = Game.query.filter(
            or_(
                Game.name.ilike(f'%{query}%'),
                Game.comments.ilike(f'%{query}%')
            )
        ).all()
    else:
        games = []
    
    return render_template('search.html', games=games, query=query)

# Platform routes
@app.route('/platforms')
def platforms():
    platforms = Platform.query.all()
    return render_template('platforms.html', platforms=platforms)


@app.route('/platform/create', methods=['GET', 'POST'])
def create_platform():
    if request.method == 'POST':
        platform = Platform(platform_name=request.form.get('platform_name'))
        db.session.add(platform)
        db.session.commit()
        flash('Platform created successfully!', 'success')
        return redirect(url_for('platforms'))
    return render_template('create_platform.html')


@app.route('/platform/edit/<int:id>', methods=['GET', 'POST'])
def edit_platform(id):
    platform = Platform.query.get_or_404(id)
    if request.method == 'POST':
        platform.platform_name = request.form.get('platform_name')
        db.session.commit()
        flash('Platform updated successfully!', 'success')
        return redirect(url_for('platforms'))
    return render_template('edit_platform.html', platform=platform)


@app.route('/platform/delete/<int:id>', methods=['POST'])
def delete_platform(id):
    platform = Platform.query.get_or_404(id)
    if platform.games:
        flash('Cannot delete platform - games are using it!', 'danger')
        return redirect(url_for('platforms'))
    db.session.delete(platform)
    db.session.commit()
    flash('Platform deleted successfully!', 'success')
    return redirect(url_for('platforms'))


# Perspective routes
@app.route('/perspectives')
def perspectives():
    perspectives = Perspective.query.all()
    return render_template('perspectives.html', perspectives=perspectives)


@app.route('/perspective/create', methods=['GET', 'POST'])
def create_perspective():
    if request.method == 'POST':
        perspective = Perspective(perspective_name=request.form.get('perspective_name'))
        db.session.add(perspective)
        db.session.commit()
        flash('Perspective created successfully!', 'success')
        return redirect(url_for('perspectives'))
    return render_template('create_perspective.html')


@app.route('/perspective/edit/<int:id>', methods=['GET', 'POST'])
def edit_perspective(id):
    perspective = Perspective.query.get_or_404(id)
    if request.method == 'POST':
        perspective.perspective_name = request.form.get('perspective_name')
        db.session.commit()
        flash('Perspective updated successfully!', 'success')
        return redirect(url_for('perspectives'))
    return render_template('edit_perspective.html', perspective=perspective)


@app.route('/perspective/delete/<int:id>', methods=['POST'])
def delete_perspective(id):
    perspective = Perspective.query.get_or_404(id)
    if perspective.games:
        flash('Cannot delete perspective - games are using it!', 'danger')
        return redirect(url_for('perspectives'))
    db.session.delete(perspective)
    db.session.commit()
    flash('Perspective deleted successfully!', 'success')
    return redirect(url_for('perspectives'))


# Tag routes
@app.route('/tags')
def tags():
    tags = CategoryTag.query.all()
    return render_template('tags.html', tags=tags)


@app.route('/tag/create', methods=['GET', 'POST'])
def create_tag():
    if request.method == 'POST':
        tag = CategoryTag(tag_name=request.form.get('tag_name'))
        db.session.add(tag)
        db.session.commit()
        flash('Tag created successfully!', 'success')
        return redirect(url_for('tags'))
    return render_template('create_tag.html')


@app.route('/tag/edit/<int:id>', methods=['GET', 'POST'])
def edit_tag(id):
    tag = CategoryTag.query.get_or_404(id)
    if request.method == 'POST':
        tag.tag_name = request.form.get('tag_name')
        db.session.commit()
        flash('Tag updated successfully!', 'success')
        return redirect(url_for('tags'))
    return render_template('edit_tag.html', tag=tag)


@app.route('/tag/delete/<int:id>', methods=['POST'])
def delete_tag(id):
    tag = CategoryTag.query.get_or_404(id)
    GameCategoryTag.query.filter_by(tag_id=id).delete()
    db.session.delete(tag)
    db.session.commit()
    flash('Tag deleted successfully!', 'success')
    return redirect(url_for('tags'))


# Comments timeline
@app.route('/comments')
def comments():
    games = Game.query.filter(
        Game.comments.isnot(None),
        Game.comments != ''
    ).order_by(
        Game.played_year.desc().nulls_last(),
        Game.name.asc()
    ).all()

    grouped = {}
    for game in games:
        year = game.played_year
        grouped.setdefault(year, []).append(game)

    timeline_data = sorted(
        grouped.items(),
        key=lambda x: (x[0] is None, -(x[0] or 0))
    )

    return render_template('comments.html',
                           timeline=timeline_data,
                           total_games=len(games))


# Timeline
@app.route('/timeline')
def timeline():
    from itertools import groupby
    games = Game.query.order_by(
        Game.played_year.desc().nulls_last(),
        Game.name.asc()
    ).all()

    grouped = {}
    for game in games:
        year = game.played_year
        grouped.setdefault(year, []).append(game)

    # Sort: years descending, None last
    timeline_data = sorted(
        grouped.items(),
        key=lambda x: (x[0] is None, -(x[0] or 0))
    )

    return render_template('timeline.html',
                           timeline=timeline_data,
                           total_games=len(games))


# Stats
@app.route('/stats')
def stats():
    total_games = Game.query.count()
    finished_games = Game.query.filter_by(finished=True).count()
    total_playtime = db.session.query(db.func.sum(Game.playtime)).scalar() or 0
    
    platform_stats = db.session.query(
        Platform.platform_name,
        db.func.count(Game.game_id).label('count')
    ).join(Game).group_by(Platform.platform_name).all()
    
    perspective_stats = db.session.query(
        Perspective.perspective_name,
        db.func.count(Game.game_id).label('count')
    ).join(Game).group_by(Perspective.perspective_name).all()

    games = Game.query.options(
        joinedload(Game.platform),
        joinedload(Game.perspective),
        joinedload(Game.tags)
    ).all()

    hours_per_year = {}
    hours_per_platform = {}
    hours_per_perspective = {}
    hours_per_tag = {}

    for game in games:
        hours = float(game.playtime or 0)
        year_label = str(game.played_year) if game.played_year is not None else 'Unknown'
        platform_label = game.platform.platform_name if game.platform else 'Unknown'
        perspective_label = game.perspective.perspective_name if game.perspective else 'Unknown'

        hours_per_year[year_label] = hours_per_year.get(year_label, 0) + hours
        hours_per_platform[platform_label] = hours_per_platform.get(platform_label, 0) + hours
        hours_per_perspective[perspective_label] = hours_per_perspective.get(perspective_label, 0) + hours

        if game.tags:
            for tag in game.tags:
                tag_label = tag.tag_name if tag.tag_name else 'Unknown'
                hours_per_tag[tag_label] = hours_per_tag.get(tag_label, 0) + hours
        else:
            hours_per_tag['Untagged'] = hours_per_tag.get('Untagged', 0) + hours

    def serialize_chart_data(source, sort_years=False):
        if sort_years:
            sorted_items = sorted(
                source.items(),
                key=lambda item: (item[0] == 'Unknown', int(item[0]) if item[0].isdigit() else 9999)
            )
        else:
            sorted_items = sorted(source.items(), key=lambda item: item[0].lower())
        return [{'label': key, 'value': round(value, 2)} for key, value in sorted_items]
    
    return render_template('stats.html',
                         total_games=total_games,
                         finished_games=finished_games,
                         total_playtime=total_playtime,
                         platform_stats=platform_stats,
                         perspective_stats=perspective_stats,
                         hours_per_year=serialize_chart_data(hours_per_year, sort_years=True),
                         hours_per_platform=serialize_chart_data(hours_per_platform),
                         hours_per_perspective=serialize_chart_data(hours_per_perspective),
                         hours_per_tag=serialize_chart_data(hours_per_tag))


# Claude AI helpers
def fetch_game_info_from_claude(game_name, release_year=None):
    """Fetch game description and Metacritic score from Claude."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)
    year_info = f" (released in {release_year})" if release_year else ""
    prompt = (
        f'For the video game "{game_name}"{year_info}, return ONLY a JSON object '
        f'with these fields:\n'
        f'{{"description": "1-2 sentence description", '
        f'"metacritic_score": <integer 0-100 or null>, '
        f'"avg_playtime_hours": <average community main-story playtime in hours as a number or null>}}\n'
        f'No markdown, no extra text — JSON only.'
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text.strip()
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.splitlines()
        response_text = "\n".join(lines[1:-1]).strip()

    data = json.loads(response_text)

    # Normalize metacritic_score to int or None
    raw_score = data.get("metacritic_score")
    if raw_score is None or raw_score == "" or raw_score == "null":
        data["metacritic_score"] = None
    else:
        try:
            data["metacritic_score"] = int(raw_score)
        except (ValueError, TypeError):
            data["metacritic_score"] = None

    # Normalize avg_playtime_hours to float or None
    raw_playtime = data.get("avg_playtime_hours")
    if raw_playtime is None or raw_playtime == "" or raw_playtime == "null":
        data["avg_playtime_hours"] = None
    else:
        try:
            data["avg_playtime_hours"] = round(float(raw_playtime), 1)
        except (ValueError, TypeError):
            data["avg_playtime_hours"] = None

    data["fetched_at"] = datetime.now().isoformat()
    return data


# AI Game Info routes
@app.route('/game_info')
def game_info():
    games = Game.query.order_by(Game.name.asc()).all()
    games_with_info = []
    redis_available = True
    for game in games:
        info = None
        try:
            cached = redis_client.get(f"game_info:{game.game_id}")
            if cached:
                info = json.loads(cached)
        except redis_lib.exceptions.ConnectionError:
            redis_available = False
            break
        games_with_info.append((game, info))

    if not redis_available:
        flash("Redis is not available. Cannot load cached game info.", "danger")
        games_with_info = [(g, None) for g in games]

    total = len(games_with_info)
    cached_count = sum(1 for _, info in games_with_info if info)
    return render_template('game_info.html',
                           games_with_info=games_with_info,
                           total=total,
                           cached_count=cached_count)


@app.route('/game_info/fetch/<int:game_id>', methods=['POST'])
def fetch_single_game_info(game_id):
    game = Game.query.get_or_404(game_id)
    next_url = request.args.get('next')
    if not next_url or not next_url.startswith('/') or next_url.startswith('//'):
        next_url = url_for('game_info')
    if not os.getenv("ANTHROPIC_API_KEY"):
        flash("ANTHROPIC_API_KEY is not set. Please configure the environment variable.", "danger")
        return redirect(next_url)
    try:
        info = fetch_game_info_from_claude(game.name, game.release_year)
        redis_client.set(f"game_info:{game.game_id}", json.dumps(info))
        flash(f"Info for \"{game.name}\" fetched successfully!", "success")
    except redis_lib.exceptions.ConnectionError:
        flash("Redis is not available. Cannot store game info.", "danger")
    except Exception as e:
        flash(f"Error fetching info for \"{game.name}\": {e}", "danger")
    return redirect(next_url)


@app.route('/game_info/fetch_new', methods=['POST'])
def fetch_new_game_info():
    if not os.getenv("ANTHROPIC_API_KEY"):
        flash("ANTHROPIC_API_KEY is not set. Please configure the environment variable.", "danger")
        return redirect(url_for('game_info'))
    games = Game.query.order_by(Game.game_id.asc()).all()
    fetched_count = 0
    error_count = 0
    for game in games:
        try:
            cached = redis_client.get(f"game_info:{game.game_id}")
        except redis_lib.exceptions.ConnectionError:
            flash("Redis is not available. Cannot fetch game info.", "danger")
            return redirect(url_for('game_info'))
        if cached:
            continue
        try:
            info = fetch_game_info_from_claude(game.name, game.release_year)
            redis_client.set(f"game_info:{game.game_id}", json.dumps(info))
            fetched_count += 1
        except Exception as e:
            print(f"Error fetching info for game {game.game_id} ({game.name}): {e}")
            error_count += 1

    if fetched_count > 0:
        flash(f"Fetched info for {fetched_count} new game(s).", "success")
    else:
        flash("No new games without cached info found.", "info")
    if error_count > 0:
        flash(f"Failed to fetch info for {error_count} game(s).", "danger")
    return redirect(url_for('game_info'))


# CSV Export
@app.route('/export/games.csv')
def export_games_csv():
    import csv
    import io

    finished_filter = request.args.get('finished', '')
    platform_filter = request.args.get('platform', '')
    perspective_filter = request.args.get('perspective', '')
    tag_filter = request.args.get('tag', '')
    release_year_filter = request.args.get('release_year', '')
    played_year_filter = request.args.get('played_year', '')

    query = Game.query.options(
        joinedload(Game.platform),
        joinedload(Game.perspective),
        joinedload(Game.tags)
    )

    if finished_filter == 'yes':
        query = query.filter(Game.finished == True)
    elif finished_filter == 'no':
        query = query.filter(Game.finished == False)
    if platform_filter:
        query = query.filter(Game.platform_id == platform_filter)
    if perspective_filter:
        query = query.filter(Game.perspective_id == perspective_filter)
    if tag_filter:
        query = query.join(Game.tags).filter(CategoryTag.tag_id == tag_filter)
    if release_year_filter:
        query = query.filter(Game.release_year == release_year_filter)
    if played_year_filter:
        query = query.filter(Game.played_year == played_year_filter)

    games = query.order_by(Game.game_id.asc()).all()

    # Load cached AI info from Redis for matched games
    ai_cache = {}
    try:
        for game in games:
            cached = redis_client.get(f"game_info:{game.game_id}")
            if cached:
                ai_cache[game.game_id] = json.loads(cached)
    except redis_lib.exceptions.ConnectionError:
        pass

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'game_id', 'name', 'release_year', 'played_year',
        'platform', 'perspective', 'tags',
        'playtime_hours', 'finished', 'started_at', 'finished_at', 'comments',
        'ai_description', 'metacritic_score', 'avg_playtime_hours', 'ai_fetched_at'
    ])

    for game in games:
        ai = ai_cache.get(game.game_id, {})
        writer.writerow([
            game.game_id,
            game.name,
            game.release_year or '',
            game.played_year or '',
            game.platform.platform_name if game.platform else '',
            game.perspective.perspective_name if game.perspective else '',
            '|'.join(t.tag_name for t in game.tags),
            game.playtime or '',
            game.finished,
            game.started_at.isoformat() if game.started_at else '',
            game.finished_at.isoformat() if game.finished_at else '',
            game.comments or '',
            ai.get('description', ''),
            ai.get('metacritic_score', ''),
            ai.get('avg_playtime_hours', ''),
            (ai.get('fetched_at', '')[:19].replace('T', ' ')) if ai.get('fetched_at') else '',
        ])

    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=games_{timestamp}.csv'}
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')