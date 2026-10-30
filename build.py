#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
 文件：build.py
 项目：AYS · Du株 · 好好吃饭 官网（GitHub Pages 静态站）
 作者：神启（AI 助手，代主理人 Du株 维护）
 创建日期：2026-10-22（内容驱动架构重构）
 最近维护：2026-10-27
 版本：v1.0.0（首次合规归档）
 用途：官网「内容驱动」构建引擎——读取 content/*.md 生成全站页面。
 主要作用：解析 site/home/about/roadmap.md 与 posts/*.md，输出 index/about/
   roadmap/articles 及文章详情页，并生成 sitemap.xml 与 robots.txt；统一产出
   全站导航、页脚、深色模式、响应式、SEO、YouTube 外链卡、意见反馈悬浮按钮。
 依赖：Python 3 标准库（os/re/glob/html/datetime），无第三方包
 合规说明：本文件为「生成器」，产物 *.html 自动生成请勿手改；改文案改
   content/*.md，改样式改 assets/style.css；不含任何密钥，问卷链接由
   site.md 的 feedback_url 配置。
============================================================================
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
LETTERS_DIR = os.path.join(CONTENT_DIR, "letters")
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

FAVICON = "assets/logo/logo-tile.svg"


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
        # 容错：Markdown 表格的分隔行（如 | --- | --- |）不是有效配置，直接跳过
        if re.fullmatch(r"[\s\-:|]+", s):
            continue
        if section == "导航":
            parts = [p.strip().strip("<>") for p in s.split("|")]
            if len(parts) >= 2 and parts[0]:
                label, href = parts[0], parts[1]
                external = len(parts) >= 3 and parts[2] == "external"
                nav.append((label, href, external))
        elif section == "渠道":
            parts = [p.strip().strip("<>") for p in s.split("|")]
            if len(parts) >= 4 and parts[0] and parts[1]:
                name, typ, value, logo = parts[0], parts[1], parts[2], parts[3]
                if typ == "link":
                    channels.append((logo, name, value, logo, None))
                else:  # qr
                    channels.append((logo, name, None, logo, value))
    return {
        "brand": fm.get("brand", "AYS 唤醒真我 | Du株"),
        "kicker": fm.get("kicker", fm.get("brand", "AYS · Du株")),
        "footer": fm.get("footer", "© 2026 AYS · Du株 · 好好吃饭 · 内容仅供参考，不替代医疗诊断"),
        "youtube_embed": fm.get("youtube_embed", "https://www.youtube.com/embed?listType=search&list=DuZhu-AYS%20AYS%20营养"),
        "video_mode": fm.get("video_mode", "link"),
        "video_src": fm.get("video_src", ""),
        "feedback_url": fm.get("feedback_url", ""),
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
    ic = f'<div class="rd-dir__icon">{icon}</div>' if icon else ""
    return f'''        <div class="rd-dir">
          {ic}
          <div class="rd-dir__eyebrow">FOCUS</div>
          <div class="rd-dir__name">{title}</div>
          <p class="rd-dir__desc">{desc}</p>
          <span class="rd-dir__tag">第一优先级</span>
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
      <h2 class="section__title">欢迎关注 · 全平台</h2>
""" + channels_html(channels) + """
    </section>"""


def nav_html(site):
    links = []
    for label, href, external in site["nav"]:
        tgt = ' target="_blank" rel="noopener"' if external else ""
        links.append(f'    <a class="nav__link" href="{href}"{tgt}>{label}</a>')
    return f'''  <nav class="nav" id="nav">
    <a class="nav__brand" href="index.html">{html.escape(site["brand"])}</a>
    <button class="nav__toggle" aria-label="菜单" aria-expanded="false">☰</button>
    <div class="nav__spacer"></div>
    <div class="nav__menu">
{chr(10).join(links)}
    </div>
  </nav>'''


def feedback_fab(site):
    """全站右下角悬浮反馈按钮：仅在 feedback_url 为有效 http(s) 链接时显示。
    胶囊形态（图标 + 反馈文字），点击在新标签打开腾讯问卷。"""
    url = (site.get("feedback_url") or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return ""
    return f'''  <a class="feedback-fab" href="{url}" target="_blank" rel="noopener" aria-label="填写意见反馈">
    <span class="feedback-fab__icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7A8.5 8.5 0 1 1 21 11.5z"/></svg>
    </span>
    <span class="feedback-fab__text">反馈</span>
  </a>'''


def footer(site, show_channels=True):
    ch = channels_html(site["channels"], mini=True) if show_channels else ""
    return f'''  <footer class="footer">
{ch}
    <div class="footer__copy">{site["footer"]}</div>
  </footer>
  <script src="assets/script.js"></script>'''


def page(site, title, desc, inner, url, ogimg="", extra_head="", show_channels=True):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <!-- 本文件由 build.py 自动生成（生成日期随每次构建刷新），请勿手动修改；改文案见 content/*.md，改样式见 assets/style.css -->
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <link rel="icon" href="{FAVICON}" type="image/svg+xml" />
  <link rel="icon" href="assets/logo/favicon.ico" sizes="48x48" />
  <link rel="apple-touch-icon" href="assets/logo/apple-touch-icon.png" />
  <meta name="theme-color" content="#1faf77" />
  <link rel="canonical" href="{url}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{ogimg or SITE + '/assets/og-default.png'}" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="stylesheet" href="assets/style.css" />
  {extra_head}
</head>
<body>
{nav_html(site)}
{inner}
{footer(site, show_channels)}
{feedback_fab(site)}
</body>
</html>"""


# ---------------- 页面模板 ----------------
def video_section(site):
    """首页视频区：依 video_mode 渲染。
    - bilibili / youtube：内嵌播放器（需在 site.md 的 video_src 填嵌入地址）
    - link（默认）：海报外链卡，国内微信内可点开 B站/YouTube，避免 YouTube 被墙打不开
    """
    mode = site.get("video_mode", "link")
    src = site.get("video_src", "")
    if mode in ("bilibili", "youtube") and src:
        return f'''    <section class="section section--soft">
      <div class="wrap">
        <h2 class="section__title">在视频平台看 Du株</h2>
        <div class="yt" style="max-width:820px;margin:0 auto;">
          <iframe src="{src}" title="Du株 视频" allowfullscreen></iframe>
        </div>
        <p class="yt__note">订阅频道不错过更新。</p>
      </div>
    </section>'''
    # link 模式：外链卡（国内微信环境可正常打开）
    bili = yt = None
    for key, name, url, logo, qr in site["channels"]:
        if logo == "bilibili" and url:
            bili = url
        if logo == "youtube" and url:
            yt = url
    btns = ""
    if bili:
        btns += f'<a class="yt-link__btn" href="{bili}" target="_blank" rel="noopener">▷ 在 Bilibili 看</a>'
    if yt:
        btns += f'<a class="yt-link__btn" href="{yt}" target="_blank" rel="noopener">在 YouTube 看</a>'
    return f'''    <section class="section section--soft">
      <div class="wrap">
        <h2 class="section__title">在视频平台看 Du株</h2>
        <div class="yt-link">
          <span class="yt-link__play">▷</span>
          <span class="yt-link__title">循证营养短视频</span>
          <span class="yt-link__sub">国内推荐 Bilibili，加载顺畅</span>
          <span class="yt-link__row">{btns}</span>
        </div>
      </div>
    </section>'''


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

{video_section(site)}
{follow_section(site['channels'])}"""
    return page(site, fm.get("title", site["brand"]), fm.get("desc", ""), inner, SITE + "/index.html", show_channels=False)


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
    return page(SITE_CONFIG, f"文章 | {SITE_CONFIG['brand']}", "Du株的全部营养科普文章列表。", inner, SITE + "/articles.html")


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
    return page(SITE_CONFIG, f"{p['title']} | {SITE_CONFIG['brand']}", p["summary"] or p["title"], inner, SITE + "/" + p["slug"] + ".html", ogimg)


SPONSOR_MARK = "[[SPONSOR]]"
SPONSOR_ITEMS = [
    ("assets/qr/qr-sponsor-wechat.png", "微信", "WeChat"),
    ("assets/qr/qr-sponsor-alipay.png", "支付宝", "Alipay"),
]

PERSON_MARK_RE = re.compile(r"\[\[PERSON:([a-z]+)\]\]")
PERSON_IMG = {
    # 两张人物图统一为「圆角方形」：同一尺寸、同一圆角、同一描边，避免一圆一方割裂
    "avatar": ("assets/avatar.jpg", "person__img--square", "AYS 唤醒真我 头像"),
    "duzhu": ("assets/duzhu-photo-square.jpg", "person__img--square", "Du株 照片"),
}


def sponsor_grid():
    """赞助收款码双卡：中英文平台名 + 统一「扫一扫」。
    仅在 about.md 卡片内容里出现 [[SPONSOR]] 标记时渲染；图片为本地静态素材（已裁白静区）。"""
    items = "".join(
        f'''      <div class="sponsor__item">
        <span class="sponsor__qr"><img src="{src}" alt="{cn}收款码 {en}" loading="lazy" /></span>
        <span class="sponsor__name">{cn}<span class="sponsor__en">{en}</span></span>
        <span class="sponsor__hint">扫一扫</span>
      </div>
''' for src, cn, en in SPONSOR_ITEMS)
    return f'''    <div class="sponsor__grid">
{items}    </div>'''


# ---------------- 主理人寄语（每年 11.01 一封，按时间维度归档） ----------------
def ymd_cn(d):
    """日期显示：2026-11-01 -> 2026.11.01；解析失败原样返回。"""
    try:
        return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%Y.%m.%d")
    except Exception:
        return d


def load_letters():
    """读取 content/letters/*.md，按日期倒序。文件名（YYYY）即年份标识。
    用户每年 11 月 1 日新增一个 md，即自动成为「最新一期」，旧文自动进往期归档。"""
    items = []
    if not os.path.isdir(LETTERS_DIR):
        return items
    for path in sorted(glob.glob(os.path.join(LETTERS_DIR, "*.md"))):
        name = os.path.basename(path)
        if name.startswith("_"):        # 下划线开头=模板/草稿，不参与构建
            continue
        fm, body = parse_frontmatter(read_md(path))
        year = fm.get("year") or os.path.splitext(os.path.basename(path))[0]
        items.append(dict(
            year=str(year),
            slug="letter-" + str(year),
            title=fm.get("title", f"{year} 年主理人寄语"),
            date=fm.get("date", ""),
            summary=fm.get("summary", ""),
            html=md_to_html(body),
        ))
    items.sort(key=lambda x: (str(x["date"]), x["year"]), reverse=True)
    return items


def letters_block(letters):
    """关于页「主理人Du株 · 寄语」卡内的最新一期摘要；尚无内容时显示预告态。"""
    if not letters:
        return '''    <div class="letter letter--pending">
      <div class="letter__meta"><span class="letter__badge">2026</span><span class="letter__date">11.01</span></div>
      <p class="letter__excerpt">首期主理人寄语将于 2026 年 11 月 1 日发布，此后每年一封。</p>
    </div>'''
    top = letters[0]
    more = '<a class="letter__more letter__more--sub" href="letters.html">往期寄语</a>' if len(letters) > 1 else ""
    return f'''    <div class="letter">
      <div class="letter__meta"><span class="letter__badge">{top["year"]}</span><span class="letter__date">{ymd_cn(top["date"])}</span></div>
      <div class="letter__title">{html.escape(top["title"])}</div>
      <p class="letter__excerpt">{html.escape(top["summary"])}</p>
      <div class="letter__foot"><a class="letter__more" href="{top["slug"]}.html">阅读全文 →</a>{more}</div>
    </div>'''


def letters_page(site, letters):
    """寄语归档页：按年份倒序列出全部寄语（含预告态）。"""
    if letters:
        rows = "".join(f'''      <a class="lrow" href="{it["slug"]}.html">
        <span class="lrow__year">{it["year"]}</span>
        <span class="lrow__body"><span class="lrow__title">{html.escape(it["title"])}</span><span class="lrow__sum">{html.escape(it["summary"])}</span></span>
        <span class="lrow__date">{ymd_cn(it["date"])}</span>
      </a>
''' for it in letters)
        body = f'    <div class="llist">\n{rows}    </div>'
    else:
        body = '''    <div class="letter letter--pending">
      <div class="letter__meta"><span class="letter__badge">2026</span><span class="letter__date">11.01</span></div>
      <p class="letter__excerpt">首期主理人寄语将于 2026 年 11 月 1 日发布，此后每年一封，全部收录在这里。</p>
    </div>'''
    inner = f"""    <main class="wrap section">
      <h1 class="section__title">主理人Du株 · 寄语</h1>
      <p class="section__lead">每年 11 月 1 日一封，逐年收录。</p>
{body}
      <p class="backlink"><a href="about.html">← 返回关于</a></p>
    </main>"""
    return page(site, f"主理人寄语 | {site['brand']}", "AYS 主理人 Du株 每年 11 月 1 日写给读者的一封信，按年份收录。", inner, SITE + "/letters.html")


def letter_page(site, it):
    inner = f"""    <main class="wrap section letter-view">
      <h1 class="section__title">{html.escape(it["title"])}</h1>
      <p class="letter-view__date">{ymd_cn(it["date"])} · 主理人Du株 · 寄语</p>
      <div class="letter-view__body">
{it["html"]}
      </div>
      <p class="backlink"><a href="letters.html">← 全部寄语</a></p>
    </main>"""
    return page(site, f"{it['title']} | {site['brand']}", it["summary"] or it["title"], inner, SITE + "/" + it["slug"] + ".html")


def render_about(site, content):
    fm, body = parse_frontmatter(content)
    h1, lead, blocks = parse_about_blocks(body)
    letters = load_letters()
    cards = []
    for b in blocks:
        raw = b["content"]
        media = ""
        m = PERSON_MARK_RE.search(raw)
        if m:
            src, cls, alt = PERSON_IMG.get(m.group(1), ("", "", ""))
            if src:
                media = f'<div class="person__media"><img class="person__img {cls}" src="{src}" alt="{alt}" loading="lazy" /></div>'
            raw = raw.replace(m.group(0), "")
        extra = ""
        if "[[LETTERS]]" in raw:
            extra += "\n" + letters_block(letters)
            raw = raw.replace("[[LETTERS]]", "")
        if SPONSOR_MARK in raw:
            extra += "\n" + sponsor_grid()
            raw = raw.replace(SPONSOR_MARK, "")
        text = md_to_html(raw.strip())
        if media:
            cards.append(f'''    <div class="card card--person" style="margin-bottom:22px;">
      <div class="person__row">
        {media}
        <div class="person__body">
          <div class="card__title">{b["title"]}</div>
          <div class="card__text">{text}</div>
        </div>
      </div>{extra}
    </div>''')
        else:
            cards.append(f'''    <div class="card" style="margin-bottom:22px;">
      <div class="card__title">{b["title"]}</div>
      <div class="card__text">{text}</div>{extra}
    </div>''')
    inner = f"""    <main class="wrap section">
      <h1 class="section__title">{h1 or fm.get("title", "关于")}</h1>
      <p class="section__lead">{lead or ""}</p>
{''.join(cards)}
    </main>
{follow_section(site['channels'])}"""
    return page(site, fm.get("title", f"关于 | {site['brand']}"), fm.get("desc", ""), inner, SITE + "/about.html", show_channels=False)


ROADMAP_CSS = """<style>
/* 规划页专属样式（2026-10-29 v1.1 B 版：宣言卡 + 编号卡片） */
/* 项目方向：居中宣言卡 */
.rd-dirs{display:grid;gap:18px;margin:8px 0 0}
.rd-dir{background:radial-gradient(130% 150% at 50% 0%,#f4fcf8 0%,#fff 58%);border:1px solid var(--border);border-radius:26px;box-shadow:var(--shadow);padding:40px 34px 34px;text-align:center}
.rd-dir__icon{width:74px;height:74px;margin:0 auto 18px;border-radius:50%;background:#fff;display:grid;place-items:center;font-size:32px;box-shadow:0 0 0 9px var(--primary-soft),inset 0 0 0 1px #e6f6ee}
.rd-dir__eyebrow{font-size:12px;font-weight:800;letter-spacing:1.6px;color:var(--primary-strong)}
.rd-dir__name{font-size:23px;font-weight:800;margin:8px 0 12px;letter-spacing:.3px}
.rd-dir__desc{color:var(--text-muted);font-size:15px;margin:0 auto;max-width:560px;line-height:1.85}
.rd-dir__tag{display:inline-block;margin-top:20px;font-size:12px;font-weight:800;color:var(--primary-strong);background:var(--primary-soft);padding:6px 16px;border-radius:999px}
/* 里程碑：编号卡片 */
.rd-cards{display:grid;gap:16px;margin:8px 0 0}
.rd-card{position:relative;background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:22px 24px;box-shadow:0 2px 10px rgba(20,60,40,.05);overflow:hidden;transition:transform .18s ease,box-shadow .18s ease}
.rd-card:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.rd-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--primary-soft)}
.rd-card--latest::before{background:var(--primary)}
.rd-card--latest{border-color:#a9dcc4;box-shadow:0 8px 24px rgba(31,175,119,.13)}
.rd-card__head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px;position:relative}
.rd-card__date{font-size:12px;font-weight:800;color:var(--primary-strong);background:var(--surface-2);padding:4px 12px;border-radius:999px;font-variant-numeric:tabular-nums;letter-spacing:.3px}
.rd-card__badge{font-size:11px;font-weight:800;color:#fff;background:var(--primary);padding:3px 10px;border-radius:999px}
.rd-card__title{font-size:18px;font-weight:800;margin:0 0 6px;position:relative}
.rd-card__desc{color:var(--text-muted);font-size:14px;margin:0;position:relative;max-width:88%}
@media (max-width:640px){
.rd-dir{padding:30px 22px 26px;border-radius:20px}
.rd-dir__icon{width:62px;height:62px;font-size:27px;box-shadow:0 0 0 7px var(--primary-soft),inset 0 0 0 1px #e6f6ee}
.rd-dir__name{font-size:19px}
.rd-card{padding:18px 18px 18px 20px}
.rd-card__desc{max-width:100%}
}
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
            cards = []
            for i, (d, t, de) in enumerate(ms, 1):
                latest = i == 1
                cards.append(f'''        <div class="rd-card{" rd-card--latest" if latest else ""}">
          <div class="rd-card__head"><span class="rd-card__date">{d.replace("-", ".")}</span>{'<span class="rd-card__badge">最新</span>' if latest else ''}</div>
          <h3 class="rd-card__title">{t}</h3>
          <p class="rd-card__desc">{de}</p>
        </div>''')
            parts.append(f'''    <section>
      <div class="wrap">
        <h2 class="section__title">{sec["title"]}</h2>
        <p class="section__lead">{sec["lead"] or ""}</p>
        <div class="rd-cards">
{chr(10).join(cards)}
        </div>
      </div>
    </section>''')
        else:
            dirs = "".join(dir_html(*split_icon_title(it)) for it in sec["items"])
            parts.append(f'''    <section class="section--soft">
      <div class="wrap">
        <h2 class="section__title">{sec["title"]}</h2>
        <p class="section__lead">{sec["lead"] or ""}</p>
        <div class="rd-dirs">{dirs}</div>
      </div>
    </section>''')
    inner = f"""    <header class="hero">
      <span class="hero__kicker">{html.escape(site["kicker"])}</span>
      <h1 class="hero__title">{hero_title}</h1>
      <p class="hero__sub">{hero_sub}</p>
    </header>
{''.join(parts)}"""
    return page(site, fm.get("title", f"里程碑 & 项目规划 | {site['brand']}"), fm.get("desc", ""), inner, SITE + "/roadmap.html", extra_head=ROADMAP_CSS)


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

    letters = load_letters()
    with open(os.path.join(ROOT, "letters.html"), "w", encoding="utf-8") as f:
        f.write(letters_page(SITE_CONFIG, letters))
    for it in letters:
        with open(os.path.join(ROOT, it["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(letter_page(SITE_CONFIG, it))

    # sitemap
    urls = [SITE + "/index.html", SITE + "/about.html", SITE + "/articles.html",
            SITE + "/roadmap.html", SITE + "/letters.html"]
    urls += [SITE + "/" + p["slug"] + ".html" for p in posts]
    urls += [SITE + "/" + it["slug"] + ".html" for it in letters]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f"  <url><loc>{html.escape(u)}</loc></url>\n"
    sm += "</urlset>"
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sm)
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: " + SITE + "/sitemap.xml\n")

    print(f"构建完成：{len(posts)} 篇文章，{len(letters)} 篇主理人寄语，生成 index/about/roadmap/articles/letters + 详情页 + sitemap/robots（内容来自 content/）")


if __name__ == "__main__":
    main()
