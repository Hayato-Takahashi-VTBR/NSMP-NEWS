# NSMP - Central de Notícias

Site simples para publicar notícias do servidor NSMP.

Instalação e execução:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse `http://localhost:5000`.

- Para criar/editar/remover notícias você precisa fazer login como administrador.
- A senha de administrador padrão é `nsmp123`. Para alterar, exporte a variável de ambiente `NSMP_ADMIN_PWD` antes de executar o app:
 - Para criar/editar/remover notícias você precisa fazer login como administrador.
 - Nome de administrador padrão: `Kaiser`.
 - A senha de administrador padrão é `2k0a0u7e`. Para alterar, exporte as variáveis de ambiente `NSMP_ADMIN_PWD` e/ou `NSMP_ADMIN_NAME` antes de executar o app:

```bash
export NSMP_ADMIN_PWD="minha-senha-secreta"
export NSMP_ADMIN_NAME="OutroNome"
python app.py
```

Uploads de imagens ficam em `static/uploads` e o banco está em `news.db`.

Visite `/login` para entrar com a senha, depois acesse "Nova notícia".

Publicação automática no GitHub Pages
-------------------------------------

Este repositório inclui um gerador estático e um workflow do GitHub Actions que publica automaticamente um site estático em `gh-pages` quando você fizer push para `main`.

- Crie posts em `posts/` como arquivos Markdown com front matter YAML (campos: `title`, `date`, `image` opcional).
- O Actions executará `build_static.py` e publicará o conteúdo em `gh-pages`.

Exemplo de post: `posts/example-2026-06-17-boas-vindas.md`.

Após o primeiro deploy, habilite o GitHub Pages nas configurações do repositório para servir a partir do branch `gh-pages` (ou configure o Pages para apontar automaticamente). O site ficará disponível em `https://<seu-usuario>.github.io/<repo>`.

Para executar localmente o build estático:

```bash
pip install -r requirements.txt
python build_static.py
# o site será gerado na pasta `site/`
```

Gerenciar senha de administrador localmente
-----------------------------------------

Você pode armazenar a senha e o nome do administrador em um arquivo `.env` para que o app Flask os carregue automaticamente.

Use o helper incluído para criar/atualizar o `.env`:

```bash
python set_admin_pwd.py --password "2k0a0u7e" --name "Kaiser"
# ou apenas rodar e seguir os prompts
python set_admin_pwd.py
```

O arquivo `.env` **não deve** ser comitado. Ele contém segredos e será ignorado se você adicionar `.env` ao `.gitignore`.

Sincronização automática com GitHub (opcional)
-------------------------------------------

O app pode automaticamente criar o arquivo Markdown em `posts/`, commitar e dar push para `main` quando você publicar uma notícia pelo painel. Para isso, defina a variável de ambiente `GITHUB_TOKEN` (ou `GH_TOKEN`) com um token que tenha permissão `repo` no repositório.

Exemplo (Linux/macOS):

```bash
export GITHUB_TOKEN="ghp_xxx..."
python app.py
```

Se `GITHUB_TOKEN` não estiver configurado, o app tentará usar as credenciais git locais (SSH/HTTPS) para dar push.

OBS: Para edições de posts existentes, o app **não** sincroniza automaticamente o arquivo Markdown correspondente; apenas novas postagens criadas via painel serão escritas e enviadas.

