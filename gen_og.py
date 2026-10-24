# -*- coding: utf-8 -*-
"""生成官网默认分享图 assets/og-default.png（1200x630，薄荷绿品牌卡）。
复用 render_logo 的图标几何；中文用系统微软雅黑字体。
仅本地生成资源，不依赖外部渲染器。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_logo import draw_logo
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(ROOT, "assets", "logo")
FONT = r"C:\Windows\Fonts\msyh.ttc"

W, H = 1200, 630
C0 = (0x38, 0xd3, 0x94)
C1 = (0x1f, 0xaf, 0x77)

img = Image.new("RGBA", (W, H), C1 + (255,))
d = ImageDraw.Draw(img)

# 右下大圆做空间层次（浅薄荷，半透明叠加）
d.ellipse([W - 560, -180, W + 160, 760], fill=C0 + (255,))

# 左侧品牌图标（渐变方牌+碗筷）
logo = draw_logo(220)
lx, ly = 110, (H - 220) // 2
img.alpha_composite(logo, (lx, ly))

# 文案（右侧）
title_font = ImageFont.truetype(FONT, 132)
sub_font = ImageFont.truetype(FONT, 46)
tip_font = ImageFont.truetype(FONT, 40)

tx = 400
d.text((tx, 215), "好好吃饭", font=title_font, fill=(255, 255, 255, 255))
d.text((tx, 380), "AYS · Du株 · 循证营养", font=sub_font, fill=(255, 255, 255, 245))
d.text((tx, 460), "把健康一口口吃回来", font=tip_font, fill=(255, 255, 255, 220))

out = os.path.join(LOGO, "og-default.png")
img.convert("RGB").save(out, "PNG")
print("OK ->", out, img.size)
