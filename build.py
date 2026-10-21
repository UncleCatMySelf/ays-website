#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AYS 官网 · 博客发布引擎
用法：python build.py
- 读取 posts/*.md（含 frontmatter）渲染为 <slug>.html
- 自动重建首页 index.html（含最新 3 篇）与文章列表 articles.html
- 生成 sitemap.xml / robots.txt
- 复制 assets 由仓库本身承载，无需额外步骤
用户只需写 markdown，跑本脚本 + sync 即上线。
"""
import os, re, glob, json, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(ROOT, "posts")
SITE = "https://unclecatmyself.github.io/ays-website"
REPO = "UncleCatMySelf/ays-website"

NAV = """
  <nav class="nav">
    <div class="nav__brand">AYS · <span>Du株</span></div>
    <div class="nav__spacer"></div>
    <a class="nav__link" href="index.html">首页</a>
    <a class="nav__link" href="articles.html">文章</a>
    <a class="nav__link" href="about.html">关于</a>
    <a class="nav__link nav__yt" href="https://www.youtube.com/@duzhu" target="_blank" rel="noopener">YouTube</a>
    <button class="theme-toggle" aria-label="切换深色模式">🌙</button>
  </nav>"""

FOOTER = """
  <footer class="footer">
    <div class="footer__row">
      <a href="https://www.youtube.com/@duzhu" target="_blank" rel="noopener">YouTube</a> ·
      <a href="https://space.bilibili.com" target="_blank" rel="noopener">B站</a> ·
      <a href="https://www.xiaohongshu.com" target="_blank" rel="noopener">小红书</a> ·
      <a href="https://www.douyin.com" target="_blank" rel="noopener">抖音</a>
    </div>
    <div class="footer__copy">© <span data-year>2026</span> AYS · Du株 · 好好吃饭 · 内容仅供参考，不替代医疗诊断</div>
  </footer>
  <script src="assets/script.js"></script>"""

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='8' fill='%231faf77'/%3E"
           "%3Ctext x='16' y='22' font-size='16' font-family='sans-serif' font-weight='700' fill='white' text-anchor='middle'%3EA%3C/text%3E%3C/svg%3E")


def page(title, desc, inner, url, ogimg="", extra_head=""):
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
{NAV}
{inner}
{FOOTER}
</body>
</html>"""


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


def parse_post(path):
    raw = open(path, encoding="utf-8").read()
    fm, body = {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
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


def subscribe_section():
    return """    <div class="subscribe">
      <h3>想第一时间收到更新？</h3>
      <p>留下邮箱，新文章与视频上线时通知你（免费）。</p>
      <form action="https://formspree.io/f/你的FORMID" method="POST">
        <input type="email" name="email" placeholder="你的邮箱" required />
        <button class="btn btn--primary" type="submit">订阅更新</button>
      </form>
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


def giscus_section():
    try:
        cfg = json.load(open(os.path.join(ROOT, "giscus.json"), encoding="utf-8"))
    except Exception:
        return ""
    return f"""    <div class="section wrap">
      <div id="giscus-thread"></div>
      <script src="https://giscus.app/client.js"
        data-repo="{REPO}"
        data-repo-id="{cfg['repo_id']}"
        data-category="Comments"
        data-category-id="{cfg['category_id']}"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="bottom"
        data-theme="preferred_color_scheme"
        data-lang="zh-CN"
        crossorigin="anonymous" async></script>
    </div>"""


# ---------------- 页面模板 ----------------
def home(latest):
    cards = "\n".join(post_card(p) for p in latest) or '      <p>文章即将上线，先去 <a href="https://www.youtube.com/@duzhu" target="_blank" rel="noopener">YouTube @duzhu</a> 看视频吧。</p>'
    inner = f"""
    <section class="hero">
      <span class="hero__kicker">AYS · 唤醒真我</span>
      <h1 class="hero__title">好好<em>吃饭</em>，<br/>把健康一口口吃回来</h1>
      <p class="hero__sub">Du株 · 持证营养师 + 互联网医疗从业者，用循证营养，陪你吃对每一天。</p>
      <div class="btn-row">
        <a class="btn btn--primary" href="articles.html">读最新文章</a>
        <a class="btn btn--ghost" href="https://www.youtube.com/@duzhu" target="_blank" rel="noopener">▷ 看 YouTube 频道</a>
      </div>
    </section>

    <section class="section wrap">
      <h2 class="section__title">为什么是「好好吃饭」</h2>
      <p class="section__lead">不节食、不焦虑，只把身体真正需要的营养，重新端上餐桌。</p>
      <div class="grid">
        <div class="card"><div class="card__icon">🥗</div><div class="card__title">循证优先</div><p class="card__text">每条建议尽量有依据，拒绝制造焦虑的伪科普。</p></div>
        <div class="card"><div class="card__icon">🎯</div><div class="card__title">可立即执行</div><p class="card__text">不教你玄学，只给今天就能用上的具体做法。</p></div>
        <div class="card"><div class="card__icon">📺</div><div class="card__title">视频 + 图文</div><p class="card__text">小中视频发四端，配套图文沉淀在这里。</p></div>
      </div>
    </section>

    <section class="section section--soft">
      <div class="wrap">
        <h2 class="section__title">内容系列</h2>
        <p class="section__lead">从「怎么吃对」起步，逐步覆盖体重管理、慢病饮食。</p>
        <div class="grid">
          <div class="card"><div class="card__title">① 怎么吃对</div><p class="card__text">24 种常见食材的吃法、搭配与坑。</p><a class="card__link" href="articles.html">查看系列 →</a></div>
          <div class="card"><div class="card__title">② 怎么瘦得稳</div><p class="card__text">不饿肚子的体重管理思路。</p><a class="card__link" href="articles.html">查看系列 →</a></div>
          <div class="card"><div class="card__title">③ 慢病饮食</div><p class="card__text">三高、肾健康等的日常饮食框架。</p><a class="card__link" href="articles.html">查看系列 →</a></div>
        </div>
      </div>
    </section>

    <section class="section wrap">
      <h2 class="section__title">最新文章</h2>
      <p class="section__lead">图文沉淀，配套视频在 YouTube @duzhu。</p>
      <div class="grid">
{cards}
      </div>
      <div style="text-align:center;margin-top:30px;"><a class="btn btn--ghost" href="articles.html">查看全部文章 →</a></div>
    </section>

    <section class="section section--soft">
      <div class="wrap" style="text-align:center;">
        <h2 class="section__title">在 YouTube 看视频</h2>
        <div class="yt" style="max-width:820px;margin:0 auto;">
          <iframe src="https://www.youtube.com/embed?listType=search&list=Du株%20AYS%20营养" title="Du株 YouTube" allowfullscreen></iframe>
        </div>
        <p class="yt__note">上方为占位嵌入，部署后替换为你的频道/视频真实链接。订阅 <a href="https://www.youtube.com/@duzhu" target="_blank" rel="noopener">@duzhu</a> 不错过更新。</p>
      </div>
    </section>
{subscribe_section()}"""
    return page("AYS · Du株 · 好好吃饭｜循证营养科普",
                "Du株的循证营养科普官网：怎么吃对、怎么瘦得稳、慢病饮食。配套 YouTube @duzhu 视频。",
                inner, SITE + "/index.html")


def list_page(posts):
    cards = "\n".join(post_card(p) for p in posts) or '      <p>暂无文章。</p>'
    inner = f"""
    <main class="wrap section">
      <h1 class="section__title">全部文章</h1>
      <p class="section__lead">循证营养科普，配套视频在 YouTube @duzhu。</p>
      <div class="grid">
{cards}
      </div>
    </main>"""
    return page("文章 · AYS · Du株", "Du株的全部营养科普文章列表。", inner, SITE + "/articles.html")


def article_page(p):
    cover = f'<img class="article__cover" src="{p["cover"]}" alt="{p["title"]}" />' if p["cover"] else ""
    inner = f"""
    <article class="article">
      <div class="article__meta">{p['date']} · {tags_html(p)}</div>
      <h1>{p['title']}</h1>
      {cover}
      {p['html']}
      {share_section(p)}
      {subscribe_section()}
    </article>
    {giscus_section()}"""
    ogimg = SITE + "/" + p["cover"] if p["cover"] else ""
    return page(p["title"] + " · AYS · Du株",
                p["summary"] or p["title"],
                inner, SITE + "/" + p["slug"] + ".html", ogimg)


# ---------------- 入口 ----------------
def main():
    os.makedirs(POSTS_DIR, exist_ok=True)
    posts = [parse_post(p) for p in glob.glob(os.path.join(POSTS_DIR, "*.md"))]
    posts.sort(key=pdate, reverse=True)

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(home(posts[:3]))
    with open(os.path.join(ROOT, "articles.html"), "w", encoding="utf-8") as f:
        f.write(list_page(posts))
    for p in posts:
        with open(os.path.join(ROOT, p["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(article_page(p))

    # sitemap
    urls = [SITE + "/index.html", SITE + "/about.html", SITE + "/articles.html"]
    urls += [SITE + "/" + p["slug"] + ".html" for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f"  <url><loc>{html.escape(u)}</loc></url>\n"
    sm += "</urlset>"
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sm)
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: " + SITE + "/sitemap.xml\n")

    print(f"构建完成：{len(posts)} 篇文章，生成 index/articles + {len(posts)} 篇详情 + sitemap/robots")


if __name__ == "__main__":
    main()
