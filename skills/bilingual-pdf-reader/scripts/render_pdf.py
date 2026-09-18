#!/usr/bin/env python3
"""把逐段中英对照的 Markdown 排成 A4 阅读版 PDF（封面 + 段落 + 生词行 + 译注）。

用法：
    python3 render_pdf.py bilingual.md [-o bilingual.pdf]
                            [--title 中文标题] [--original 英文原名]
                            [--author 作者] [--year 1983]
                            [--no-cover] [--accent "#c8a86b"] [--keep-html]

Markdown 结构（见 assets/bilingual-template.md）：

    ---
    title: 中文标题
    original: English Title
    author: 作者
    year: 1983
    ---
    ## 正文
    **1**
    English paragraph.
    > 中文译文。
    生词：**word** /ipa/ *n.* 释义 · …

依赖：weasyprint（pip install weasyprint）。中文字体优先用系统自带的
Songti SC / Noto Serif CJK / Source Han Serif，西文用 Georgia / Times。
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FONT_STACK_SERIF = '"Georgia", "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "Hiragino Sans GB", serif'
FONT_STACK_SANS = '"Helvetica Neue", "Heiti SC", "Noto Sans CJK SC", "Source Han Sans SC", "Hiragino Sans GB", sans-serif'
FONT_STACK_MONO = '"SF Mono", Menlo, Consolas, monospace'

CSS_TEMPLATE = """
@page {{
  size: {paper};
  margin: 20mm 18mm 18mm 18mm;
  @bottom-center {{
    content: counter(page);
    font-family: {serif};
    font-size: 8.5pt;
    color: #8a8377;
  }}
  @bottom-right {{
    content: "{running}";
    font-family: {serif};
    font-size: 7.5pt;
    color: #b3aca0;
  }}
}}
@page :first {{
  @bottom-right {{ content: ""; }}
  @bottom-center {{ content: ""; }}
}}

html {{
  font-family: {serif};
  font-size: 10pt;
  color: #1c1a17;
  line-height: 1.62;
}}

