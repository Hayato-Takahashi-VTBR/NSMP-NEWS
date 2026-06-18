import glob
import os
import sqlite3
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
import subprocess
import re
import time

# load environment variables from .env if present
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'news.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
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
            image TEXT,
            markdown_filename TEXT
        )
        '''
    )
    conn.commit()
    try:
        conn.execute('ALTER TABLE posts ADD COLUMN markdown_filename TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def slugify(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def write_markdown_file(fullpath, title, date, content, image=None):
    front = [
        '---',
        f'title: {title}',
        f'date: {date}',
    ]
    if image:
        front.append(f'image: {image}')
    front.append('---')
    md = '\n'.join(front) + '\n\n' + content + '\n'
    with open(fullpath, 'w', encoding='utf-8') as f:
        f.write(md)


def create_post_markdown(title, date, content, image=None):
    slug = slugify(title)
    timestamp = int(time.time())
    filename = f"{date}-{slug}-{timestamp}.md"
    path = os.path.join(BASE_DIR, 'posts')
    os.makedirs(path, exist_ok=True)
    fullpath = os.path.join(path, filename)
    write_markdown_file(fullpath, title, date, content, image)
    return fullpath, filename


def update_post_markdown(filename, title, date, content, image=None):
    path = os.path.join(BASE_DIR, 'posts')
    fullpath = os.path.join(path, filename)
    if not os.path.exists(fullpath):
        os.makedirs(path, exist_ok=True)
    write_markdown_file(fullpath, title, date, content, image)
    return fullpath


def git_commit_and_push(paths, message):
    # try normal git push first; if GITHUB_TOKEN is set, use it for authenticated push
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    try:
        # stage deletions and changes
        subprocess.run(['git', 'add', '--all'], check=True)
        # ensure new files are added explicitly
        for path in paths:
            if os.path.exists(path):
                subprocess.run(['git', 'add', path], check=True)
        subprocess.run(['git', 'commit', '-m', message], check=True)
    except subprocess.CalledProcessError:
        # nothing to commit or error
        return False

    if token:
        # get origin URL
        try:
            origin = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], text=True).strip()
        except subprocess.CalledProcessError:
            return False

        if origin.startswith('https://'):
            secure = origin.replace('https://', f'https://{token}@')
        elif origin.startswith('git@'):
            # convert SSH to https
            m = re.match(r'git@github.com:(.+)/(.+).git', origin)
            if m:
                owner, repo = m.group(1), m.group(2)
                secure = f'https://{token}@github.com/{owner}/{repo}.git'
            else:
                secure = origin
        else:
            secure = origin

        try:
            subprocess.run(['git', 'push', secure, 'HEAD:main'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        try:
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            return True
        except subprocess.CalledProcessError:
            return False


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
        cursor = conn.execute(
            'INSERT INTO posts (title, date, content, image, markdown_filename) VALUES (?, ?, ?, ?, ?)',
            (title, date, content, image_filename, None),
        )
        post_id = cursor.lastrowid
        conn.commit()
        md_path = None
        try:
            fullpath, md_filename = create_post_markdown(title, date, content, image_filename)
            conn.execute(
                'UPDATE posts SET markdown_filename = ? WHERE id = ?',
                (md_filename, post_id),
            )
            conn.commit()
            md_path = fullpath
        except Exception as e:
            flash(f'Publicada, mas erro ao gerar o arquivo Markdown: {e}')
        finally:
            conn.close()

        if md_path:
            pushed = git_commit_and_push([md_path], f"Add post: {title}")
            if pushed:
                flash('Notícia publicada e enviada ao repositório.')
            else:
                flash('Notícia publicada localmente, mas falha ao enviar ao repositório.')
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

        markdown_filename = post['markdown_filename']
        md_path = None
        if markdown_filename:
            try:
                md_path = update_post_markdown(markdown_filename, title, date, content, image_filename)
            except Exception:
                flash('Atualizada, mas falha ao atualizar o arquivo Markdown.')
        else:
            try:
                md_path, md_filename = create_post_markdown(title, date, content, image_filename)
                conn.execute(
                    'UPDATE posts SET markdown_filename = ? WHERE id = ?',
                    (md_filename, post_id),
                )
                conn.commit()
            except Exception:
                flash('Atualizada, mas falha ao gerar o arquivo Markdown.')

        conn.close()
        if md_path:
            pushed = git_commit_and_push([md_path], f"Update post: {title}")
            if pushed:
                flash('Notícia atualizada e sincronizada com o repositório.')
            else:
                flash('Notícia atualizada localmente, mas falha ao sincronizar com o repositório.')
        else:
            flash('Notícia atualizada.')
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
        if post['markdown_filename']:
            try:
                md_path = os.path.join(BASE_DIR, 'posts', post['markdown_filename'])
                os.remove(md_path)
                git_commit_and_push([md_path], f"Remove post: {post['title']}")
            except OSError:
                pass
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
    conn.close()
    flash('Notícia removida.')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
