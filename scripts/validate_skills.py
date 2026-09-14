#!/usr/bin/env python3
"""校验 skills/ 下每个 skill 的结构和 SKILL.md 元数据。

只依赖标准库。在 GitHub Actions 里会输出 ::error / ::warning 注解，本地运行输出普通文本。

用法：
    python3 scripts/validate_skills.py [--root <仓库根目录>]

退出码：有错误时为 1，只有警告或全部通过时为 0。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
FENCE_RE = re.compile(r"^(\s*)(`{3,})(.*)$")
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.S)
# 匹配非图片、非外链、非锚点的 Markdown 链接
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\((?!https?://|mailto:|#)([^)\s]+)")

MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024

IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"


def report(level: str, path: Path | None, message: str) -> None:
    if IN_CI and path is not None:
        print(f"::{level} file={path.as_posix()}::{message}")
    elif path is not None:
        print(f"[{level.upper()}] {path}: {message}")
    else:
        print(f"[{level.upper()}] {message}")


def strip_fenced_blocks(text: str) -> str:
    """去掉围栏代码块，避免把示例代码里的链接/围栏当成真实内容。"""
    return FENCED_BLOCK_RE.sub("", text)


def check_fences(path: Path, text: str) -> list[str]:
    """检查代码围栏是否配平，以及有没有在围栏内又开一个不同长度的围栏。"""
    problems: list[str] = []
    depth = 0
    opener: tuple[int, str] | None = None

    for lineno, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if not match:
            continue
        _, ticks, info = match.groups()

        if depth == 0:
            depth = len(ticks)
            opener = (lineno, ticks)
            continue

        if len(ticks) >= depth and not info.strip():
            depth = 0
            opener = None
        else:
            assert opener is not None
            problems.append(
                f"第 {lineno} 行的代码围栏未正确闭合（外层围栏从第 {opener[0]} 行开始）"
            )

    if depth != 0 and opener is not None:
        problems.append(f"第 {opener[0]} 行开始的代码围栏没有闭合")

    return problems


def parse_frontmatter(path: Path, text: str) -> tuple[dict[str, str], list[str]]:
    problems: list[str] = []
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, ["缺少 YAML frontmatter（文件必须以 --- 开头，并以 --- 结束）"]

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t", "-")):
            continue  # 嵌套结构，本校验不解析
        if ":" not in line:
            problems.append(f"frontmatter 不是 key: value 形式：{line!r}")
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()

    return fields, problems


def check_skill(skill_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.name}/ 下缺少 SKILL.md"], []

    text = skill_md.read_text(encoding="utf-8")
    fields, fm_problems = parse_frontmatter(skill_md, text)
    errors.extend(fm_problems)

    name = fields.get("name", "")
    if not name:
        errors.append("frontmatter 缺少 name")
    else:
        if name != skill_dir.name:
            errors.append(f"name「{name}」与目录名「{skill_dir.name}」不一致")
        if not NAME_RE.match(name):
            errors.append(f"name「{name}」不合规：只能用小写字母、数字和短横线，且不能以短横线开头或结尾")
        if len(name) > MAX_NAME_LEN:
            errors.append(f"name 长度 {len(name)} 超过 {MAX_NAME_LEN}")

    description = fields.get("description", "")
    if not description:
        errors.append("frontmatter 缺少 description")
    elif len(description) > MAX_DESCRIPTION_LEN:
        errors.append(f"description 长度 {len(description)} 超过 {MAX_DESCRIPTION_LEN}")

    errors.extend(check_fences(skill_md, text))

    # 相对链接必须存在（忽略代码块内的示例）
    body = strip_fenced_blocks(text)
    for target in LINK_RE.findall(body):
        relative = target.split("#", 1)[0]
        if not relative:
            continue
        if not (skill_md.parent / relative).resolve().exists():
            errors.append(f"SKILL.md 里的相对链接不存在：{target}")

    # 附加文件应当能从 SKILL.md 抵达（渐进披露）
    for extra in sorted(skill_dir.rglob("*")):
        if not extra.is_file() or extra.name == "SKILL.md":
            continue
        relative = extra.relative_to(skill_dir).as_posix()
        if relative not in text and extra.name not in text:
            warnings.append(f"{relative} 没有被 SKILL.md 引用")

    return errors, warnings


def check_marketplace(root: Path) -> list[str]:
    manifest = root / ".claude-plugin" / "marketplace.json"
    if not manifest.exists():
        return []

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f".claude-plugin/marketplace.json 不是合法 JSON：{exc}"]

    problems: list[str] = []
    for plugin in data.get("plugins", []):
        for entry in plugin.get("skills", []):
            if not (root / entry).is_dir():
                problems.append(f"marketplace.json 里的 skills 路径不存在：{entry}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 skills/ 下的 skill 结构")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="仓库根目录，默认取本脚本的上一级",
    )
    args = parser.parse_args()
    root: Path = args.root.resolve()

    skills_root = root / "skills"
    if not skills_root.is_dir():
        report("error", skills_root, "找不到 skills/ 目录")
        return 1

    total_errors = 0
    total_warnings = 0
    skill_dirs = sorted(d for d in skills_root.iterdir() if d.is_dir())

    if not skill_dirs:
        report("error", skills_root, "skills/ 下没有任何 skill")
        return 1

    for skill_dir in skill_dirs:
        errors, warnings = check_skill(skill_dir)
        for message in errors:
            report("error", skill_dir / "SKILL.md", message)
        for message in warnings:
            report("warning", skill_dir, message)
        total_errors += len(errors)
        total_warnings += len(warnings)
        status = "OK" if not errors else "FAIL"
        print(f"  {status}  {skill_dir.relative_to(root).as_posix()}")

    for message in check_marketplace(root):
        report("error", root / ".claude-plugin" / "marketplace.json", message)
        total_errors += 1

    print()
    print(f"共校验 {len(skill_dirs)} 个 skill：{total_errors} 个错误，{total_warnings} 个警告")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
