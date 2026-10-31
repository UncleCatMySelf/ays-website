# -*- coding: utf-8 -*-
"""
============================================================================
 文件：check_site.py
 项目：AYS · Du株 · 好好吃饭 官网（构建后自检）
 作者：神启（AI 助手，代主理人 Du株 维护）
 创建日期：2026-10-31（安全加固配套）
 版本：v1.0.0
 用途：build.py 跑完之后执行，检查生成的静态页有没有踩到安全红线、有没有断链。
 主要作用：
   1. 每个页面必须带 CSP（内容安全策略）
   2. 页面里不许出现内联 <style> 块、style="..." 行内样式、on*="..." 事件属性
   3. 页面里不许出现 javascript: / vbscript: / data:text/html 这类可执行链接
   4. 站内链接与图片地址必须真实存在（防断链）
   5. 所有 target="_blank" 的外链必须带 rel="noopener"
 依赖：仅标准库
 合规说明：纯本地只读检查，不联网、不修改任何文件；有问题是打印并返回非 0 退出码
用法：
   python check_site.py
============================================================================
"""
import os
import re
import sys
import glob
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
DANGER_TAGS = {"script", "iframe", "object", "embed", "form"}
DANGER_URL = ("javascript:", "vbscript:", "data:text/html")


class PageAudit(HTMLParser):
    """解析单个页面，收集安全问题和断链。"""

    def __init__(self, page):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.problems = []
        self.has_csp = False
        self.inline_style_block = 0
        self.links = []          # (tag, attr, value, attrs)
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)

        if tag == "meta" and (a.get("http-equiv") or "").lower() == "content-security-policy":
            self.has_csp = True

        if tag == "style":
            self._in_style = True
            self.inline_style_block += 1
            self.problems.append("出现内联 <style> 块（CSP style-src 'self' 会拦掉，样式会丢）")

        if tag in DANGER_TAGS and tag != "script":
            self.problems.append("出现禁用标签 <%s>" % tag)

        # 行内样式
        if "style" in a:
            self.problems.append("行内 style 属性：%s" % (a.get("style") or "")[:40])

        # 事件处理器
        for k, v in attrs:
            if k.startswith("on"):
                self.problems.append("内联事件属性 %s" % k)

        # 可执行协议
        for attr in ("href", "src", "action", "formaction"):
            v = a.get(attr)
            if v:
                probe = re.sub(r"[\x00-\x20\x7f]", "", v).lower()
                if probe.startswith(DANGER_URL):
                    self.problems.append("危险链接 %s=%s" % (attr, v[:50]))
                self.links.append((tag, attr, v, a))

        # 外链安全属性
        if a.get("target") == "_blank":
            rel = (a.get("rel") or "").lower()
            if "noopener" not in rel:
                self.problems.append("target=_blank 缺少 rel=noopener：%s" % (a.get("href") or "")[:50])

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False


def check_file(path):
    name = os.path.basename(path)
    html = open(path, encoding="utf-8").read()
    p = PageAudit(name)
    p.feed(html)

    if not p.has_csp:
        p.problems.append("缺少 Content-Security-Policy")

    # 断链检查：只查站内相对地址
    for tag, attr, val, _ in p.links:
        v = val.strip()
        if not v or v.startswith(("#", "http://", "https://", "mailto:", "tel:", "//", "data:")):
            continue
        target = v.split("#")[0].split("?")[0]
        if not target:
            continue
        full = os.path.normpath(os.path.join(ROOT, target))
        if not os.path.exists(full):
            p.problems.append("断链 %s=%s" % (attr, v))

    return p


def main():
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    if not pages:
        print("没有找到生成的页面，先运行 build.py")
        return 1

    total = 0
    for path in pages:
        p = check_file(path)
        if p.problems:
            total += len(p.problems)
            print("\n[有问题] %s" % p.page)
            for msg in p.problems:
                print("   - %s" % msg)
        else:
            print("[通过] %s" % p.page)

    # 附带检查：assets 下 CSS 是否都生成出来了
    for css in ("roadmap.css", "service.css"):
        if not os.path.exists(os.path.join(ROOT, "assets", css)):
            print("[有问题] 缺少 assets/%s（CSP 要求样式外置）" % css)
            total += 1

    print("\n" + "=" * 56)
    if total:
        print("自检未通过：%d 个问题，请修复后再发布。" % total)
        return 1
    print("自检通过：%d 个页面，无安全隐患、无断链。" % len(pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