.cover {{ padding-top: 70mm; text-align: center; }}
.cover h1 {{
  font-family: {sans};
  font-size: 27pt;
  font-weight: 600;
  letter-spacing: 2pt;
  margin: 0 0 6pt 0;
}}
.cover .orig {{
  font-family: {serif};
  font-size: 14pt;
  font-style: italic;
  color: #6d665c;
  margin: 0 0 22pt 0;
}}
.cover .rule {{ width: 46mm; height: 1.6pt; background: {accent}; margin: 0 auto 22pt auto; }}
.cover .by {{ font-family: {sans}; font-size: 11.5pt; color: #3d3830; }}
.cover .meta {{ font-size: 9pt; color: #8a8377; margin-top: 4pt; }}
.cover .tags {{ margin-top: 30pt; font-size: 9pt; color: #8a8377; letter-spacing: 1pt; }}

.note {{
  border-left: 2.4pt solid {accent};
  background: #faf7f0;
  padding: 7pt 10pt;
  margin: 10pt 0;
  font-size: 9pt;
  line-height: 1.55;
  color: #4a443b;
  break-inside: avoid;
}}
.note .label {{
  font-family: {sans};
  font-size: 8.5pt;
  letter-spacing: 0.6pt;
  color: #9a7f42;
  display: block;
  margin-bottom: 2pt;
}}
.note.warn {{ border-left-color: #b4553f; background: #fbf4f2; }}
.note.warn .label {{ color: #a04a36; }}

h2 {{
  font-family: {sans};
  font-size: 14pt;
  font-weight: 600;
  color: #2b2721;
  margin: 16pt 0 4pt 0;
  padding-bottom: 4pt;
  border-bottom: 0.8pt solid #ddd6c8;
  break-after: avoid;
}}
.pagebreak {{ break-before: page; }}

.pair {{ margin: 0 0 9pt 0; }}
p {{ margin: 0; orphans: 2; widows: 2; }}
p.en {{ text-align: left; hyphens: none; }}
p.cn {{
  margin-top: 2.5pt;
  padding-left: 8pt;
  border-left: 1.6pt solid #e4ddd0;
  color: #100e0c;
  text-align: justify;
}}
.num {{
  font-family: {serif};
  font-size: 7.5pt;
  color: #b99a5c;
  vertical-align: 0.28em;
  margin-right: 4pt;
  letter-spacing: 0.3pt;
}}
p.vocab {{
  margin: 3.5pt 0 0 0;
  padding: 3.5pt 0 0 8pt;
  border-left: 1.6pt solid #e4ddd0;
  font-size: 8.3pt;
  line-height: 1.55;
  color: #6d665c;
}}
p.vocab .vlabel {{
  font-family: {sans};
  font-size: 7pt;
  letter-spacing: 0.8pt;
  color: #a98b4c;
  background: #f6f1e6;
  border-radius: 2pt;
  padding: 1pt 3.5pt;
  margin-right: 6pt;
}}
p.vocab strong {{ font-family: {serif}; font-weight: 600; font-size: 8.8pt; color: #17150f; }}
p.vocab .ipa {{ color: #9a9384; }}
p.vocab em {{ font-style: italic; color: #a89272; }}

p.label {{
  font-family: {sans};
  font-size: 8pt;
  letter-spacing: 1.2pt;
  color: #9a7f42;
  margin: 12pt 0 3pt 0;
}}
ol.notes {{ margin: 0; padding-left: 16pt; }}
ol.notes li {{ margin-bottom: 6pt; text-align: justify; }}
ol.notes li::marker {{ color: #b99a5c; font-family: {serif}; }}
.colophon {{
  margin-top: 18pt;
  padding-top: 8pt;
  border-top: 0.8pt solid #ddd6c8;
  font-size: 8.5pt;
  color: #7d766a;
  line-height: 1.5;
}}
code {{ font-family: {mono}; font-size: 8.6pt; }}
"""


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    return text


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields, text[match.end():]


def parse(text: str):
    out: list[tuple[str, object]] = []
    lines = text.split("\n")
    buf: list[str] = []
    mode: str | None = None
    in_notes = False

    def flush() -> None:
        nonlocal buf, mode
        if buf:
            out.append((mode or "plain", " ".join(buf)))
        buf, mode = [], None

    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        i += 1
        if not s:
            continue
        if s == "---":
            flush()
            continue
        if s.startswith("> ["):  # Obsidian 风格提示框
            flush()
            kind = "warn" if "[!warning]" in s else "info"
            label = s.split("]", 1)[1].strip()
            body = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                body.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(("note", (kind, label, " ".join(body))))
            continue
        if s.startswith("### "):
            flush()
            out.append(("h3", s[4:].strip()))
            continue
        if s.startswith("## "):
            flush()
            heading = s[3:].strip()
            in_notes = heading.startswith("译注")
            out.append(("h2", heading))
            continue
        if s.startswith("# "):
            flush()
            out.append(("h1", s[2:].strip()))
            continue
        if s.startswith("> "):
            if mode not in (None, "cn"):
                flush()
            mode = "cn"
            buf.append(s[2:].strip())
            continue
        if s.startswith("生词："):
            flush()
            out.append(("vocab", s))
            continue
        bold = re.fullmatch(r"\*\*(.+?)\*\*", s)
        if bold:
            flush()
            inner = bold.group(1).strip()
            out.append(("num", inner) if inner.isdigit() else ("label", inner))
            continue
        if in_notes and re.match(r"^\d+\.\s", s):
            flush()
            item = re.sub(r"^\d+\.\s", "", s)
            while i < len(lines) and lines[i].strip() and not re.match(r"^\d+\.\s", lines[i].strip()) and lines[i].strip() != "---":
                item += " " + lines[i].strip()
                i += 1
            out.append(("li", item))
            continue
        if mode not in (None, "en"):
            flush()
        mode = "en"
        buf.append(s)
    flush()
    return out


def build_html(items, meta: dict[str, str], args) -> tuple[str, int, int]:
    title = args.title or meta.get("title", "双语阅读")
    original = args.original or meta.get("original", "")
    author = args.author or meta.get("author", "")
    year = args.year or meta.get("year", "")
    paragraphs = [p for k, p in items if k == "num"]
    vocab_entries = sum(
        len([x for x in str(payload)[len("生词："):].split(" · ") if x.strip()])
        for kind, payload in items
        if kind == "vocab"
    )
    body: list[str] = []

    if not args.no_cover:
        meta_bits = []
        if year:
            meta_bits.append(f"{year} 年")
        cover = [
            '<div class="cover">',
            f"<h1>{inline(title)}</h1>",
        ]
        if original:
            cover.append(f'<p class="orig">{inline(original)}</p>')
        cover.append('<div class="rule"></div>')
        if author:
            cover.append(f'<div class="by">{inline(author)}</div>')
        if meta_bits:
            cover.append(f'<div class="meta">{"　".join(meta_bits)}</div>')
        cover.append(f'<div class="tags">逐段中英对照　·　全文 {len(paragraphs)} 段</div>')
        cover.append("</div>")
        cover.append('<div class="pagebreak"></div>')
        body.append("".join(cover))

    pending_num = ""
    pair_open = False

    def close_pair() -> None:
        nonlocal pair_open
        if pair_open:
            body.append("</div>")
            pair_open = False

    for kind, payload in items:
        if kind in ("h1", "h3"):
            continue
        if kind == "note":
            close_pair()
            note_kind, label, text = payload  # type: ignore[misc]
            cls = "note warn" if note_kind == "warn" else "note"
            body.append(f'<div class="{cls}"><span class="label">{inline(label)}</span>{inline(text)}</div>')
            continue
        if kind == "h2":
            close_pair()
            body.append(f"<h2>{inline(str(payload))}</h2>")
            continue
        if kind == "num":
            close_pair()
            pending_num = str(payload)
            continue
        if kind == "label":
            close_pair()
            body.append(f'<p class="label">{inline(str(payload))}</p>')
            continue
        if kind == "en":
            close_pair()
            tag = f'<span class="num">{pending_num}</span>' if pending_num else ""
            pending_num = ""
            body.append(f'<div class="pair"><p class="en">{tag}{inline(str(payload))}</p>')
            pair_open = True
            continue
        if kind == "cn":
            body.append(f'<p class="cn">{inline(str(payload))}</p>')
            continue
        if kind == "vocab":
            text = inline(str(payload)[len("生词："):])
            text = re.sub(r"(?<!<)/([^/<>]{1,40})/", r'<span class="ipa">/\1/</span>', text)
            body.append(f'<p class="vocab"><span class="vlabel">生词</span>{text}</p>')
            close_pair()
            continue
        if kind == "li":
            close_pair()
            body.append(f"<li>{inline(str(payload))}</li>")
            continue
        close_pair()
        text = inline(str(payload))
        if text.startswith("&quot;"):
            body.append(f'<div class="colophon">{text}</div>')
        else:
            body.append(f"<p>{text}</p>")

    close_pair()
    doc = "\n".join(body)
    doc = re.sub(r'(<h2>译注[^<]*</h2>)((?:<li>.*?</li>)+)', r'\1<ol class="notes">\2</ol>', doc, flags=re.S)
    return doc, len(paragraphs), vocab_entries


def main() -> int:
    parser = argparse.ArgumentParser(description="双语 Markdown → A4 PDF")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--original")
    parser.add_argument("--author")
    parser.add_argument("--year")
    parser.add_argument("--paper", default="A4")
    parser.add_argument("--accent", default="#c8a86b")
    parser.add_argument("--no-cover", action="store_true")
    parser.add_argument("--keep-html", action="store_true", help="保留中间 HTML 便于排查")
    args = parser.parse_args()

    if shutil.which("weasyprint") is None:
        try:
            import weasyprint  # noqa: F401
        except ImportError:
            sys.exit("缺少依赖：pip install weasyprint（或 brew install weasyprint）")

    raw = args.markdown.read_text(encoding="utf-8")
    meta, body_text = parse_frontmatter(raw)
    items = parse(body_text)
    content, paragraphs, vocab_entries = build_html(items, meta, args)

    css = CSS_TEMPLATE.format(
        paper=args.paper,
        serif=FONT_STACK_SERIF,
        sans=FONT_STACK_SANS,
        mono=FONT_STACK_MONO,
        accent=args.accent,
        running=inline(args.title or meta.get("title", ""))[:28],
    )
    html_doc = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>{inline(args.title or meta.get('title', '双语阅读'))}</title>"
        f"<style>{css}</style></head><body>{content}</body></html>"
    )

    out = args.out or args.markdown.with_suffix(".pdf")
    tmp_html = Path(tempfile.mkdtemp()) / "bilingual.html"
    tmp_html.write_text(html_doc, encoding="utf-8")
    if args.keep_html:
        Path(out).with_suffix(".html").write_text(html_doc, encoding="utf-8")

    env = dict(os.environ)
    # 无家目录写权限时，把 fontconfig 缓存挪到临时目录，避免字体扫描失败
    env.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "fc-cache"))
    Path(env["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)

    if shutil.which("weasyprint"):
        cmd = ["weasyprint", "-e", "utf-8", str(tmp_html), str(out)]
    else:
        cmd = [sys.executable, "-m", "weasyprint", "-e", "utf-8", str(tmp_html), str(out)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        return result.returncode

    size_kb = out.stat().st_size / 1024
    print(f"已生成 {out}（{paragraphs} 段 / {vocab_entries} 条生词 / {size_kb:.0f} KB）")
    print("建议：抽 1–2 页渲染成图目检，再跑 check_bilingual.py 做交付自检。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
