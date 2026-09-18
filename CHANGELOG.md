# Changelog

本仓库的版本变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- `bilingual-pdf-reader`：英文 PDF → 逐段中英对照精读稿（Markdown + A4 PDF），译文下方带「生词」行（词条 + 美式音标 + 词性 + 中文释义）。含五个脚本：
  - `scripts/extract_pdf.py`：PDF → 编号段落 Markdown；处理双栏重排、跨页页眉页脚、页码、`[12]` 角标与粘在词尾的脚注数字（`gnarled9` → `gnarled`），并把原书脚注收集到文末；行距聚类用「全文级行距 + 同一视觉行合并」，避免对话密集页被判成一段。
  - `scripts/insert_vocab.py`：生词表 JSON 按段插入生词行，幂等（重复运行不重复插入），支持 `--clear`。
  - `scripts/render_pdf.py`：双语 Markdown → A4 PDF，封面独立成页、中文段落细线标记、生词行、译注列表、页脚页码，中文字体按 `Songti SC → Noto Serif CJK SC → Source Han Serif` 回退。
  - `scripts/check_bilingual.py`：交付自检——段号连续性、每段中英齐全、生词行格式与词性取值、生词是否真的出现在该段、与源 PDF 的英文词流比对（漏译 / 多译）、PDF 页数与 HTML 标签泄漏、字体内嵌。
  - `scripts/selftest.py`：不依赖 PyMuPDF / WeasyPrint 的自测，覆盖最容易回归的纯文本逻辑（同一视觉行合并、行距聚类与切段、行尾连字符、脚注数字剥离、生词插入幂等、自检脚本的报错行为）。
- `bilingual-pdf-reader` 的 `references/translation-style.md`（翻译与口语层次规范、难点处理、译注写法）、`references/vocab-guide.md`（收词阈值、格式、音标约定）、`assets/bilingual-template.md`（双语稿骨架）。
- CI：`validate-skills.yml` 增加一步跑 `bilingual-pdf-reader` 的 `selftest.py`（纯标准库，无需额外依赖）。
- README 增加该 skill 的表格行、目录结构与说明；`.claude-plugin/marketplace.json` 的 `skills` 列表加入 `./skills/bilingual-pdf-reader`，描述改为三个 skill，版本号 0.2.0。

### 变更

- `get-it-done` 与 `write-article` 的 `description` 补充触发词：「搞定开发」「落地这个项目 / 计划 / 方案」「把这个需求做出来 / 实现」「写一篇微信公众号文章」「公众号推文」等；README 表格的「触发示例」同步更新。
- 新增 `AGENTS.md`：本仓库自己的 agent 约定（改 skill 要同步 `description` 触发词、跑校验、同步 marketplace.json / README / CHANGELOG、新增 skill 流程等）。

## [0.1.2] - 2026-09-14

### 变更

- `write-article` 明确链接的写法：文章里的链接统一写成 `标题 : URL`（英文冒号，前后各一个空格），并新增 `references/style-guide.md` 的「链接的写法」一节。同步更新了 `SKILL.md` 的写作规则与交付要求、`references/wechat.md` 的排版细则与检查清单，以及 `assets/article-template.md` 的参考来源骨架。这条规则只管文章产出，skill 内部文件之间的相对链接不受影响。

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

[Unreleased]: https://github.com/everettjf/nice-skills/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/everettjf/nice-skills/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/everettjf/nice-skills/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/everettjf/nice-skills/releases/tag/v0.1.0
