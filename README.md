# nice-skills

我日常在用的 agent skills 集合。每个 skill 是一个独立目录，遵循 [Agent Skills 规范](https://agentskills.io/specification)，可以被 Claude Code、Codex、Cursor、DSH 等支持 skills 的 agent 直接加载。

## 包含的 skills

| Skill | 作用 | 触发示例 |
| --- | --- | --- |
| [`get-it-done`](./skills/get-it-done/SKILL.md) | 把交办的事情真正落地：实施、本地验证、提交、开 PR，并盯 GitHub Actions 到全绿 | 「把这个事情搞定」「搞定它」「把这件事落地」「ship it」 |
| [`write-article`](./skills/write-article/SKILL.md) | 写客观朴素的科普 / 描述性文章；说「写微信公众号」时按图文并茂产出配图 | 「写篇文章」「写篇科普」「写个介绍」「写微信公众号」 |

## 安装

使用 [skills CLI](https://github.com/vercel-labs/skills)（`npx skills`）：

```bash
# 安装本仓库的全部 skills
npx skills add everettjf/nice-skills

# 只装某一个
npx skills add everettjf/nice-skills --skill get-it-done
npx skills add everettjf/nice-skills --skill write-article

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

## 目录结构

```
nice-skills/
├── skills/
│   ├── get-it-done/
│   │   ├── SKILL.md                 # 主流程与红线
│   │   └── references/
│   │       └── github-pr.md         # PR、CI 排障、冲突处理命令
│   └── write-article/
│       ├── SKILL.md                 # 写作流程与风格底线
│       ├── references/
│       │   ├── style-guide.md       # 词表、改写对照、来源规范
│       │   └── wechat.md            # 公众号图文流程与配图
│       └── assets/
│           ├── article-template.md
│           └── figure-plan-template.md
├── .claude-plugin/marketplace.json  # Claude Code 插件清单
├── LICENSE
└── README.md
```

## 关于这两个 skill

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

## 自己加一个 skill

1. 新建 `skills/<skill-name>/SKILL.md`，`name` 用小写字母、数字和短横线，`description` 写清「做什么」和「什么时候用」。
2. 内容太长就拆到 `references/`，输出模板放 `assets/`，脚本放 `scripts/`，并在 `SKILL.md` 里用相对路径引用。
3. 需要 Claude Code 插件安装时，把新目录加进 `.claude-plugin/marketplace.json` 的 `skills` 列表。

## License

[MIT](./LICENSE)
