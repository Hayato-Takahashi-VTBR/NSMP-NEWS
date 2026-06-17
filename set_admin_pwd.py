#!/usr/bin/env python3
import os
import argparse

def write_env(password, name=None, secret=None, path='.env'):
    lines = []
    if password:
        lines.append(f'NSMP_ADMIN_PWD={password}')
    if name:
        lines.append(f'NSMP_ADMIN_NAME={name}')
    if secret:
        lines.append(f'SECRET_KEY={secret}')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'Wrote {path} with provided values (do NOT commit this file).')


def main():
    p = argparse.ArgumentParser(description='Create/update .env with admin credentials')
    p.add_argument('--password', '-p', help='Admin password', required=False)
    p.add_argument('--name', '-n', help='Admin display name', required=False)
    p.add_argument('--secret', '-s', help='Flask SECRET_KEY (optional)', required=False)
    args = p.parse_args()

    pwd = args.password
    name = args.name
    secret = args.secret

    if not pwd:
        pwd = input('Senha admin (será salva em .env): ').strip()
    if not name:
        name = input('Nome do admin (opcional, enter para manter Kaiser): ').strip() or 'Kaiser'
    if not secret:
        secret = input('SECRET_KEY opcional (enter para gerar aleatório): ').strip() or None

    write_env(pwd, name, secret)


if __name__ == '__main__':
    main()
