#!/usr/bin/env python3
"""把《Codex完全零基础入门》全书.md 拆成分章网页。用法: build.py <src_dir> <out_site_dir>"""
import html, json, os, re, shutil, sys
from urllib.parse import unquote
import markdown
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
BOOK = os.path.join(OUT, "codex-guide")
ASSETS_IN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
REPO = "https://github.com/mali9527/codex-full-guide-for-beginners"
COMMIT = "f0393647dd6d2414b27e6bff191b849745b6f5b3"
TITLE = "Codex完全零基础入门"
KEEP = 5  # 只收录前 5 个单元：开篇 + 第1–4章

text = open(os.path.join(SRC, "book.md"), encoding="utf-8").read()
lines = text.splitlines()

# ---- 1. 按一级标题拆章；章节 slug 取标题前第一个 <a id> ----
ANCH = re.compile(r'^<a id="([^"]+)"></a>\s*$')
chapters, cur, pending = [], None, []
for ln in lines:
    m = ANCH.match(ln)
    if m:
        pending.append(m.group(1)); continue
    if ln.startswith("# "):
        cur = {"title": ln[2:].strip(), "slug": pending[0] if pending else "cover",
               "anchors": list(pending), "body": []}
        chapters.append(cur); pending = []; continue
    if cur is None:
        continue
    if ln.startswith("## ") or ln.startswith("### "):
        hashes, rest = ln.split(" ", 1)
        if pending:
            extra = "".join(f'<span id="{a}"></span>' for a in pending[:-1])
            ln = f"{hashes} {extra}{rest.strip()} {{#{pending[-1]}}}"
        pending = []
    elif pending and ln.strip():
        cur["body"].extend(f'<span id="{a}"></span>' for a in pending); pending = []
    if pending and not ln.strip():
        continue
    cur["body"].append(ln)

cover = chapters.pop(0)  # 书名 + 目录
id2page = {}
for ch in chapters:
    for a in ch["anchors"]:
        id2page[a] = ch["slug"]
    for a in re.findall(r'\{#([^}]+)\}|<span id="([^"]+)"', "\n".join(ch["body"])):
        id2page[a[0] or a[1]] = ch["slug"]

# ---- 2. 图片：压缩成 WebP ----
chapters = chapters[:KEEP]
kept = {ch["slug"] for ch in chapters}
shutil.rmtree(BOOK, ignore_errors=True)
imgdir = os.path.join(BOOK, "img"); os.makedirs(imgdir, exist_ok=True)
imgmap = {}
for p in re.findall(r'\]\((assets/illustrations/[^)]+)\)', "\n".join(l for ch in chapters for l in ch["body"])):
    if p in imgmap: continue
    fig = re.search(r'(FIG-\d+)', p).group(1)
    im = Image.open(os.path.join(SRC, "imgs", p)).convert("RGB")
    if im.width > 1600:
        im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    im.save(os.path.join(imgdir, fig + ".webp"), "WEBP", quality=84, method=6)
    imgmap[p] = (f"img/{fig}.webp", im.width, im.height)

# ---- 3. Markdown → HTML ----
def render(md_text):
    h = markdown.markdown(md_text, extensions=["tables", "fenced_code", "attr_list", "sane_lists"],
                          output_format="html5")
    # 图片 → figure
    def fig(m):
        alt = html.unescape(m.group(1)); src, w, hgt = imgmap[m.group(2)]
        return (f'<figure><img src="{src}" alt="{html.escape(alt, quote=True)}" width="{w}" height="{hgt}" loading="lazy">'
                f'<figcaption>{html.escape(alt)}</figcaption></figure>')
    h = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>', fig, h)
    # 内部链接
    def link(m):
        href = m.group(1)
        if href.startswith("#"):
            pid = href[1:]
            if pid in id2page and id2page[pid] not in kept:  # 未收录章节 → 原仓库
                return f'href="{REPO}/blob/main/%E5%85%A8%E4%B9%A6.md{href}" target="_blank" rel="noopener"'
            if pid in id2page:
                return f'href="{id2page[pid]}.html{"" if pid == id2page[pid] else href}"'
        elif not re.match(r'https?:|mailto:', href):
            return f'href="{REPO}/blob/main/{unquote(href)}" target="_blank" rel="noopener"'
        else:
            return f'href="{href}" target="_blank" rel="noopener"'
        return m.group(0)
    h = re.sub(r'href="([^"]+)"', link, h)
    h = re.sub(r'<table>', '<div class="table-wrap"><table>', h).replace("</table>", "</table></div>")
    h = h.replace("<blockquote>", '<blockquote class="prompt">')
    return h

