from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import os
from datetime import datetime

# Read DB config from environment
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a4f8c2e6b9d1f5a7c3e8b2d6f1a9c4e7b5d2f8a6c1e9b3d7f2a5c8e4b1d6f9a3'

db = SQLAlchemy(app)

# Database Models
class Game(db.Model):
    __tablename__ = 'games'
    
    game_id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    finished_at = db.Column(db.Date)
    perspective_id = db.Column(db.Integer, db.ForeignKey('perspectives.perspective_id'), nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('platforms.platform_id'), nullable=False)
    finished = db.Column(db.Boolean, default=False, nullable=False)
    playtime = db.Column(db.Numeric)
    release_year = db.Column(db.SmallInteger)
    played_year = db.Column(db.SmallInteger)
    comments = db.Column(db.Text)
    
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
    
    # Apply sorting
    if sort_by == 'name':
        order_column = Game.name
    elif sort_by == 'playtime':
        order_column = Game.playtime
    elif sort_by == 'finished':
        order_column = Game.finished
    elif sort_by == 'finished_at':
        order_column = Game.finished_at
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
    
    return render_template('index.html', 
                         games=games, 
                         platforms=platforms, 
                         perspectives=perspectives,
                         tags=tags,
                         finished_filter=finished_filter,
                         platform_filter=platform_filter,
                         perspective_filter=perspective_filter,
                         tag_filter=tag_filter,
                         sort_by=sort_by,
                         sort_order=sort_order)


@app.route('/game/<int:id>')
def view_game(id):
    game = Game.query.get_or_404(id)
    return render_template('view_game.html', game=game)


@app.route('/game/create', methods=['GET', 'POST'])
def create_game():
    if request.method == 'POST':
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
            finished_at=finished_at,
            perspective_id=request.form.get('perspective_id'),
            platform_id=request.form.get('platform_id'),
            finished=request.form.get('finished') == 'on',
            playtime=request.form.get('playtime') if request.form.get('playtime') else None,
            release_year=request.form.get('release_year') if request.form.get('release_year') else None,
            played_year=request.form.get('played_year') if request.form.get('played_year') else None,
            comments=request.form.get('comments') if request.form.get('comments') else None
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
        game.finished_at = finished_at
        game.perspective_id = request.form.get('perspective_id')
        game.platform_id = request.form.get('platform_id')
        game.finished = request.form.get('finished') == 'on'
        game.playtime = request.form.get('playtime') if request.form.get('playtime') else None
        game.release_year = request.form.get('release_year') if request.form.get('release_year') else None
        game.played_year = request.form.get('played_year') if request.form.get('played_year') else None
        game.comments = request.form.get('comments') if request.form.get('comments') else None
                
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
    
    return render_template('stats.html',
                         total_games=total_games,
                         finished_games=finished_games,
                         total_playtime=total_playtime,
                         platform_stats=platform_stats,
                         perspective_stats=perspective_stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')