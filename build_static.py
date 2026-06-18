import os
import shutil
import glob
import frontmatter
import markdown as md
from jinja2 import Environment, FileSystemLoader

BASE = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BASE, 'posts')
TEMPLATES_DIR = os.path.join(BASE, 'templates_static')
OUT_DIR = os.path.join(BASE, 'site')

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

def load_posts():
    posts = []
    for path in glob.glob(os.path.join(POSTS_DIR, '*.md')):
        with open(path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            html = md.markdown(post.content, extensions=['fenced_code'])
            meta = post.metadata
            meta.setdefault('title', os.path.splitext(os.path.basename(path))[0])
            meta.setdefault('date', '')
            image = meta.get('image')
            meta['image'] = f"static/uploads/{image}" if image else None
            slug = os.path.splitext(os.path.basename(path))[0]
            preview = post.content[:200] + ('...' if len(post.content) > 200 else '')
            posts.append({'meta':meta, 'html':html, 'preview':preview, 'slug':slug})
    posts.sort(key=lambda p: p['meta'].get('date',''), reverse=True)
    return posts


def build():
    # clean output
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)

    posts = load_posts()

    # copy static files
    static_src = os.path.join(BASE, 'static')
    static_dest = os.path.join(OUT_DIR, 'static')
    if os.path.exists(static_src):
        shutil.copytree(static_src, static_dest)

    # render index
    tpl = env.get_template('index.html')
    # Add id and preview to posts for index rendering
    posts_with_id = []
    for i, p in enumerate(posts, 1):
        p['id'] = i
        posts_with_id.append(p)
    
    with open(os.path.join(OUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(tpl.render(posts=posts_with_id))

    # render posts
    post_tpl = env.get_template('post.html')
    posts_out = os.path.join(OUT_DIR, 'posts')
    os.makedirs(posts_out, exist_ok=True)
    for i, p in enumerate(posts_with_id, 1):
        out_path = os.path.join(posts_out, p['slug'] + '.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(post_tpl.render(post=p))

    print('Built', len(posts), 'posts into', OUT_DIR)

if __name__ == '__main__':
    build()

