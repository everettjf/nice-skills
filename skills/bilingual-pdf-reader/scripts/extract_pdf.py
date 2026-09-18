#!/usr/bin/env python3
"""把英文 PDF 抽成「编号段落」的 Markdown，供逐段翻译使用。

用法：
    python3 extract_pdf.py input.pdf [-o original.md]
                           [--start-page 1] [--end-page 0]
                           [--gap 1.35] [--keep-footnotes]
                           [--strip-markers / --no-strip-markers]

输出：
    一段一个 **N** 编号块 + YAML frontmatter（title/author 取自 PDF 元数据，
    抽不到就用文件名），末尾附「脚注」区（原书自带的注释，翻译时很有用）。

注意：这是**机器初切**。双栏、图注、练习题栏、页眉页脚都存在时，段落边界
一定会有出入，翻译前必须对照 PDF 复核（见 SKILL.md 第 2 步）。

依赖：PyMuPDF（pip install pymupdf）
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from pathlib import Path

def fitz_module():
    """延迟导入 PyMuPDF：这样纯文本逻辑（分组、清洗）无需装依赖也能自测。"""
    try:
        import fitz  # type: ignore
    except ImportError:  # pragma: no cover
        sys.exit("缺少依赖：pip install pymupdf")
    return fitz

PAGE_NUM_RE = re.compile(r"^[0-9ivxlcdmIVXLCDM]{1,6}$")
FOOTNOTE_RE = re.compile(r"^(\d{1,2})\.\s*(.*)$")
BRACKET_MARK_RE = re.compile(r"\[(\d{1,3})\]")
# 句末标点：行距分不出段落时，用它判断「上一行是否把话说完」
SENTENCE_END = (".", "!", "?", '"', "\u201d", "\u2019")


def page_lines(page: "fitz.Page") -> tuple[list[dict], float]:
    """取出一页的所有文本行，按阅读顺序返回（含双栏重排）。"""
    data = page.get_text("dict")
    lines: list[dict] = []
    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line.get("spans", [])).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            # 用「行底」当基线：上标脚注会把 bbox 顶边抬高，按 y0 排序会错序
            bottom = max(span["bbox"][3] for span in line.get("spans", []))
            lines.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "bottom": bottom, "text": text})
    width = page.rect.width
    return order_columns(lines, width), width


def order_columns(lines: list[dict], page_width: float) -> list[dict]:
    """简单双栏检测：若页面中部存在一条没有任何行跨越的中缝，就左栏读完再读右栏。"""
    if len(lines) < 8:
        return sorted(lines, key=lambda l: (l["bottom"], l["x0"]))
    best = None
    for frac in (0.5, 0.45, 0.55, 0.4, 0.6):
        gutter = page_width * frac
        crossing = [l for l in lines if l["x0"] < gutter < l["x1"]]
        left = [l for l in lines if l["x1"] <= gutter]
        right = [l for l in lines if l["x0"] >= gutter]
        if not crossing and len(left) >= 3 and len(right) >= 3:
            best = (left, right)
            break
    if best is None:
        return sorted(lines, key=lambda l: (l["bottom"], l["x0"]))
    left, right = best
    return sorted(left, key=lambda l: l["bottom"]) + sorted(right, key=lambda l: l["bottom"])


def merge_same_line(lines: list[dict]) -> list[dict]:
    """把被 PyMuPDF 拆成多段（字体变化、上标脚注）的同一视觉行合并回一行。"""
    merged: list[dict] = []
    for line in lines:
        if merged:
            prev = merged[-1]
            overlap = min(prev["y1"], line["y1"]) - max(prev["y0"], line["y0"])
            smaller = min(prev["y1"] - prev["y0"], line["y1"] - line["y0"]) or 1.0
            if overlap / smaller > 0.6:
                first, second = sorted([prev, line], key=lambda l: l["x0"])
                prev["text"] = (first["text"] + " " + second["text"]).strip()
                prev["x0"] = first["x0"]
                prev["x1"] = max(prev["x1"], second["x1"])
                prev["y0"] = min(prev["y0"], line["y0"])
                prev["y1"] = max(prev["y1"], line["y1"])
                prev["bottom"] = max(prev["bottom"], line["bottom"])
                continue
        merged.append(dict(line))
    return merged


def line_pitch(pages: list[list[dict]]) -> tuple[float, bool]:
    """全文级行距估计：返回 (行距, 是否有清晰双峰)。

    有双峰（行距 / 段距分得清）时按行距切段；没有双峰时说明这页几乎每行
    都是独立段落（对话、诗歌、清单），要改用「句子是否收尾」来判断。
    """
    gaps: list[float] = []
    for lines in pages:
        for i in range(len(lines) - 1):
            gap = lines[i + 1]["bottom"] - lines[i]["bottom"]
            if gap > 1.0:
                gaps.append(gap)
    if not gaps:
        return 12.0, False
    gaps.sort()
    # 找排序后最大的相对跳变，把间距分成「行距」和「段距」两簇
    best_ratio, best_idx = 0.0, 0
    for i in range(len(gaps) - 1):
        ratio = gaps[i + 1] / gaps[i]
        if ratio > best_ratio:
            best_ratio, best_idx = ratio, i
    if best_ratio >= 1.2:  # 双峰清晰：小簇就是行距
        return statistics.median(gaps[: best_idx + 1]), True
    return gaps[max(0, len(gaps) // 10)], False  # 双峰不清晰：退化为 10 分位


def group_paragraphs(
    lines: list[dict], gap_factor: float, pitch: float, bimodal: bool = True
) -> list[list[dict]]:
    """按行距、首行缩进、句子是否收尾，把行聚成段落。"""
    if not lines:
        return []
    median_gap = pitch
    body_left = statistics.median([l["x0"] for l in lines])

    paragraphs: list[list[dict]] = [[lines[0]]]
    for i, line in enumerate(lines[1:], start=1):
        prev = lines[i - 1]
        gap = line["bottom"] - prev["bottom"]
        indented = line["x0"] - body_left > median_gap * 2.2
        if bimodal:
            new_para = gap > max(median_gap * gap_factor, median_gap + 3.0)
            if not new_para and indented and gap > median_gap * 1.05:
                new_para = True
        else:
            # 没有双峰：行距本身就可能是段距，靠「上一行是否收尾 + 下一行是否另起」判断
            ends_sentence = prev["text"].rstrip().endswith(SENTENCE_END)
            head = line["text"].strip().lstrip("\"'\u201c\u201d\u2018\u2019([{")
            starts_new = bool(head[:1].isupper() or head[:1].isdigit())
            new_para = (
                (ends_sentence and starts_new and gap > median_gap * 0.95)
                or indented
                or gap > median_gap * 1.6
            )
        if new_para:
            paragraphs.append([line])
        else:
            paragraphs[-1].append(line)
    return paragraphs


def join_lines(paragraph: list[dict]) -> str:
    """段内换行拼成一行；行尾连字符视为断词。"""
    out = ""
    for line in paragraph:
        text = line["text"]
        if not out:
            out = text
        elif out.endswith("-") and not out.endswith("--"):
            out = out[:-1] + text
        else:
            out = out + " " + text
    return re.sub(r"\s+", " ", out).strip()


def repeated_furniture(pages: list[list[dict]]) -> set[str]:
    """跨页重复出现的行（页眉、书名、水印）→ 视为版式杂物。"""
    if len(pages) < 3:
        return set()
    counter: dict[str, int] = {}
    for lines in pages:
        for text in {l["text"] for l in lines}:
            counter[text] = counter.get(text, 0) + 1
    threshold = max(2, int(len(pages) * 0.6))
    return {t for t, c in counter.items() if c >= threshold and len(t) < 80}


def strip_markers(text: str, footnote_nums: set[str]) -> str:
    """去掉 [12] 这类角标，以及粘在单词尾部、且当页确有同名脚注的数字。"""
    text = BRACKET_MARK_RE.sub("", text)
    for num in sorted(footnote_nums, key=len, reverse=True):
        text = re.sub(rf"(?<=[A-Za-z.]){num}(?![\d])", "", text)
    return text


def extract(path: Path, args) -> tuple[str, int, list[str]]:
    fitz = fitz_module()
    doc = fitz.open(path)
    first = max(args.start_page - 1, 0)
    last = len(doc) if not args.end_page else min(args.end_page, len(doc))

    raw_pages: list[list[dict]] = []
    footnotes: list[str] = []
    per_page_footnote_nums: list[set[str]] = []
    for page in doc[first:last]:
        lines, _ = page_lines(page)
        nums: set[str] = set()
        for line in lines:
            match = FOOTNOTE_RE.match(line["text"])
            if match and int(match.group(1)) <= 30:
                nums.add(match.group(1))
        per_page_footnote_nums.append(nums)
        raw_pages.append(lines)

    raw_pages = [[*merge_same_line(lines)] for lines in raw_pages]
    furniture = repeated_furniture(raw_pages)
    pitch, bimodal = line_pitch(raw_pages)

    paragraphs: list[str] = []
    for lines, footnote_nums in zip(raw_pages, per_page_footnote_nums):
        keep: list[dict] = []
        i = 0
        while i < len(lines):
            text = lines[i]["text"].strip()
            i += 1
            if not text or text in furniture or PAGE_NUM_RE.match(text):
                continue
            match = FOOTNOTE_RE.match(text)
            is_footnote = bool(match) and int(match.group(1)) <= 30
            if is_footnote and not args.keep_footnotes:
                # 脚注区：数字可能单独占一行，释义在下一行
                body_text = match.group(2).strip()
                if not body_text and i < len(lines):
                    body_text = lines[i]["text"].strip()
                    i += 1
                footnotes.append(f"{match.group(1)}. {body_text}")
                continue
            keep.append({**lines[i - 1], "text": text})
        for paragraph in group_paragraphs(keep, args.gap, pitch, bimodal):
            text = join_lines(paragraph)
            if args.strip_markers:
                text = strip_markers(text, footnote_nums)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                paragraphs.append(text)

    title = (doc.metadata or {}).get("title") or path.stem
    author = (doc.metadata or {}).get("author") or ""
    doc.close()
    return title, author, paragraphs, footnotes


def render(path: Path, title: str, author: str, paragraphs: list[str], footnotes: list[str], pages: int) -> str:
    head = [
        "---",
        f"title: {title}",
        f"source: {path.name}",
    ]
    if author:
        head.append(f"author: {author}")
    head += [
        f"pages: {pages}",
        "stage: extracted",  # 提示：这一步只是机器初切
        "---",
        "",
        "<!-- 机器初切结果：段落边界、页眉页脚、练习题栏都可能需要人工复核 -->",
        "",
    ]
    body: list[str] = []
    for i, text in enumerate(paragraphs, start=1):
        body += [f"**{i}**", "", text, ""]
    if footnotes:
        body += ["## 脚注", ""]
        body += [f"- {note}" for note in dict.fromkeys(footnotes)]
        body += [""]
    return "\n".join(head + body)


def main() -> int:
    parser = argparse.ArgumentParser(description="英文 PDF → 编号段落 Markdown")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("-o", "--out", type=Path, help="输出 md（默认与 PDF 同名）")
    parser.add_argument("--start-page", type=int, default=1, help="起始页（1 起，默认 1）")
    parser.add_argument("--end-page", type=int, default=0, help="结束页（0 = 到末尾）")
    parser.add_argument("--gap", type=float, default=1.35, help="段间距阈值倍数，默认 1.35；段落被切太碎就调大")
    parser.add_argument("--keep-footnotes", action="store_true", help="脚注保留在正文流里（默认挪到文末）")
    parser.add_argument("--no-strip-markers", dest="strip_markers", action="store_false", help="不删角标数字")
    parser.set_defaults(strip_markers=True)
    args = parser.parse_args()

    if not args.pdf.exists():
        sys.exit(f"找不到文件：{args.pdf}")

    fitz = fitz_module()
    doc = fitz.open(args.pdf)
    total_pages = len(doc)
    doc.close()
    title, author, paragraphs, footnotes = extract(args.pdf, args)
    out = args.out or args.pdf.with_suffix(".md")
    out.write_text(
        render(args.pdf, title, author, paragraphs, footnotes, total_pages), encoding="utf-8"
    )

    words = sum(len(p.split()) for p in paragraphs)
    print(f"已抽取 {len(paragraphs)} 段 / 约 {words} 词 / {total_pages} 页 → {out}")
    print("下一步：对照 PDF 复核分段（合并被切碎的段、删掉封面与练习题栏），再逐段翻译。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
