#!/usr/bin/env python3
"""把生词表按段落号插进双语 Markdown，每段译文下方一行「生词：」。

用法：
    python3 insert_vocab.py bilingual.md vocab.json [--clear] [--dry-run]

vocab.json 两种写法都支持：

    {"1": [["stoop", "/stuːp/", "n.", "（美）楼门前的台阶"]],
     "3": [{"word": "suspense", "ipa": "/səˈspens/", "pos": "n.", "meaning": "悬念"}]}

生成的 Markdown 行：

    生词：**stoop** /stuːp/ *n.* （美）楼门前的台阶 · **suspense** /səˈspens/ *n.* 悬念

幂等：同一段重复运行只会保留一行最新的生词行。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PARA_RE = re.compile(r"^\*\*(\d+)\*\*$")
VOCAB_PREFIX = "生词："
SEP = " · "
ALLOWED_POS = {
    "n.", "v.", "vt.", "vi.", "adj.", "adv.", "prep.", "conj.", "pron.",
    "num.", "art.", "int.", "aux.", "abbr.", "词组", "习语", "俚语", "专名",
}


def load_vocab(path: Path) -> dict[int, list[tuple[str, str, str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    vocab: dict[int, list[tuple[str, str, str, str]]] = {}
    for key, items in data.items():
        para = int(key)
        entries = []
        for item in items:
            if isinstance(item, dict):
                entries.append(
                    (
                        str(item["word"]).strip(),
                        str(item.get("ipa", "")).strip(),
                        str(item.get("pos", "")).strip(),
                        str(item.get("meaning", "")).strip(),
                    )
                )
            else:
                word, ipa, pos, meaning = (list(item) + ["", "", "", ""])[:4]
                entries.append((str(word).strip(), str(ipa).strip(), str(pos).strip(), str(meaning).strip()))
        vocab[para] = entries
    return vocab


def format_line(entries: list[tuple[str, str, str, str]]) -> str:
    parts = []
    for word, ipa, pos, meaning in entries:
        chunk = f"**{word}**"
        if ipa:
            chunk += f" {ipa}"
        if pos:
            chunk += f" *{pos}*"
        if meaning:
            chunk += f" {meaning}"
        parts.append(chunk)
    return VOCAB_PREFIX + SEP.join(parts)


def validate(entries: list[tuple[str, str, str, str]], para: int, problems: list[str]) -> None:
    for word, ipa, pos, meaning in entries:
        if not word or not meaning:
            problems.append(f"第 {para} 段：词条或释义为空（{word!r}）")
        if ipa and not (ipa.startswith("/") and ipa.endswith("/")):
            problems.append(f"第 {para} 段：{word} 的音标要用斜杠包住，当前是 {ipa!r}")
        if pos and pos not in ALLOWED_POS:
            problems.append(f"第 {para} 段：{word} 的词性 {pos!r} 不在约定集合里（{sorted(ALLOWED_POS)}）")


def apply_vocab(lines: list[str], vocab, clear: bool) -> tuple[list[str], int]:
    """按段落块重写：删掉块内旧的生词行，再把新行插到中文译文正下方。"""
    starts = [idx for idx, line in enumerate(lines) if PARA_RE.match(line.strip())]
    if not starts:
        return lines, 0
    boundaries = starts + [len(lines)]
    out: list[str] = lines[: starts[0]]
    inserted = 0

    for k, start in enumerate(starts):
        block = [l for l in lines[start : boundaries[k + 1]] if not l.startswith(VOCAB_PREFIX)]
        para = int(PARA_RE.match(lines[start].strip()).group(1))  # type: ignore[union-attr]
        entries = vocab.get(para, [])
        cn_idx = max((idx for idx, l in enumerate(block) if l.startswith("> ")), default=None)
        if entries and not clear and cn_idx is not None:
            tail = block[cn_idx + 1 :]
            while tail and not tail[0].strip():
                tail.pop(0)
            block = block[: cn_idx + 1] + ["", format_line(entries)]
            block += ([""] + tail) if tail else [""]
            inserted += 1
        out.extend(block)

    while len(out) > 1 and not out[-1].strip() and not out[-2].strip():
        out.pop()
    return out, inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="把生词行插进双语 Markdown")
    parser.add_argument("markdown", type=Path)
    parser.add_argument("vocab", type=Path, nargs="?", help="生词表 JSON；配合 --clear 时可省略")
    parser.add_argument("--clear", action="store_true", help="删掉所有生词行")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写回文件")
    args = parser.parse_args()

    if not args.vocab and not args.clear:
        sys.exit("需要给出 vocab.json，或使用 --clear 删除生词行")

    vocab = load_vocab(args.vocab) if args.vocab else {}
    problems: list[str] = []
    for para, entries in vocab.items():
        validate(entries, para, problems)
    if problems:
        print("生词表有问题：")
        for problem in problems:
            print("  -", problem)
        return 1

    text = args.markdown.read_text(encoding="utf-8")
    lines = text.split("\n")
    result, inserted = apply_vocab(lines, vocab, args.clear)
    new_text = "\n".join(result)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)

    existing = sum(1 for l in lines if l.startswith(VOCAB_PREFIX))
    total = sum(len(v) for v in vocab.values())
    print(f"生词行：{existing} → {new_text.count(VOCAB_PREFIX)}（本次写入 {inserted} 段 / {total} 条）")
    if not args.dry_run:
        args.markdown.write_text(new_text, encoding="utf-8")
        print(f"已写回 {args.markdown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
