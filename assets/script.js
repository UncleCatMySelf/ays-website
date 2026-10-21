/* AYS 官网交互脚本：深色模式 / 年份 / 当前导航高亮 */
(function () {
  "use strict";

  // 深色模式：读取偏好并应用
  var root = document.documentElement;
  var stored = null;
  try { stored = localStorage.getItem("ays-theme"); } catch (e) {}
  if (stored === "dark" || stored === "light") {
    root.setAttribute("data-theme", stored);
  } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    root.setAttribute("data-theme", "dark");
  }

  function applyTheme(t) {
    root.setAttribute("data-theme", t);
    try { localStorage.setItem("ays-theme", t); } catch (e) {}
    var btn = document.querySelector(".theme-toggle");
    if (btn) btn.textContent = t === "dark" ? "☀️" : "🌙";
    setGiscusTheme(t);
  }

  // 评论区（Giscus）跟随深色模式
  function setGiscusTheme(t) {
    var f = document.querySelector("iframe.giscus-frame");
    if (!f) return;
    f.contentWindow.postMessage({ giscus: { setTheme: t === "dark" ? "dark" : "light" } }, "https://giscus.app");
  }

  document.addEventListener("click", function (e) {
    if (e.target && e.target.closest(".theme-toggle")) {
      var cur = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(cur);
    }
    // 复制链接
    var cl = e.target && e.target.closest(".copy-link");
    if (cl) {
      e.preventDefault();
      var u = cl.getAttribute("data-url");
      var done = function () { var old = cl.textContent; cl.textContent = "已复制 ✓"; setTimeout(function(){ cl.textContent = old; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(u).then(done, function(){ location.href = u; });
      } else {
        location.href = u;
      }
    }
  });

  // 初始化按钮图标
  var initBtn = document.querySelector(".theme-toggle");
  if (initBtn) initBtn.textContent = root.getAttribute("data-theme") === "dark" ? "☀️" : "🌙";

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
