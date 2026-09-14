# Changelog

本仓库的版本变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.1] - 2026-09-14

### 新增

- README 的「更新」章节：`npx skills update` 的用法、按 tag 固定版本，以及本地路径来源不会被更新的说明。
- `scripts/validate_skills.py`：校验每个 skill 的 frontmatter（`name` 与目录一致、`description` 长度）、相对链接可达性、代码围栏配平，以及 `marketplace.json` 里的 skills 路径。
- `.github/workflows/validate-skills.yml`：push 到 `main` 和每个 Pull Request 都会跑上面的校验。
- 本文件。

### 变更

- `.claude-plugin/marketplace.json` 的版本号更新为 `0.1.1`。

## [0.1.0] - 2026-09-14

### 新增

- `get-it-done`：把交办的事情落地成可交付、可验证的成果；涉及 GitHub 仓库时保证 GitHub Actions 全部通过，并默认以 Pull Request 交付。
- `write-article`：写客观朴素的科普 / 描述性文章；说「写微信公众号」时按图文并茂产出配图清单、能生成的图与 AI 配图提示词。
- `README.md`、`.claude-plugin/marketplace.json`、`.gitignore`。

[Unreleased]: https://github.com/everettjf/nice-skills/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/everettjf/nice-skills/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/everettjf/nice-skills/releases/tag/v0.1.0
