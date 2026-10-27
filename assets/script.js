/* ===========================================================================
 * 文件：assets/script.js
 * 项目：AYS · Du株 · 好好吃饭 官网（前端交互）
 * 作者：神启（AI 助手，代主理人 Du株 维护）
 * 创建日期：2026-10-21（官网 v1）
 * 最近维护：2026-10-27
 * 版本：v1.0.0（首次合规归档）
 * 用途：官网前端交互脚本（原生 JS，无框架、无第三方库）
 * 主要作用：
 *   - 导航汉堡菜单（≤768px 折叠 / 点链接收起 / 点外部关闭）
 *   - 关注渠道弹卡（悬停或移动端点按 切换二维码 / 外链卡）
 *   - 文章页"复制链接"、页脚年份等小交互
 *   - 注：官网为固定浅色品牌基调（无深色模式切换），故本脚本不含主题切换逻辑
 * 依赖：无
 * 合规说明：仅前端交互、不含密钥；与 assets/style.css 配套
 * ======================================================================== */
/* AYS 官网交互脚本：深色模式 / 年份 / 导航高亮 / 渠道弹卡 */
(function () {
  "use strict";

  document.addEventListener("click", function (e) {
    // 移动端汉堡菜单：切换展开，并同步 aria-expanded
    var tog = e.target && e.target.closest(".nav__toggle");
    if (tog) {
      var nav = document.getElementById("nav");
      if (nav) {
        var open = nav.classList.toggle("is-open");
        tog.setAttribute("aria-expanded", open ? "true" : "false");
      }
      return;
    }
    // 点击菜单内链接后自动收起
    var nl = e.target && e.target.closest(".nav__menu .nav__link");
    if (nl) {
      var nav2 = document.getElementById("nav");
      if (nav2) nav2.classList.remove("is-open");
    }

    // 二维码渠道：移动端点按出卡（桌面用 hover，由 CSS 控制）
    var qr = e.target && e.target.closest(".channel--qr");
    if (qr) {
      document.querySelectorAll(".channel.is-open").forEach(function (c) {
        if (c !== qr) c.classList.remove("is-open");
      });
      qr.classList.toggle("is-open");
      return;
    }
    // 点击别处关闭已打开的码卡
    if (!e.target.closest(".channel__card")) {
      document.querySelectorAll(".channel.is-open").forEach(function (c) {
        c.classList.remove("is-open");
      });
    }

    // 复制链接
    var cl = e.target && e.target.closest(".copy-link");
    if (cl) {
      e.preventDefault();
      var u = cl.getAttribute("data-url");
      var done = function () {
        var old = cl.textContent;
        cl.textContent = "已复制 ✓";
        setTimeout(function () { cl.textContent = old; }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(u).then(done, function () { location.href = u; });
      } else {
        location.href = u;
      }
    }

    // 点击导航以外区域收起汉堡菜单
    if (!e.target.closest("#nav")) {
      var nav3 = document.getElementById("nav");
      if (nav3) nav3.classList.remove("is-open");
    }
  });

  // 页脚年份
  var y = document.querySelector("[data-year]");
  if (y) y.textContent = new Date().getFullYear();

  // 当前导航高亮
  var here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav__link").forEach(function (a) {
    var href = a.getAttribute("href");
    if (href && href.indexOf(here) === 0 && here !== "index.html") a.classList.add("is-active");
    if (here === "index.html" && href === "index.html") a.classList.add("is-active");
  });
})();
