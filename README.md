# ays-website

AYS 唤醒真我 · Du株 · 好好吃饭 —— 官方网站（纯静态，托管于 GitHub Pages）

线上地址：https://unclecatmyself.github.io/ays-website/

## 技术构成

- 纯静态 HTML / CSS / 原生 JavaScript
- 无框架、无第三方 CDN、无统计脚本、无依赖清单
- 全部页面由 `build.py`（Python 标准库）从 `content/*.md` 生成

## 本地构建

```bash
python build.py        # 由 content/*.md 生成全部页面 + sitemap + robots
python check_site.py   # 构建后自检：CSP / 内联样式 / 危险链接 / 断链
```

不需要安装任何依赖，Python 3.8+ 即可运行。

## 目录结构

```
build.py          站点生成脚本（页面模板、Markdown 解析、URL 安全校验）
check_site.py     构建后自检脚本
content/          内容源文件（改文案只改这里）
  site.md           站点级设置：品牌、导航、关注渠道、反馈入口
  home.md           首页
  about.md          关于页
  roadmap.md        规划页
  service.md        服务页
  letters/          主理人寄语（每年一封；下划线开头的不参与构建）
posts/            文章源文件（Markdown）
assets/           样式、脚本、图片、二维码
```

## 安全基线

站点按以下基线维护，`check_site.py` 会自动校验：

- 每个页面下发严格 CSP（`default-src 'none'`，再按需逐个开白）
- 页面内不出现内联 `<style>`、行内样式、内联事件属性
- 链接与图片地址经协议白名单校验，拒绝 `javascript:` 等可执行协议
- 外链一律带 `rel="noopener noreferrer"`
- 不引入任何第三方资源；无密钥、无表单、不采集用户数据

## 内容说明

站内内容为营养科普，仅供参考，不替代医疗诊断。