def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

# ---- 4. 模板 ----
def nav_list(active):
    items = []
    for ch in chapters:
        cls = ' class="active" aria-current="page"' if ch["slug"] == active else ""
        m = re.match(r'^(第\d+章|开篇|附录)[：\s]*(.*)$', ch["title"])
        num, name = (m.group(1), m.group(2)) if m else ("", ch["title"])
        items.append(f'<li><a href="{ch["slug"]}.html"{cls}><span class="num">{num}</span>'
                     f'<span class="name">{html.escape(name)}</span></a></li>')
    return "\n".join(items)

LICENSE_NOTE = f"""<footer class="credit">
<p>原作：马力《<a href="{REPO}" target="_blank" rel="noopener">{TITLE}</a>》，采用
<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans" target="_blank" rel="noopener">CC BY-NC-SA 4.0</a> 许可。</p>
<p>本网页版据原仓库 <a href="{REPO}/blob/{COMMIT}/%E5%85%A8%E4%B9%A6.md" target="_blank" rel="noopener"><code>全书.md</code>（{COMMIT[:7]}）</a>改编，
本站只收录开篇至第4章，其余章节请到原仓库阅读。改动仅限排版与节选：按章拆分页面、重做版式与导航、插图转为 WebP 压缩、改写书内链接、未收录作者头像。正文未作修改。
本网页版同样以 CC BY-NC-SA 4.0 发布，仅供非商业阅读；内容以原仓库最新版为准。</p>
</footer>"""

def page(title, body, *, active=None, toc="", head_extra="", prev=None, nxt=None):
    tools = """<div class="tools">
  <button class="icon-btn" id="btn-search" aria-label="搜索" title="搜索 (/)"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button>
  <button class="icon-btn" id="btn-settings" aria-label="阅读设置" title="阅读设置"><span class="aa">Aa</span></button>
</div>"""
    pager = ""
    if prev or nxt:
        pa = f'<a class="prev" href="{prev["slug"]}.html"><small>← 上一章</small><span>{html.escape(prev["title"])}</span></a>' if prev else "<span></span>"
        na = f'<a class="next" href="{nxt["slug"]}.html"><small>下一章 →</small><span>{html.escape(nxt["title"])}</span></a>' if nxt else f'<a class="next" href="{REPO}/blob/main/%E5%85%A8%E4%B9%A6.md#account-usage" target="_blank" rel="noopener"><small>后续章节 ↗</small><span>第5章起，到原仓库继续阅读</span></a>'
        pager = f'<nav class="pager">{pa}{na}</nav>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="马力《{TITLE}》网页阅读版">
<link rel="stylesheet" href="style.css">
<script>try{{var t=localStorage.getItem("cg-theme");if(t)document.documentElement.dataset.theme=t;var f=localStorage.getItem("cg-font");if(f)document.documentElement.dataset.font=f;var s=localStorage.getItem("cg-size");if(s)document.documentElement.style.setProperty("--fs",s+"px")}}catch(e){{}}</script>
{head_extra}
</head>
<body data-page="{active or 'cover'}">
<div class="progress" id="progress"></div>
<header class="topbar">
  <button class="icon-btn" id="btn-menu" aria-label="目录"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button>
  <a class="brand" href="index.html">{TITLE}</a>
  <span class="crumb" id="crumb"></span>
  {tools}
</header>
<aside class="sidebar" id="sidebar">
  <a class="side-cover" href="index.html">封面与说明</a>
  <ol class="chapters">{nav_list(active)}</ol>
</aside>
<div class="scrim" id="scrim"></div>
<main class="main">
  <article class="content">{body}{pager}{LICENSE_NOTE}</article>
  {toc}
