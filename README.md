# nice-skills

我日常在用的 agent skills 集合。每个 skill 是一个独立目录，遵循 [Agent Skills 规范](https://agentskills.io/specification)，可以被 Claude Code、Codex、Cursor、DSH 等支持 skills 的 agent 直接加载。

## 包含的 skills

| Skill | 作用 | 触发示例 |
| --- | --- | --- |
| [`get-it-done`](./skills/get-it-done/SKILL.md) | 把交办的事情真正落地：实施、本地验证、提交、开 PR，并盯 GitHub Actions 到全绿 | 「把这个事情搞定」「搞定开发」「落地这个项目 / 计划」「ship it」「get it done」 |
| [`write-article`](./skills/write-article/SKILL.md) | 写客观朴素的科普 / 描述性文章；说「写微信公众号」时按图文并茂产出配图 | 「写篇文章」「写篇科普」「写个介绍」「写一篇微信公众号文章」 |
| [`bilingual-pdf-reader`](./skills/bilingual-pdf-reader/SKILL.md) | 把英文 PDF 做成逐段中英对照的精读稿：译文 + 每段生词（音标、词性、释义），产出 Markdown 与 A4 PDF | 「把这篇文章翻译成中英对照」「英文 PDF 转成中英文」「加生词和音标」 |

## 安装

使用 [skills CLI](https://github.com/vercel-labs/skills)（`npx skills`）：

```bash
# 安装本仓库的全部 skills
npx skills add everettjf/nice-skills

# 只装某一个
npx skills add everettjf/nice-skills --skill get-it-done
npx skills add everettjf/nice-skills --skill write-article
npx skills add everettjf/nice-skills --skill bilingual-pdf-reader

# 安装到用户级目录（所有项目可用），跳过确认
npx skills add everettjf/nice-skills -g -y

# 只看有哪些 skills，不安装
npx skills add everettjf/nice-skills --list
```

在 Claude Code 里也可以作为插件市场安装：

```
/plugin marketplace add everettjf/nice-skills
/plugin install nice-skills@nice-skills
```

手动安装：把需要的目录复制到 agent 的 skills 目录即可，常见位置是 `~/.claude/skills/`、`~/.agents/skills/`，或项目内的 `.claude/skills/`。目录结构必须保持 `<skill-name>/SKILL.md`。

## 更新

```bash
npx skills list                  # 查看已安装的 skills 和来源
npx skills update                # 更新全部（交互选择项目级 / 全局）
npx skills update get-it-done    # 只更新某一个
npx skills update -g             # 只更新全局安装的
npx skills update -p             # 只更新项目级安装的
npx skills update -y             # 非交互
```

更新完成后要**新开一轮会话**，agent 才会重新读取 skill 文件；正在进行的会话里用的还是旧内容。

几点说明：

- `skills-lock.json` 只记录来源和内容哈希，**不锁版本**，所以 `update` 拉的是本仓库默认分支的最新内容。
- 用本地路径安装的（`npx skills add ./some-dir`）**不会**被 `update` 更新，需要重新 `add`。
- 项目级安装时 `.agents/skills/<name>/` 才是真正的副本，`.claude/skills/` 等 agent 目录是指向它的符号链接，所以更新一次对所有 agent 生效。

### 固定版本

默认跟随默认分支。想固定在某个版本，按 tag 安装：

```bash
npx skills add https://github.com/everettjf/nice-skills/tree/v0.1.0/skills/get-it-done
```

这样 `skills-lock.json` 里会多一个 `"ref": "v0.1.0"`，之后 `update` 不会把它带到新版本。

版本变更记录见 [CHANGELOG.md](./CHANGELOG.md)。

## 目录结构

```
nice-skills/
├── skills/
│   ├── get-it-done/
│   │   ├── SKILL.md                 # 主流程与红线
│   │   └── references/
│   │       └── github-pr.md         # PR、CI 排障、冲突处理命令
│   ├── write-article/
│   │   ├── SKILL.md                 # 写作流程与风格底线
│   │   ├── references/
│   │   │   ├── style-guide.md       # 词表、改写对照、来源规范
│   │   │   └── wechat.md            # 公众号图文流程与配图
│   │   └── assets/
│   │       ├── article-template.md
│   │       └── figure-plan-template.md
│   └── bilingual-pdf-reader/
│       ├── SKILL.md                 # 双语精读稿流程与红线
│       ├── references/
│       │   ├── translation-style.md # 翻译规范：忠实度、口语层次、译注
│       │   └── vocab-guide.md       # 生词规范：收词阈值、格式、音标
│       ├── assets/
│       │   └── bilingual-template.md
│       └── scripts/
│           ├── extract_pdf.py       # PDF → 编号段落 Markdown
│           ├── insert_vocab.py      # 生词表 JSON → 按段插入生词行
│           ├── render_pdf.py        # 双语 Markdown → A4 PDF
│           ├── check_bilingual.py   # 交付自检：结构 / 生词 / 英文保真 / PDF
│           └── selftest.py          # 纯文本逻辑自测（CI 也会跑）
├── .claude-plugin/marketplace.json  # Claude Code 插件清单
├── .github/workflows/
│   └── validate-skills.yml          # 每次 PR 校验 skill 格式
├── scripts/
│   └── validate_skills.py           # 校验 SKILL.md 元数据、链接与代码围栏
├── CHANGELOG.md                     # 版本变更记录
├── LICENSE
└── README.md
```

## 关于这三个 skill

### get-it-done

触发后不会只给你建议，而是把事做完：

1. 明确目标、范围和验收标准；
2. 读项目自己的约定（`AGENTS.md`、`CONTRIBUTING.md`、CI 配置、PR 模板、提交规范）；
3. 实施最小而完整的改动；
4. 跑项目自己的门禁命令，修到通过；
5. 建分支、提交、推送、开 Pull Request；
6. 用 `gh pr checks --watch` 盯 GitHub Actions，失败就定位、修复、重推，循环到全绿；
7. 按固定格式汇报结果和遗留问题。

红线写得很明确：不直推默认分支、不绕 CI、不 force push 共享分支、不提交密钥、CI 没绿不宣称搞定。

### write-article

风格约束是三条：**客观、朴素、科普 / 描述**。

- 事实、观点、推测分开写，数据必须有来源和环境说明；
- 严禁营销腔、空话开头结尾、无信息量的程度副词、编造引用；
- 写作前先建「事实底稿」，写完按清单自检；
- 说「写微信公众号」时额外产出配图清单，能用 Mermaid / SVG / matplotlib / 截图生成的图直接生成，生成不了的给中英双语提示词和占位，并附封面方案与排版细则。

### bilingual-pdf-reader

丢一个英文 PDF 进去，拿一份「一段英文、一段中文、下面带生词」的精读稿出来。

- **逐段对照**：一段英文对一段中文，不合并、不拆分，左边看一句右边就能找到；对话仍是一句一段。
- **生词带发音**：译文下面一行 `生词：**word** /ipa/ *n.* 释义 · …`，收录原文脚注词、词组习语、语境生僻义，每段 0–4 条。
- **口语不洗白**：方言、市井人物、黑人英语（AAVE）译出对应的口语层次，而不是变成标准书面语。
- **两个交付物**：可继续编辑的 Markdown，加一份封面独立、页脚带页码、中文字体内嵌的 A4 PDF。
- **带工具链**：`extract_pdf.py`（双栏 / 页眉页脚 / 脚注清洗）、`insert_vocab.py`（幂等插入生词行）、`render_pdf.py`（排版）、`check_bilingual.py`（段号、生词格式、与源 PDF 的英文词流比对、PDF 成品检查）。
- 版权红线写在 SKILL.md 里：受版权保护的全文只供个人学习，要公开发布时改成「导读 + 有限引文 + 解读」。

## 自己加一个 skill

1. 新建 `skills/<skill-name>/SKILL.md`，`name` 用小写字母、数字和短横线，`description` 写清「做什么」和「什么时候用」。
2. 内容太长就拆到 `references/`，输出模板放 `assets/`，脚本放该 skill 目录下的 `scripts/`，并在 `SKILL.md` 里用相对路径引用。
3. 需要 Claude Code 插件安装时，把新目录加进 `.claude-plugin/marketplace.json` 的 `skills` 列表。
4. 本地跑一遍校验：`python3 scripts/validate_skills.py`。提 PR 后 CI 会跑同一个脚本。

## License

[MIT](./LICENSE)
