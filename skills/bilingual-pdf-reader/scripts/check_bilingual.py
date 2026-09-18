#!/usr/bin/env python3
"""交付自检：结构、生词行格式、英文保真、PDF 成品。

用法：
    python3 check_bilingual.py bilingual.md
    python3 check_bilingual.py bilingual.md --source original.pdf
    python3 check_bilingual.py bilingual.md --source original.pdf --pdf bilingual.pdf
    python3 check_bilingual.py bilingual.md --strict     # 把英文差异也算成错误

检查项：
    1. 结构：frontmatter、段号连续、每段都有英文 + 中文译文；
    2. 生词行：格式、音标斜杠、词性取值、词条是否真的出现在该段英文里；
    3. 英文保真：与源 PDF 的词流比对，列出「原文有、译文缺」和「多出来」的部分；
    4. PDF：页数、有没有漏出 HTML 标签、中文是否正常写入、字体是否内嵌。

退出码：有错误时为 1。
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
import unicodedata
from pathlib import Path

PARA_RE = re.compile(r"^\*\*(\d+)\*\*$")
VOCAB_PREFIX = "生词："
ALLOWED_POS = {
    "n.", "v.", "vt.", "vi.", "adj.", "adv.", "prep.", "conj.", "pron.",
    "num.", "art.", "int.", "aux.", "abbr.", "词组", "习语", "俚语", "专名",
}
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ENTRY_RE = re.compile(r"^\*\*(?P<word>[^*]+)\*\*(?:\s+(?P<ipa>/[^/]+/))?(?:\s+\*(?P<pos>[^*]+)\*)?\s+(?P<meaning>.+)$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.infos: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def info(self, message: str) -> None:
        self.infos.append(message)

    def dump(self) -> int:
        for message in self.infos:
            print(f"[信息] {message}")
        for message in self.warnings:
            print(f"[警告] {message}")
        for message in self.errors:
            print(f"[错误] {message}")
        print()
        print(f"结论：{len(self.errors)} 个错误，{len(self.warnings)} 个警告")
        return 1 if self.errors else 0


def read_paragraphs(text: str) -> list[dict]:
    """从双语 Markdown 里读出每段的英文、中文、生词行。"""
    lines = text.split("\n")
    paragraphs: list[dict] = []
    i = 0
    while i < len(lines):
        match = PARA_RE.match(lines[i].strip())
        if not match:
            i += 1
            continue
        entry = {"num": int(match.group(1)), "en": "", "cn": "", "vocab": None}
        i += 1
        en_buf: list[str] = []
        while i < len(lines) and not lines[i].startswith("> ") and not lines[i].startswith(VOCAB_PREFIX):
            if lines[i].strip():
                en_buf.append(lines[i].strip())
            i += 1
        entry["en"] = " ".join(en_buf)
        if i < len(lines) and lines[i].startswith("> "):
            entry["cn"] = lines[i][2:].strip()
            i += 1
        while i < len(lines) and not lines[i].strip():  # 跳过译文与生词行之间的空行
            i += 1
        if i < len(lines) and lines[i].startswith(VOCAB_PREFIX):
            entry["vocab"] = lines[i][len(VOCAB_PREFIX):].strip()
            i += 1
        paragraphs.append(entry)
    return paragraphs


def check_structure(frontmatter: str, paragraphs: list[dict], report: Report) -> None:
    if "title:" not in frontmatter:
        report.warn("frontmatter 里没有 title")
    if not paragraphs:
        report.error("没有解析到任何 **N** 段落")
        return
    numbers = [p["num"] for p in paragraphs]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        report.error(f"段号不连续：共 {len(numbers)} 段，缺号 {missing[:10]}")
    for para in paragraphs:
        if not para["en"]:
            report.error(f"第 {para['num']} 段缺英文正文")
        if not para["cn"]:
            report.error(f"第 {para['num']} 段缺中文译文")
        elif not CJK_RE.search(para["cn"]):
            report.error(f"第 {para['num']} 段的中文译文里没有中文字符，可能没翻")
    report.info(f"段落数 {len(paragraphs)}，段号连续")


def check_vocab(paragraphs: list[dict], report: Report) -> None:
    total = 0
    with_vocab = 0
    for para in paragraphs:
        raw = para["vocab"]
        if not raw:
            continue
        with_vocab += 1
        entries = [e.strip() for e in raw.split(" · ") if e.strip()]
        for chunk in entries:
            total += 1
            match = ENTRY_RE.match(chunk)
            if not match:
                report.error(f"第 {para['num']} 段生词行格式不对：{chunk[:50]}")
                continue
            word = match.group("word").strip()
            ipa = match.group("ipa")
            pos = match.group("pos")
            meaning = match.group("meaning")
            if not ipa:
                report.warn(f"第 {para['num']} 段 {word} 没有音标")
            if pos and pos not in ALLOWED_POS:
                report.warn(f"第 {para['num']} 段 {word} 的词性 {pos!r} 不在约定集合里")
            if not CJK_RE.search(meaning):
                report.warn(f"第 {para['num']} 段 {word} 的释义不是中文：{meaning[:30]}")
            stem = word.lower().split()[0].strip("'’")
            body = para["en"].lower()
            if stem and stem[: max(4, len(stem) - 2)] not in body:
                report.warn(
                    f"第 {para['num']} 段生词 {word} 似乎没出现在该段英文里"
                    "（可能放错段，也可能是词形变化：写成文中的形式更好找）"
                )
    report.info(f"生词行 {with_vocab} 段 / {total} 条")


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", " ").replace("\u2013", " ")
    text = re.sub(r"\[\d{1,3}\]", " ", text)
    text = re.sub(r"(?<=[A-Za-z.])\d{1,2}(?!\d)", "", text)  # 上标脚注数字
    text = re.sub(r"[^A-Za-z0-9'.,?! ]", " ", text)
    return re.sub(r"\s+", " ", text).strip().split()


def source_words(pdf: Path) -> list[str]:
    try:
        import fitz
    except ImportError:
        sys.exit("比对源 PDF 需要 PyMuPDF：pip install pymupdf")
    doc = fitz.open(pdf)
    chunks: list[str] = []
    for page in doc:
        for line in page.get_text().split("\n"):
            stripped = line.strip()
            if re.fullmatch(r"[\divxlcdmIVXLCDM]{1,6}", stripped):
                continue  # 页码
            if re.match(r"^\d{1,2}\.\s+[A-Za-z]", stripped) or re.fullmatch(r"\d{1,2}\.", stripped):
                continue  # 原文脚注区，翻译时本来就不进正文
            chunks.append(stripped)
    doc.close()
    return normalize(" ".join(chunks))


def check_fidelity(paragraphs: list[dict], pdf: Path, report: Report, strict: bool) -> None:
    source = source_words(pdf)
    translated = normalize(" ".join(p["en"] for p in paragraphs))
    matcher = difflib.SequenceMatcher(None, source, translated, autojunk=False)
    missing: list[str] = []
    extra: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace") and i2 > i1:
            missing.append(" ".join(source[i1:i2]))
        if tag in ("insert", "replace") and j2 > j1:
            extra.append(" ".join(translated[j1:j2]))
    report.info(f"与源 PDF 词流比对：相似度 {matcher.ratio():.3f}（原文 {len(source)} 词 / 译文 {len(translated)} 词）")
    if missing:
        sample = " / ".join(m[:60] for m in missing[:6])
        message = f"源 PDF 里有、双语稿里没有的英文（前 {min(6, len(missing))} 处）：{sample}"
        (report.error if strict else report.warn)(message)
    if extra:
        sample = " / ".join(e[:60] for e in extra[:6])
        message = f"双语稿里多出来的英文（前 {min(6, len(extra))} 处）：{sample}"
        (report.error if strict else report.warn)(message)
    if not missing and not extra:
        report.info("英文与源 PDF 完全一致")


def check_pdf(pdf: Path, report: Report) -> None:
    try:
        import fitz
    except ImportError:
        sys.exit("检查 PDF 需要 PyMuPDF：pip install pymupdf")
    doc = fitz.open(pdf)
    text = "".join(page.get_text() for page in doc)
    fonts = set()
    for page in doc:
        for font in page.get_fonts():
            fonts.add(font[3])
    pages = len(doc)
    doc.close()

    report.info(f"PDF：{pages} 页 / 字体 {', '.join(sorted(fonts))}")
    for leaked in ("<span", "</strong>", "</em>", "&lt;", "&gt;", "&amp;"):
        if leaked in text:
            report.error(f"PDF 里漏出了 HTML 片段：{leaked}")
    if len(CJK_RE.findall(text)) < 50:
        report.error("PDF 里几乎读不到中文，字体可能没生效")
    if fonts and not any("+" in f for f in fonts):
        report.warn("字体看起来没有内嵌（子集名里通常带 +），换机器可能显示异常")


def main() -> int:
    parser = argparse.ArgumentParser(description="双语稿交付自检")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--source", type=Path, help="源英文 PDF，用于比对英文保真")
    parser.add_argument("--pdf", type=Path, help="生成的 PDF，用于成品检查")
    parser.add_argument("--strict", action="store_true", help="把英文差异也算成错误")
    args = parser.parse_args()

    raw = args.markdown.read_text(encoding="utf-8")
    frontmatter_match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", raw, re.S)
    frontmatter = frontmatter_match.group(1) if frontmatter_match else ""
    paragraphs = read_paragraphs(raw)

    report = Report()
    check_structure(frontmatter, paragraphs, report)
    check_vocab(paragraphs, report)
    if args.source:
        check_fidelity(paragraphs, args.source, report, args.strict)
    if args.pdf:
        check_pdf(args.pdf, report)
    return report.dump()


if __name__ == "__main__":
    sys.exit(main())