</main>
<div class="panel" id="settings" hidden>
  <div class="row"><span>主题</span><div class="seg" data-key="theme"><button data-v="light">浅色</button><button data-v="sepia">护眼</button><button data-v="dark">深色</button><button data-v="">自动</button></div></div>
  <div class="row"><span>字体</span><div class="seg" data-key="font"><button data-v="">黑体</button><button data-v="serif">宋体</button></div></div>
  <div class="row"><span>字号</span><div class="seg"><button id="fs-dec">A−</button><span id="fs-val">18</span><button id="fs-inc">A+</button></div></div>
</div>
<div class="search" id="search" hidden>
  <div class="search-box">
    <input id="search-input" type="search" placeholder="搜索全书，例如：权限、Skill、定时" autocomplete="off">
    <div id="search-results" class="results"></div>
  </div>
</div>
<div class="lightbox" id="lightbox" hidden><img alt=""></div>
<script src="app.js"></script>
</body>
</html>"""

# ---- 5. 生成章节页 + 搜索索引 ----
search = []
for i, ch in enumerate(chapters):
    body_html = render("\n".join(ch["body"]))
    heads = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body_html)
    toc = ""
    if heads:
        toc = '<nav class="toc" id="toc"><div class="toc-title">本章内容</div><ul>' + "".join(
            f'<li><a href="#{hid}">{strip_tags(t)}</a></li>' for hid, t in heads) + "</ul></nav>"
    full = f'<h1 id="{ch["slug"]}">{html.escape(ch["title"])}</h1>\n{body_html}'
    out = page(f'{ch["title"]} · {TITLE}', full, active=ch["slug"], toc=toc,
               prev=chapters[i - 1] if i else None, nxt=chapters[i + 1] if i + 1 < len(chapters) else None)
    open(os.path.join(BOOK, ch["slug"] + ".html"), "w", encoding="utf-8").write(out)
    # 按 h2 切分索引
    parts = re.split(r'(<h[23] id="[^"]+">.*?</h[23]>)', body_html)
    sec_id, sec_title, buf = ch["slug"], ch["title"], []
    def flush():
        t = strip_tags(" ".join(buf))
        if t: search.append({"p": ch["slug"], "c": ch["title"], "id": sec_id, "h": sec_title, "t": t})
    for part in parts:
        m = re.match(r'<h[23] id="([^"]+)">(.*?)</h[23]>', part)
        if m:
            flush(); sec_id, sec_title, buf = m.group(1), strip_tags(m.group(2)), []
        else:
            buf.append(part)
    flush()

json.dump(search, open(os.path.join(BOOK, "search.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---- 6. 封面页 ----
cards = []
for ch in chapters:
    m = re.match(r'^(第\d+章|开篇|附录)[：\s]*(.*)$', ch["title"])
    num, name = (m.group(1), m.group(2)) if m else ("", ch["title"])
    cards.append(f'<li><a href="{ch["slug"]}.html"><span class="num">{num}</span><span class="name">{html.escape(name)}</span></a></li>')
cover_body = f"""<div class="cover">
  <p class="eyebrow">网页阅读版</p>
  <h1 class="cover-title">{TITLE}</h1>
  <p class="author">马力 著</p>
  <p class="lead">写给没有编程经验的人：从安装应用、发出第一条消息，到权限、Plan、Goal、Skill、插件和定时任务，一步步学会用 Codex 把一件事真正做完。</p>
  <p class="lead">本站收录开篇与第1–4章：从认识 Codex、安装应用，到完成第一件完整任务。后续章节请到<a href="{REPO}" target="_blank" rel="noopener">原仓库</a>阅读。</p>
  <div class="cta"><a class="btn primary" href="{chapters[0]['slug']}.html">开始阅读</a><a class="btn" id="resume" hidden href="#">继续阅读</a></div>
</div>
<h2 id="contents">目录</h2>
<ol class="cover-toc">{''.join(cards)}</ol>
<p class="hint">阅读小提示：按 <kbd>/</kbd> 搜索全书，按 <kbd>←</kbd> <kbd>→</kbd> 翻章，右上角 <b>Aa</b> 可以调主题、字体和字号。</p>"""
open(os.path.join(BOOK, "index.html"), "w", encoding="utf-8").write(page(TITLE, cover_body))

for f in ("style.css", "app.js"):
    shutil.copy(os.path.join(ASSETS_IN, f), os.path.join(BOOK, f))
print(f"{len(chapters)} chapters, {len(search)} search sections, {len(imgmap)} images")
