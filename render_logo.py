# -*- coding: utf-8 -*-
"""
============================================================================
 文件：render_logo.py
 项目：AYS · Du株 · 好好吃饭 官网（资源生成工具）
 作者：神启（AI 助手，代主理人 Du株 维护）
 创建日期：2026-10-22（官网图标 logo-tile 定稿）
 最近维护：2026-10-27
 版本：v1.0.0（首次合规归档）
 用途：按 logo-tile.svg 的精确几何，用 Pillow 重绘多尺寸 PNG 网站图标。
 主要作用：
   - 复现薄荷绿渐变方牌 + 白碗米饭 + 斜筷的矢量几何
   - 输出 favicon.ico（16/32/48）、apple-touch-icon.png（180）等多尺寸资源
 依赖：Pillow（PIL）、numpy
 合规说明：纯本地资源生成，不联网、不含密钥；坐标取自 512 空间源 SVG 按比例缩放
============================================================================
按 logo-tile.svg 的精确几何，用 Pillow 重绘多尺寸 PNG 图标。
不依赖外部 SVG 渲染器；所有坐标取自 512 空间的源 SVG，按比例缩放。"""
import numpy as np
from PIL import Image, ImageDraw

C0 = (0x38, 0xd3, 0x94)   # 渐变左上
C1 = (0x1f, 0xaf, 0x77)   # 渐变右下
WHITE = (255, 255, 255, 255)
RICE = (0xd4, 0xf0, 0xe2, 255)


def cubic(p0, p1, p2, p3, n=48):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
        y = mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts


def quad(p0, p1, p2, n=32):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt*mt*p0[0] + 2*mt*t*p1[0] + t*t*p2[0]
        y = mt*mt*p0[1] + 2*mt*t*p1[1] + t*t*p2[1]
        pts.append((x, y))
    return pts


def draw_logo(S):
    scale = S / 512.0
    arr = np.zeros((S, S, 4), dtype=np.uint8)
    ys, xs = np.mgrid[0:S, 0:S]
    t = np.clip((xs + ys) / (2.0 * S), 0, 1)
    col = (np.array(C0) * (1 - t)[..., None] + np.array(C1) * t[..., None]).astype(np.uint8)
    arr[..., :3] = col
    arr[..., 3] = 255
    # 圆角矩形蒙版 (512 空间: x16 y16 w480 h480 r112)
    x0, y0, x1, y1, r = 16*scale, 16*scale, 496*scale, 496*scale, 112*scale
    mask = np.zeros((S, S), bool)
    mask[int(y0+r):int(y1-r)+1, int(x0):int(x1)+1] = True
    mask[int(y0):int(y1)+1, int(x0+r):int(x1-r)+1] = True
    for cx, cy in [(x0+r, y0+r), (x1-r, y0+r), (x0+r, y1-r), (x1-r, y1-r)]:
        d = (xs - cx)**2 + (ys - cy)**2
        mask |= (d <= r*r)
    arr[~mask] = 0
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    sw = max(2, int(20 * scale))
    # 碗身
    b1 = cubic((106, 300), (106, 402), (176, 448), (256, 448))
    b2 = cubic((256, 448), (336, 448), (406, 402), (406, 300))
    poly = [(x*scale, y*scale) for x, y in b1 + b2]
    d.polygon(poly, fill=WHITE)
    # 碗口
    cx, cy, rx, ry = 256*scale, 300*scale, 150*scale, 40*scale
    d.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=WHITE)
    # 米饭
    rcx, rcy, rrx, rry = 256*scale, 292*scale, 120*scale, 29*scale
    d.ellipse([rcx-rrx, rcy-rry, rcx+rrx, rcy+rry], fill=RICE)
    rq = quad((170, 286), (256, 246), (342, 286))
    d.polygon([(x*scale, y*scale) for x, y in rq], fill=RICE)
    # 筷子
    d.line([(150*scale, 292*scale), (362*scale, 150*scale)], fill=WHITE, width=sw, joint="curve")
    d.line([(170*scale, 302*scale), (382*scale, 160*scale)], fill=WHITE, width=sw, joint="curve")
    return img


if __name__ == "__main__":
    import os
    ROOT = os.path.dirname(os.path.abspath(__file__))
    LOGO = os.path.join(ROOT, "assets", "logo")
    DESK = r"C:\Users\HY00400896\Desktop"
    os.makedirs(LOGO, exist_ok=True)

    # favicon.ico (16/32/48 内嵌多尺寸)
    ico = draw_logo(48)
    ico.save(os.path.join(LOGO, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    # apple-touch-icon 180
    draw_logo(180).save(os.path.join(LOGO, "apple-touch-icon.png"))
    # 小程序图标：1024 主图 + 144 微信后台要求
    draw_logo(1024).save(os.path.join(DESK, "AYS小程序图标-1024.png"))
    draw_logo(144).save(os.path.join(DESK, "AYS小程序图标-144.png"))
    # 预览用 512
    draw_logo(512).save(os.path.join(LOGO, "_preview_512.png"))
    print("OK ->", os.listdir(LOGO))
    print("桌面 ->", [f for f in os.listdir(DESK) if f.startswith("AYS小程序")])
