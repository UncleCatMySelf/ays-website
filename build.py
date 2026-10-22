#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AYS 官网 · 内容驱动构建引擎
用法：python build.py
设计原则：内容（文案）与代码/样式彻底分离
- content/site.md   全站设置：品牌、导航、各平台关注渠道（链接/二维码）
- content/home.md   首页文案（hero + 各栏目卡片）
- content/about.md  关于页文案
- content/roadmap.md 规划页：方向 + 里程碑（自动按日期倒序）
- posts/*.md        博客文章（含 frontmatter）
生成：index/about/roadmap/articles + 文章详情 + sitemap/robots
用户只需改 content/*.md，跑本脚本 + sync 即上线。
样式/布局/功能（导航、页脚、深色模式、响应式、动态文章列表、YouTube 嵌入）由本引擎负责。
"""
import os, re, glob, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(ROOT, "posts")
CONTENT_DIR = os.path.join(ROOT, "content")
SITE = "https://unclecatmyself.github.io/ays-website"
REPO = "UncleCatMySelf/ays-website"

# ---------------- 手绘渠道 logo（内联 SVG，品牌色） ----------------
LOGOS = {
    "bilibili": '<svg viewBox="0 0 64 64" width="64" height="64"><rect x="6" y="20" width="52" height="36" rx="12" fill="#00a1d6"/><path d="M16 8l10 12M48 8l-10 12" stroke="#00a1d6" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M22 30h20M22 38h20" stroke="#fff" stroke-width="4" stroke-linecap="round"/></svg>',
    "youtube": '<svg viewBox="0 0 64 64" width="64" height="64"><rect x="6" y="16" width="52" height="32" rx="10" fill="#ff0033"/><path d="M28 26l14 6-14 6z" fill="#fff"/></svg>',
    "ximalaya": '<svg viewBox="0 0 64 64" width="64" height="64"><rect x="6" y="16" width="52" height="32" rx="10" fill="#f96a1c"/><path d="M18 32h4M26 24v16M34 20v24M42 24v16M50 32h4" stroke="#fff" stroke-width="4" stroke-linecap="round"/></svg>',
    "wechat": '<svg viewBox="0 0 64 64" width="64" height="64"><rect x="6" y="14" width="52" height="36" rx="12" fill="#1faf77"/><circle cx="24" cy="30" r="6" fill="#fff"/><circle cx="42" cy="36" r="6" fill="#fff"/><circle cx="22" cy="29" r="2" fill="#1faf77"/><circle cx="40" cy="35" r="2" fill="#1faf77"/></svg>',
    "xhs": '<svg viewBox="0 0 64 64" width="64" height="64"><rect x="6" y="14" width="52" height="36" rx="12" fill="#ff2442"/><text x="32" y="40" font-size="20" fill="#fff" text-anchor="middle" font-family="sans-serif" font-weight="800">RED</text></svg>',
    "douyin": '<svg viewBox="0 0 64 64" width="64" height="64"><rect x="6" y="14" width="52" height="36" rx="12" fill="#161823"/><path d="M38 22v18a7 7 0 11-5-6.6" stroke="#25f4ee" stroke-width="4" fill="none" stroke-linecap="round"/><path d="M38 22a7 7 0 005 6.6" stroke="#fe2c55" stroke-width="4" fill="none" stroke-linecap="round"/></svg>',
}

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='8' fill='%231faf77'/%3E"
           "%3Ctext x='16' y='22' font-size='16' font-family='sans-serif' font-weight='700' fill='white' text-anchor='middle'%3EA%3C/text%3E%3C/svg%3E")


# ---------------- 读取与解析 ----------------
def read_md(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_frontmatter(raw):
    fm, body = {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        body = m.group(2)
    return fm, body


def load_site():
    """读取 content/site.md：品牌、导航、关注渠道。"""
    fm, body = parse_frontmatter(read_md(os.path.join(CONTENT_DIR, "site.md")))
    nav, channels = [], []
    section = None
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("## "):
            section = s[3:].strip()
            continue
        if not s or section is None:
            continue
        if section == "导航":
            parts = [p.strip() for p in s.split("|")]
            if len(parts) >= 2:
                label, href = parts[0], parts[1]
                external = len(parts) >= 3 and parts[2] == "external"
                nav.append((label, href, external))
        elif section == "渠道":
            parts = [p.strip() for p in s.split("|")]
            if len(parts) >= 4:
                name, typ, value, logo = parts[0], parts[1], parts[2], parts[3]
                if typ == "link":
                    channels.append((logo, name, value, logo, None))
                else:  # qr
                    channels.append((logo, name, None, logo, value))
    return {
        "brand": fm.get("brand", "AYS · Du株"),
        "kicker": fm.get("kicker", fm.get("brand", "AYS · Du株")),
        "footer": fm.get("footer", "© 2026 AYS · Du株 · 好好吃饭 · 内容仅供参考，不替代医疗诊断"),
        "youtube_embed": fm.get("youtube_embed", "https://www.youtube.com/embed?listType=search&list=DuZhu-AYS%20AYS%20营养"),
        "nav": nav,
        "channels": channels,
    }


def parse_blocks(raw):
    """首页/规划页：抽取 hero + 各 ## 栏目（引导句 + 卡片项）。"""
    fm, body = parse_frontmatter(raw)
    hero_title, hero_sub = "", ""
    sections, cur = [], None
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            hero_title = s[2:].strip()
        elif s.startswith("> "):
            if cur is None:
                hero_sub = s[2:].strip()
            else:
                cur["lead"] = s[2:].strip()
        elif s.startswith("## "):
            cur = {"title": s[3:].strip(), "lead": None, "items": []}
            sections.append(cur)
        elif re.match(r"^[-*] ", s) and cur is not None:
            cur["items"].append(s[2:].strip())
    return fm, hero_title, hero_sub, sections


def parse_about_blocks(body):
    """关于页：# 标题 + > 引导 + 每个 ## 变一张卡片。"""
    h1 = lead = None
    blocks, cur, buf = [], None, []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# "):
            h1 = s[2:].strip()
        elif s.startswith("> "):
            if cur is None:
                lead = s[2:].strip()
            else:
                buf.append(line)
        elif s.startswith("## "):
            if cur:
                cur["content"] = "\n".join(buf).strip()
                blocks.append(cur)
            cur, buf = {"title": s[3:].strip(), "content": ""}, []
        else:
            if cur is not None:
                buf.append(line)
    if cur:
        cur["content"] = "\n".join(buf).strip()
        blocks.append(cur)
    return h1, lead, blocks


# ---------------- Markdown 轻量解析 ----------------
def inline(t):
    t = html.escape(t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" />', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def md_to_html(md):
    lines = md.split("\n")
    out, i, in_code, code_buf = [], 0, False, []
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>")
                code_buf, in_code = [], False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        if not s:
            i += 1
            continue
        if s == "---":
            out.append("<hr/>")
            i += 1
            continue
        if s.startswith("# "):
            out.append("<h1>" + inline(s[2:]) + "</h1>")
        elif s.startswith("## "):
            out.append("<h2>" + inline(s[3:]) + "</h2>")
        elif s.startswith("### "):
            out.append("<h3>" + inline(s[4:]) + "</h3>")
        elif s.startswith("> "):
            out.append("<blockquote>" + inline(s[2:]) + "</blockquote>")
        elif re.match(r"^[-*] ", s):
            items = []
            while i < len(lines) and re.match(r"^[-*] ", lines[i].strip()):
                items.append("<li>" + inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif re.match(r"^\d+\. ", s):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i].strip()):
                items.append("<li>" + inline(lines[i].strip().split(". ", 1)[1]) + "</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        else:
            para = []
            while (i < len(lines) and lines[i].strip()
                   and not lines[i].strip().startswith("#")
                   and not lines[i].strip().startswith(">")
                   and lines[i].strip() != "---"
                   and not re.match(r"^[-*] ", lines[i].strip())
                   and not re.match(r"^\d+\. ", lines[i].strip())):
                para.append(inline(lines[i]))
                i += 1
            out.append("<p>" + " ".join(para) + "</p>")
            continue
        i += 1
    return "\n".join(out)


# ---------------- 卡片 / 项解析 ----------------
def split_card_item(text):
    m = re.split(r"[:：]", text, maxsplit=1)
    if len(m) == 2:
        return m[0].strip(), m[1].strip()
    return text.strip(), ""


def split_icon(title):
    m = re.match(r"^(\S)\s+(.+)$", title)
    if m and not re.match(r"[\w一-鿿]", m.group(1)):
        return m.group(1), m.group(2)
    return "", title


def split_icon_title(text):
    title, desc = split_card_item(text)
    icon, name = split_icon(title)
    return icon, name, desc


def card_html(icon, title, desc):
    ic = f'<div class="card__icon">{icon}</div>' if icon else ""
    return f'''      <div class="card">{ic}<div class="card__title">{title}</div><p class="card__text">{desc}</p></div>'''


def dir_html(icon, title, desc):
    ic = f'<div class="dir__icon">{icon}</div>' if icon else ""
    return f'''          <div class="dir">
            {ic}
            <div class="dir__name">{title}</div>
            <div class="dir__desc">{desc}</div>
            <span class="dir__tag">长期目标</span>
          </div>'''


# ---------------- 片段 ----------------
def tags_html(p):
    return "".join(f'<span class="tag">{t}</span>' for t in p["tags"])


def post_card(p):
    return f"""      <div class="card post-card">
        <div class="post-card__meta">{p['date']} · {tags_html(p)}</div>
        <div class="post-card__title">{p['title']}</div>
        <p class="post-card__excerpt">{p['summary']}</p>
        <a class="card__link" href="{p['slug']}.html">阅读全文 →</a>
      </div>"""


def share_section(p):
    url = html.escape(SITE + "/" + p["slug"] + ".html", quote=True)
    t = html.escape(p["title"])
    wb = f"https://service.weibo.com/share/share.php?url={url}&title={t}"
    tw = f"https://twitter.com/intent/tweet?url={url}&text={t}"
    qq = f"https://connect.qq.com/widget/shareqq/index.html?url={url}&title={t}"
    return f"""    <div class="share">
      <a href="{wb}" target="_blank" rel="noopener">微博</a>
      <a href="{tw}" target="_blank" rel="noopener">X / Twitter</a>
      <a href="{qq}" target="_blank" rel="noopener">QQ</a>
      <a href="#" class="copy-link" data-url="{url}">复制链接</a>
    </div>"""


def channels_html(channels, mini=False):
    out = []
    for key, name, url, logo, qr in channels:
        badge = LOGOS.get(logo, "")
        if qr:
            out.append(
                f'''      <span class="channel channel--qr" tabindex="0" data-name="{name}" role="button" aria-label="{name} 扫码关注">
        <span class="channel__badge">{badge}</span>
        <span class="channel__name">{name}</span>
        <span class="channel__card channel__card--qr">
          <img class="channel__qr" src="{qr}" alt="{name}二维码" loading="lazy" />
          <span class="channel__card-text">{name} · 扫码关注</span>
        </span>
      </span>''')
        else:
            out.append(
                f'''      <a class="channel" href="{url}" target="_blank" rel="noopener" data-name="{name}" aria-label="{name} 频道">
        <span class="channel__badge">{badge}</span>
        <span class="channel__name">{name}</span>
        <span class="channel__card">
          <img class="channel__avatar" src="assets/avatar.jpg" alt="{name}" loading="lazy" />
          <span class="channel__card-title">{name}</span>
          <span class="channel__card-text">前往 {name}频道 →</span>
        </span>
      </a>''')
    cls = "channels" + (" channels--mini" if mini else "")
    return '    <div class="' + cls + '">\n' + "\n".join(out) + "\n    </div>"


def follow_section(channels):
    return """    <section class="section wrap" style="text-align:center;">
      <h2 class="section__title">关注 Du株 · 全平台</h2>
""" + channels_html(channels) + """
    </section>"""


def nav_html(site):
    links = []
    for label, href, external in site["nav"]:
        cls = "nav__link"
        if "youtube.com" in href:
            cls += " nav__yt"
        tgt = ' target="_blank" rel="noopener"' if external else ""
        links.append(f'    <a class="{cls}" href="{href}"{tgt}>{label}</a>')
    return f'''  <nav class="nav">
    <div class="nav__brand">{html.escape(site["brand"])}</div>
    <div class="nav__spacer"></div>
{chr(10).join(links)}
    <button class="theme-toggle" aria-label="切换深色模式">🌙</button>
  </nav>'''


def footer(site, show_channels=True):
    ch = channels_html(site["channels"], mini=True) if show_channels else ""
    return f'''  <footer class="footer">
{ch}
    <div class="footer__copy">{site["footer"]}</div>
  </footer>
  <script src="assets/script.js"></script>'''


def page(site, title, desc, inner, url, ogimg="", extra_head="", show_channels=True):
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <link rel="icon" href="{FAVICON}" />
  <link rel="canonical" href="{url}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{url}" />
  {"<meta property='og:image' content='" + ogimg + "' />" if ogimg else ""}
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="stylesheet" href="assets/style.css" />
  {extra_head}
</head>
<body>
{nav_html(site)}
{inner}
{footer(site, show_channels)}
</body>
</html>"""


# ---------------- 页面模板 ----------------
def home(site, content, latest):
    fm, hero_title, hero_sub, sections = parse_blocks(content)
    sec_html = []
    for sec in sections:
        cards = "".join(card_html(*split_icon_title(it)) for it in sec["items"])
        sec_html.append(f'''    <section class="section wrap">
      <h2 class="section__title">{sec["title"]}</h2>
      <p class="section__lead">{sec["lead"] or ""}</p>
      <div class="grid">
{cards}
      </div>
    </section>''')
    cards_latest = "\n".join(post_card(p) for p in latest) or '      <p>文章即将上线，先去 <a href="https://www.youtube.com/@DuZhu-AYS" target="_blank" rel="noopener">YouTube @DuZhu-AYS</a> 看视频吧。</p>'
    inner = f"""
    <section class="hero">
      <span class="hero__kicker">{html.escape(site["kicker"])}</span>
      <h1 class="hero__title">{hero_title}</h1>
      <p class="hero__sub">{hero_sub}</p>
      <div class="btn-row">
        <a class="btn btn--primary" href="articles.html">读最新文章</a>
        <a class="btn btn--ghost" href="https://www.youtube.com/@DuZhu-AYS" target="_blank" rel="noopener">▷ 看 YouTube 频道</a>
      </div>
    </section>
{''.join(sec_html)}
    <section class="section wrap">
      <h2 class="section__title">最新文章</h2>
      <p class="section__lead">图文沉淀，配套视频在 YouTube @DuZhu-AYS。</p>
      <div class="grid">
{cards_latest}
      </div>
      <div style="text-align:center;margin-top:30px;"><a class="btn btn--ghost" href="articles.html">查看全部文章 →</a></div>
    </section>

    <section class="section section--soft">
      <div class="wrap">
        <h2 class="section__title">在 YouTube 看视频</h2>
        <div class="yt" style="max-width:820px;margin:0 auto;">
          <iframe src="{site['youtube_embed']}" title="Du株 YouTube" allowfullscreen></iframe>
        </div>
        <p class="yt__note">订阅 <a href="https://www.youtube.com/@DuZhu-AYS" target="_blank" rel="noopener">@DuZhu-AYS</a> 不错过更新。</p>
      </div>
    </section>
{follow_section(site['channels'])}"""
    return page(site, fm.get("title", "AYS · Du株 · 好好吃饭"), fm.get("desc", ""), inner, SITE + "/index.html", show_channels=False)


def list_page(posts):
    cards = "\n".join(post_card(p) for p in posts) or '      <p>暂无文章。</p>'
    inner = f"""
    <main class="wrap section">
      <h1 class="section__title">全部文章</h1>
      <p class="section__lead">循证营养科普，配套视频在 YouTube @DuZhu-AYS。</p>
      <div class="grid">
{cards}
      </div>
    </main>"""
    return page(SITE_CONFIG, "文章 · AYS · Du株", "Du株的全部营养科普文章列表。", inner, SITE + "/articles.html")


def article_page(p):
    cover = f'<img class="article__cover" src="{p["cover"]}" alt="{p["title"]}" />' if p["cover"] else ""
    inner = f"""
    <article class="article">
      <div class="article__meta">{p['date']} · {tags_html(p)}</div>
      <h1>{p['title']}</h1>
      {cover}
      {p['html']}
      {share_section(p)}
    </article>"""
    ogimg = SITE + "/" + p["cover"] if p["cover"] else ""
    return page(SITE_CONFIG, p["title"] + " · AYS · Du株", p["summary"] or p["title"], inner, SITE + "/" + p["slug"] + ".html", ogimg)


def render_about(site, content):
    fm, body = parse_frontmatter(content)
    h1, lead, blocks = parse_about_blocks(body)
    cards = []
    for b in blocks:
        cards.append(f'''    <div class="card" style="margin-bottom:22px;">
      <div class="card__title">{b["title"]}</div>
      <p class="card__text">{md_to_html(b["content"])}</p>
    </div>''')
    inner = f"""    <main class="wrap section">
      <h1 class="section__title">{h1 or fm.get("title", "关于")}</h1>
      <p class="section__lead">{lead or ""}</p>
{''.join(cards)}
    </main>
{follow_section(site['channels'])}"""
    return page(site, fm.get("title", "关于 Du株 · AYS"), fm.get("desc", ""), inner, SITE + "/about.html", show_channels=False)


ROADMAP_CSS = """<style>
.dir-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:8px}
.dir{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:26px}
.dir__icon{font-size:26px}
.dir__name{font-size:19px;font-weight:800;margin:8px 0 8px}
.dir__desc{color:var(--text-muted);font-size:15px}
.dir__tag{display:inline-block;margin-top:14px;font-size:12px;font-weight:800;color:var(--primary-strong);background:var(--primary-soft);padding:4px 12px;border-radius:999px}
.timeline{position:relative;margin:8px 0 0 8px;padding-left:30px}
.timeline::before{content:"";position:absolute;left:7px;top:6px;bottom:6px;width:2px;background:var(--border)}
.ms{position:relative;margin-bottom:26px}
.ms::before{content:"";position:absolute;left:-30px;top:4px;width:16px;height:16px;border-radius:50%;background:var(--primary);border:3px solid var(--bg);box-shadow:0 0 0 2px var(--primary-soft)}
.ms__date{font-size:13px;font-weight:800;color:var(--primary-strong);letter-spacing:.5px}
.ms__title{font-size:17px;font-weight:700;margin:2px 0 3px}
.ms__desc{color:var(--text-muted);font-size:14px}
@media (max-width:640px){.dir-grid{grid-template-columns:1fr}.dir{padding:20px}}
</style>"""


def roadmap(site, content):
    fm, hero_title, hero_sub, sections = parse_blocks(content)
    parts = []
    for sec in sections:
        if "里程碑" in sec["title"]:
            ms = []
            for it in sec["items"]:
                parts3 = [p.strip() for p in it.split("|")]
                if len(parts3) >= 3:
                    ms.append((parts3[0], parts3[1], parts3[2]))
            ms.sort(key=lambda x: x[0], reverse=True)
            items = "".join(
                f'<div class="ms"><div class="ms__date">{d}</div><div class="ms__title">{t}</div><div class="ms__desc">{de}</div></div>'
                for d, t, de in ms)
            parts.append(f'''    <section>
      <div class="wrap">
        <h2 class="section__title">{sec["title"]}</h2>
        <p class="section__lead">{sec["lead"] or ""}</p>
        <div class="timeline">{items}</div>
      </div>
    </section>''')
        else:
            dirs = "".join(dir_html(*split_icon_title(it)) for it in sec["items"])
            parts.append(f'''    <section class="section--soft">
      <div class="wrap">
        <h2 class="section__title">{sec["title"]}</h2>
        <p class="section__lead">{sec["lead"] or ""}</p>
        <div class="dir-grid">{dirs}</div>
      </div>
    </section>''')
    inner = f"""    <header class="hero">
      <span class="hero__kicker">{html.escape(site["kicker"])}</span>
      <h1 class="hero__title">{hero_title}</h1>
      <p class="hero__sub">{hero_sub}</p>
    </header>
{''.join(parts)}"""
    return page(site, fm.get("title", "里程碑 & 项目规划 · AYS · Du株"), fm.get("desc", ""), inner, SITE + "/roadmap.html", extra_head=ROADMAP_CSS)


# ---------------- 入口 ----------------
SITE_CONFIG = None


def parse_post(path):
    raw = read_md(path)
    fm, body = parse_frontmatter(raw)
    slug = os.path.splitext(os.path.basename(path))[0]
    return dict(
        slug=slug,
        title=fm.get("title", slug),
        date=fm.get("date", ""),
        summary=fm.get("summary", ""),
        tags=[t.strip() for t in fm.get("tags", "").split(",") if t.strip()],
        cover=fm.get("cover", ""),
        html=md_to_html(body),
    )


def pdate(p):
    try:
        return datetime.datetime.strptime(p["date"], "%Y-%m-%d")
    except Exception:
        return datetime.datetime(1970, 1, 1)


def main():
    global SITE_CONFIG
    os.makedirs(POSTS_DIR, exist_ok=True)
    SITE_CONFIG = load_site()

    posts = [parse_post(p) for p in glob.glob(os.path.join(POSTS_DIR, "*.md"))]
    posts.sort(key=pdate, reverse=True)

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(home(SITE_CONFIG, read_md(os.path.join(CONTENT_DIR, "home.md")), posts[:3]))
    with open(os.path.join(ROOT, "articles.html"), "w", encoding="utf-8") as f:
        f.write(list_page(posts))
    for p in posts:
        with open(os.path.join(ROOT, p["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(article_page(p))
    with open(os.path.join(ROOT, "about.html"), "w", encoding="utf-8") as f:
        f.write(render_about(SITE_CONFIG, read_md(os.path.join(CONTENT_DIR, "about.md"))))
    with open(os.path.join(ROOT, "roadmap.html"), "w", encoding="utf-8") as f:
        f.write(roadmap(SITE_CONFIG, read_md(os.path.join(CONTENT_DIR, "roadmap.md"))))

    # sitemap
    urls = [SITE + "/index.html", SITE + "/about.html", SITE + "/articles.html", SITE + "/roadmap.html"]
    urls += [SITE + "/" + p["slug"] + ".html" for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f"  <url><loc>{html.escape(u)}</loc></url>\n"
    sm += "</urlset>"
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sm)
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: " + SITE + "/sitemap.xml\n")

    print(f"构建完成：{len(posts)} 篇文章，生成 index/about/roadmap/articles + {len(posts)} 篇详情 + sitemap/robots（内容来自 content/）")


if __name__ == "__main__":
    main()
