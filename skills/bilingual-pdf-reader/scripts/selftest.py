#!/usr/bin/env python3
"""自测：只验证最容易回归的纯文本逻辑，不需要 PyMuPDF / weasyprint。

用法：
    python3 scripts/selftest.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from extract_pdf import (  # noqa: E402
    group_paragraphs,
    join_lines,
    line_pitch,
    merge_same_line,
    strip_markers,
)
from check_bilingual import read_paragraphs, Report, check_structure, check_vocab  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def line(text: str, top: float, bottom: float, x0: float = 72.0) -> dict:
    return {"x0": x0, "y0": top, "x1": 540.0, "y1": bottom, "bottom": bottom, "text": text}


def test_merge_same_line() -> None:
    print("同一视觉行的碎片合并（上标脚注会把行拆成两块）")
    raw = [
        line("He pushed the door, and", 70.0, 83.4),
        line("3", 68.0, 76.0, x0=300.0),  # 上标脚注，单独成块
        line("went in.", 84.0, 97.0),
    ]
    merged = merge_same_line(raw)
    check("行数 3 → 2", len(merged) == 2, f"实际 {len(merged)}")
    check("上标并回同一行", "3" in merged[0]["text"], merged[0]["text"])


def test_line_pitch_and_grouping() -> None:
    print("行距聚类与切段")
    # 真实页面：3 行一段 + 单行段 + 2 行一段，行距 13.6、段距 28.3
    page = [
        line("The dark sky reflected his mood as he sat", 70.0, 83.6),
        line("on the stoop of his building, thinking", 83.9, 97.5),
        line("about the lecture waiting for him.", 97.8, 111.4),
        line("His father had been a postal worker.", 139.7, 153.3),
        line("That had been two nights before. His", 181.6, 195.2),
        line("words still rumbled in his ears.", 195.5, 209.1),
    ]
    pitch, bimodal = line_pitch([page])
    check("行距估计 ≈13.6", abs(pitch - 13.6) < 0.6, f"实际 {pitch:.1f}")
    check("识别出双峰", bimodal)
    groups = group_paragraphs(page, 1.35, pitch, bimodal)
    check("切成 3 段", len(groups) == 3, f"实际 {len(groups)}")
    joined = join_lines(groups[0])
    check("段内换行拼成一行", "\n" not in joined and joined.endswith("him."), joined)

    # 退化页面：全是单行对话，行距与段距无法区分 → 靠句子收尾判断
    dialogue = [
        line("“Who are you?” Greg asked.", 100.0, 113.6),
        line("“Lemon Brown,” came the answer.", 128.3, 141.9),
        line("“Greg Ridley.”", 156.6, 170.2),
    ]
    pitch2, bimodal2 = line_pitch([dialogue])
    check("退化页面不认为是双峰", not bimodal2, f"pitch={pitch2:.1f}")
    groups = group_paragraphs(dialogue, 1.35, pitch2, bimodal2)
    check("三句对话仍是三段", len(groups) == 3, f"实际 {len(groups)}")


def test_join_hyphen() -> None:
    print("行尾连字符断词要接回去")
    paragraph = [line("graffiti-scar-", 100.0, 113.6), line("red building", 113.9, 127.5)]
    check("连字符被吃掉", join_lines(paragraph) == "graffiti-scarred building", join_lines(paragraph))


def test_strip_markers() -> None:
    print("角标与粘在词尾的脚注数字")
    text = "an old tenement1 that had been [5] abandoned for months, gnarled9 fist"
    out = strip_markers(text, {"1", "9"})
    check("[5] 被删", "[5]" not in out)
    check("tenement1 → tenement", "tenement1" not in out)
    check("gnarled9 → gnarled", "gnarled9" not in out)
    check("正常数字不受影响", strip_markers("in 1983 he left", {"1"}) == "in 1983 he left")


def test_insert_vocab() -> None:
    print("生词插入：幂等 + clear")
    with tempfile.TemporaryDirectory() as tmp:
        md = Path(tmp) / "t.md"
        vocab = Path(tmp) / "v.json"
        md.write_text(
            "---\ntitle: 测试\n---\n\n## 正文\n\n**1**\n\nThe old tenement was empty.\n\n> 那栋老楼空着。\n\n**2**\n\nHe went in.\n\n> 他进去了。\n",
            encoding="utf-8",
        )
        vocab.write_text(
            json.dumps({"1": [["tenement", "/ˈtenəmənt/", "n.", "廉租公寓楼"]]}), encoding="utf-8"
        )
        script = HERE / "insert_vocab.py"
        for _ in range(3):
            subprocess.run([sys.executable, str(script), str(md), str(vocab)], check=True, capture_output=True)
        text = md.read_text(encoding="utf-8")
        check("重复运行只留一行", text.count("生词：") == 1, f"实际 {text.count('生词：')}")
        check("生词行在译文下面", "> 那栋老楼空着。\n\n生词：**tenement**" in text, repr(text[-80:]))

        subprocess.run([sys.executable, str(script), str(md), "--clear"], check=True, capture_output=True)
        check("--clear 清干净", "生词：" not in md.read_text(encoding="utf-8"))


def test_check_bilingual() -> None:
    print("自检脚本：好稿 0 错，坏稿报错")
    good = (
        "---\ntitle: 测试\n---\n\n## 正文\n\n**1**\n\nThe old tenement was empty.\n\n"
        "> 那栋老楼空着。\n\n生词：**tenement** /ˈtenəmənt/ *n.* 廉租公寓楼\n"
    )
    report = Report()
    paragraphs = read_paragraphs(good)
    check_structure("title: 测试", paragraphs, report)
    check_vocab(paragraphs, report)
    check("正常稿无错误", not report.errors, str(report.errors))

    bad = "## 正文\n\n**1**\n\nThe old tenement was empty.\n\n> 那栋老楼空着。\n\n**3**\n\nHe went in.\n\n生词：**tenement** tenement /ˈtenəmənt/ *n.* 廉租公寓楼\n"
    report = Report()
    paragraphs = read_paragraphs(bad)
    check_structure("", paragraphs, report)
    check_vocab(paragraphs, report)
    check("缺中文 / 段号跳号会被报出来", len(report.errors) >= 2, str(report.errors))


def main() -> int:
    for test in (
        test_merge_same_line,
        test_line_pitch_and_grouping,
        test_join_hyphen,
        test_strip_markers,
        test_insert_vocab,
        test_check_bilingual,
    ):
        test()
    print()
    if FAILURES:
        print(f"失败 {len(FAILURES)} 项：{', '.join(FAILURES)}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
