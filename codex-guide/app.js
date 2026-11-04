(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { if (v === "" || v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }
  };
  var root = document.documentElement, body = document.body, page = body.dataset.page;

  // 侧栏（手机）
  $("#btn-menu").onclick = function () { body.classList.toggle("nav-open"); };
  $("#scrim").onclick = function () { body.classList.remove("nav-open"); };
  var act = $(".chapters a.active"); if (act) act.scrollIntoView({ block: "center" });

  // 记住阅读位置
  if (page !== "cover") {
    store.set("cg-last", page);
    var h1 = $(".content h1"); if (h1) store.set("cg-last-title", h1.textContent);
  } else {
    var last = store.get("cg-last"), r = $("#resume");
    if (last && r) { r.href = last + ".html"; r.textContent = "继续阅读：" + (store.get("cg-last-title") || ""); r.hidden = false; }
  }

  // 阅读设置
  var panel = $("#settings");
  $("#btn-settings").onclick = function (e) { e.stopPropagation(); panel.hidden = !panel.hidden; };
  document.addEventListener("click", function (e) { if (!panel.hidden && !panel.contains(e.target)) panel.hidden = true; });
  function syncSeg() {
    $$(".seg[data-key]").forEach(function (seg) {
      var cur = root.dataset[seg.dataset.key] || "";
      $$("button", seg).forEach(function (b) { b.classList.toggle("on", b.dataset.v === cur); });
    });
    $("#fs-val").textContent = parseInt(getComputedStyle(root).getPropertyValue("--fs"), 10);
  }
  $$(".seg[data-key] button").forEach(function (b) {
    b.onclick = function () {
      var key = b.parentNode.dataset.key;
      if (b.dataset.v) root.dataset[key] = b.dataset.v; else delete root.dataset[key];
      store.set("cg-" + key, b.dataset.v); syncSeg();
    };
  });
  function setFs(d) {
    var v = Math.min(24, Math.max(14, parseInt(getComputedStyle(root).getPropertyValue("--fs"), 10) + d));
    root.style.setProperty("--fs", v + "px"); store.set("cg-size", String(v)); syncSeg();
  }
  $("#fs-dec").onclick = function () { setFs(-1); };
  $("#fs-inc").onclick = function () { setFs(1); };
  syncSeg();

  // 进度条 + 本章目录高亮 + 面包屑
  var bar = $("#progress"), tocLinks = $$("#toc a"), crumb = $("#crumb");
  var heads = tocLinks.map(function (a) { return document.getElementById(decodeURIComponent(a.hash.slice(1))); });
  var h1el = $(".content h1");
  function onScroll() {
    var d = document.documentElement, max = d.scrollHeight - d.clientHeight;
    bar.style.width = (max > 0 ? (d.scrollTop / max) * 100 : 0) + "%";
    var idx = -1;
    for (var i = 0; i < heads.length; i++) { if (heads[i] && heads[i].getBoundingClientRect().top < 120) idx = i; }
    tocLinks.forEach(function (a, i) { a.classList.toggle("active", i === idx); });
    if (crumb && page !== "cover") crumb.textContent = idx >= 0 ? heads[idx].textContent : (h1el ? h1el.textContent : "");
  }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  // 提示词复制
  $$("blockquote.prompt").forEach(function (q) {
    var b = document.createElement("button"); b.className = "copy"; b.type = "button"; b.textContent = "复制";
    b.onclick = function () {
      var t = $$("p", q).map(function (p) { return p.textContent; }).join("\n\n");
      var done = function () { b.textContent = "已复制"; setTimeout(function () { b.textContent = "复制"; }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(t).then(done, function () {});
    };
    q.appendChild(b);
  });

  // 图片放大
  var lb = $("#lightbox");
  $$(".content figure img").forEach(function (img) {
    img.onclick = function () { $("img", lb).src = img.src; $("img", lb).alt = img.alt; lb.hidden = false; };
  });
  lb.onclick = function () { lb.hidden = true; };

  // 搜索
  var sBox = $("#search"), sIn = $("#search-input"), sRes = $("#search-results"), data = null, sel = -1;
  function openSearch() {
    sBox.hidden = false; sIn.focus(); sIn.select();
    if (!data) fetch("search.json").then(function (r) { return r.json(); }).then(function (j) { data = j; run(); })
      .catch(function () { sRes.innerHTML = '<div class="empty">索引加载失败（本地直接打开文件时浏览器会拦截，请通过网站访问）</div>'; });
  }
  function closeSearch() { sBox.hidden = true; }
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function hl(s, terms) {
    var out = esc(s);
    terms.forEach(function (t) { out = out.split(esc(t)).join("\u0001" + esc(t) + "\u0002"); });
    return out.replace(/\u0001/g, "<mark>").replace(/\u0002/g, "</mark>");
  }
  function run() {
    if (!data) return;
    var q = sIn.value.trim().toLowerCase(); sel = -1;
    if (!q) { sRes.innerHTML = ""; return; }
    var terms = q.split(/\s+/).filter(Boolean), hits = [];
    data.forEach(function (d) {
      var hl_ = d.h.toLowerCase(), tl = d.t.toLowerCase(), score = 0;
      for (var i = 0; i < terms.length; i++) {
        var inH = hl_.indexOf(terms[i]) >= 0, inT = tl.indexOf(terms[i]);
        if (!inH && inT < 0) return;
        score += (inH ? 10 : 0) + (inT >= 0 ? 1 : 0);
      }
      var pos = Math.max(0, tl.indexOf(terms[0])), start = Math.max(0, pos - 30);
      var snip = (start ? "…" : "") + d.t.slice(start, start + 110) + (start + 110 < d.t.length ? "…" : "");
      hits.push({ d: d, s: score, snip: snip });
    });
    hits.sort(function (a, b) { return b.s - a.s; });
    sRes.innerHTML = hits.length ? hits.slice(0, 40).map(function (h) {
      var href = h.d.p + ".html" + (h.d.id === h.d.p ? "" : "#" + encodeURIComponent(h.d.id));
      return '<a href="' + href + '"><div class="r-c">' + esc(h.d.c) + '</div><div class="r-h">' + hl(h.d.h, terms) +
        '</div><div class="r-t">' + hl(h.snip, terms) + "</div></a>";
    }).join("") : '<div class="empty">没有找到相关内容</div>';
  }
  sIn.addEventListener("input", run);
  sIn.addEventListener("keydown", function (e) {
    var items = $$("a", sRes); if (!items.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items.forEach(function (a, i) { a.classList.toggle("sel", i === sel); }); items[sel].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") { (items[sel] || items[0]).click(); }
  });
  sRes.addEventListener("click", function (e) { if (e.target.closest("a")) closeSearch(); });
  $("#btn-search").onclick = openSearch;
  sBox.addEventListener("click", function (e) { if (e.target === sBox) closeSearch(); });

  // 键盘
  document.addEventListener("keydown", function (e) {
    var typing = /INPUT|TEXTAREA/.test(document.activeElement.tagName);
    if (e.key === "Escape") { closeSearch(); panel.hidden = true; lb.hidden = true; body.classList.remove("nav-open"); return; }
    if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "/") { e.preventDefault(); openSearch(); }
    else if (e.key === "ArrowLeft") { var p = $(".pager .prev"); if (p) location.href = p.href; }
    else if (e.key === "ArrowRight") { var n = $(".pager .next"); if (n) location.href = n.href; }
  });
})();
