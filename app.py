import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'news.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'dev-secret'
app.config['ADMIN_PASSWORD'] = os.environ.get('NSMP_ADMIN_PWD', '2k0a0u7e')
app.config['ADMIN_NAME'] = os.environ.get('NSMP_ADMIN_NAME', 'Kaiser')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            image TEXT
        )
        '''
    )
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY date DESC, id DESC').fetchall()
    conn.close()
    return render_template('index.html', posts=posts, admin_name=app.config.get('ADMIN_NAME', 'Kaiser'))


@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            session['admin_name'] = app.config.get('ADMIN_NAME', 'Kaiser')
            flash('Autenticado.')
            return redirect(request.args.get('next') or url_for('index'))
        else:
            flash('Senha incorreta.')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('admin_name', None)
    flash('Desconectado.')
    return redirect(url_for('index'))


@app.route('/new', methods=('GET', 'POST'))
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', '').strip()
        content = request.form.get('content', '').strip()

        if not title:
            flash('Título é obrigatório.')
            return redirect(request.url)

        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        image_filename = None
        file = request.files.get('image')
        if file and file.filename:
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                image_filename = f"{int(datetime.utcnow().timestamp())}.{ext}"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                file.save(dest)
            else:
                flash('Formato de imagem não permitido.')
                return redirect(request.url)

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO posts (title, date, content, image) VALUES (?, ?, ?, ?)',
            (title, date, content, image_filename),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    today = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('new_post.html', today=today)


@app.route('/edit/<int:post_id>', methods=('GET', 'POST'))
@login_required
def edit_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        conn.close()
        flash('Notícia não encontrada.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', '').strip()
        content = request.form.get('content', '').strip()
        if not title:
            flash('Título é obrigatório.')
            return redirect(request.url)

        image_filename = post['image']
        file = request.files.get('image')
        if file and file.filename:
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                new_filename = f"{int(datetime.utcnow().timestamp())}.{ext}"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                file.save(dest)
                if image_filename:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    except OSError:
                        pass
                image_filename = new_filename
            else:
                flash('Formato de imagem não permitido.')
                return redirect(request.url)

        conn.execute(
            'UPDATE posts SET title = ?, date = ?, content = ?, image = ? WHERE id = ?',
            (title, date, content, image_filename, post_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit_post.html', post=post)


@app.route('/delete/<int:post_id>', methods=('POST',))
@login_required
def delete_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post:
        if post['image']:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], post['image']))
            except OSError:
                pass
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
    conn.close()
    flash('Notícia removida.')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
