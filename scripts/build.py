#!/usr/bin/env python3
"""Generate a dependency-free, accessible GitHub Pages policy site."""
import html
import json
import os
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'
SLUG = re.compile(r'^[a-z][a-z0-9-]+$')
LANG = re.compile(r'^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$')
URL = re.compile(r'https://[^\s<>，。；、）]+')


def escape(value):
    return html.escape(str(value), quote=True)


def text(value):
    parts, start = [], 0
    for match in URL.finditer(value):
        # Sentence punctuation belongs outside the link.
        url = match.group(0).rstrip('.;,')
        end = match.start() + len(url)
        parts.extend([escape(value[start:match.start()]), f'<a href="{escape(url)}">{escape(url)}</a>'])
        start = end
    parts.append(escape(value[start:]))
    return ''.join(parts)


def shell(language, title, description, body, css='style.css'):
    return f'''<!doctype html>
<html lang="{escape(language)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="description" content="{escape(description)}">
<title>{escape(title)}</title>
<link rel="stylesheet" href="{escape(css)}">
</head>
<body>{body}</body>
</html>
'''


def policy_page(policy, language, css_path):
    entry = policy['languages'][language]
    nav = ' '.join(
        f'<a href="{escape(code)}.html" lang="{escape(code)}" hreflang="{escape(code)}"'
        + (' aria-current="page"' if code == language else '')
        + f'>{escape(row["label"])}</a>'
        for code, row in policy['languages'].items()
    )
    sections = ''.join(
        f'<section aria-labelledby="section-{i}"><h2 id="section-{i}">{escape(section["title"])}</h2>'
        + ''.join(f'<p>{text(p)}</p>' for p in section['paragraphs']) + '</section>'
        for i, section in enumerate(entry['sections'], 1)
    )
    body = f'''
<header class="site-header"><span>{escape(entry['appName'])}</span><span>Privacy / 隐私</span></header>
<main id="main">
<nav class="languages" aria-label="Language / 语言">{nav}</nav>
<div class="eyebrow">{escape(entry['appName'])}</div>
<h1>{escape(entry['title'])}</h1>
<p class="meta">{escape(entry['dateLabel'])}: <time datetime="{policy['effectiveDate']}">{policy['effectiveDate']}</time><br>{escape(entry['developerLabel'])}: {escape(policy['developer'])}</p>
<p class="lead">{text(entry['intro'])}</p>
<aside class="summary">{text(entry['summary'])}</aside>
{sections}
<footer><a href="{escape(policy['supportUrl'])}">{escape(entry['supportLabel'])}</a><p>{escape(entry['appName'])} · {escape(policy['developer'])}</p></footer>
</main>'''
    return shell(language, entry['appName'] + ' — ' + entry['title'], entry['summary'], body, css_path)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.h1 = 0
        self.language = None
        self.has_title = False
        self.robots = None
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.language = attrs.get('lang')
        if tag == 'h1':
            self.h1 += 1
        if tag == 'title':
            self.has_title = True
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.robots = attrs.get('content')
        if tag == 'a':
            self.anchors.append(attrs.get('href'))
        if tag == 'script':
            raise ValueError('Policy pages must not contain scripts')
        for key in ['href', 'src']:
            if key in attrs:
                self.links.append(attrs[key])


def check_pages(pages):
    for page in pages:
        parser = PageParser()
        parser.feed(page.read_text())
        assert parser.language and parser.has_title and parser.h1 == 1, f'Invalid document structure: {page}'
        assert parser.robots == 'noindex, nofollow, noarchive', f'Missing indexing preference: {page}'
        if page == OUT / 'index.html':
            assert not parser.anchors, 'The landing page must not link to documents'
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme:
                assert parsed.scheme == 'https' and parsed.hostname, f'Invalid external URL: {link}'
            elif parsed.path:
                target = (page.parent / unquote(parsed.path)).resolve()
                assert target.is_relative_to(OUT.resolve()) and target.is_file(), f'Broken local link: {page}: {link}'


def main():
    registry = json.loads((ROOT / 'config/publication/catalog/registry.json').read_text())
    assert registry['schemaVersion'] == 1 and registry['apps']
    pages, seen, public_paths = [], set(), set()
    OUT.mkdir(exist_ok=True)
    for app in registry['apps']:
        slug = app['slug']
        assert SLUG.fullmatch(slug) and slug not in seen
        seen.add(slug)
        source = (ROOT / app['source']).resolve()
        assert source.is_relative_to((ROOT / 'content').resolve())
        policy = json.loads(source.read_text())
        assert policy['schemaVersion'] == 1 and policy['slug'] == slug
        date.fromisoformat(policy['effectiveDate'])
        assert policy['developer'].strip()
        assert urlsplit(policy['supportUrl']).scheme == 'https' and urlsplit(policy['supportUrl']).hostname
        assert policy['defaultLanguage'] in policy['languages']
        public_path = app['publicPath']
        parts = public_path.split('/')
        assert len(parts) >= 6 and all(re.fullmatch(r'[a-z0-9][a-z0-9-]*', part) for part in parts)
        assert public_path not in public_paths
        public_paths.add(public_path)
        directory = OUT / public_path
        directory.mkdir(parents=True, exist_ok=True)
        css_path = os.path.relpath(OUT / 'style.css', directory).replace(os.sep, '/')
        for language, entry in policy['languages'].items():
            assert LANG.fullmatch(language)
            for key in ['label', 'appName', 'title', 'dateLabel', 'developerLabel', 'supportLabel', 'intro', 'summary']:
                assert isinstance(entry[key], str) and entry[key].strip()
            assert entry['sections']
            for section in entry['sections']:
                assert section['title'] and section['paragraphs'] and all(isinstance(p, str) and p.strip() for p in section['paragraphs'])
            page = directory / f'{language}.html'
            page.write_text(policy_page(policy, language, css_path))
            pages.append(page)
        index = directory / 'index.html'
        index.write_text(policy_page(policy, policy['defaultLanguage'], css_path))
        pages.append(index)
    home = OUT / 'index.html'
    home.write_text(shell('zh-Hans', 'Documents', 'Application documents.', '<header class="site-header"><span>Documents</span></header><main><h1>Documents</h1><p class="lead">请使用应用或商店页面提供的文件链接。<br>Please use the document link provided in the app or its store listing.</p></main>'))
    pages.append(home)
    (OUT / '.nojekyll').write_text('')
    (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
    check_pages(pages)
    print(f'Built and checked {len(pages)} HTML pages for {len(seen)} app(s); local links valid.')


if __name__ == '__main__':
    main()
