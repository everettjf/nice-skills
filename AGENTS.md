# AGENTS.md

本仓库是 `everettjf/nice-skills`：一套遵循 [Agent Skills 规范](https://agentskills.io/specification) 的 skills 集合。每个 skill 是一个 `skills/<skill-name>/SKILL.md`，可被 Claude Code、Codex、Cursor、DSH 等 agent 加载。

在这个仓库里改东西，遵守下面几条。

## 核心认知

- skill 的**目录名 = frontmatter 的 `name`**，两者必须一致。
- **`description` 是触发字段**：agent 靠它决定要不要调用这个 skill，不是靠 `name`。改 skill 时触发词要写得具体、口语化，把用户可能说的话都列进去（例：「搞定开发」「落地这个项目 / 计划」「写一篇微信公众号文章」），宁可多列几条。
- 硬限制：`name` 只能用小写字母、数字、短横线，≤64 字符；`description` ≤1024 字符。这些由 `scripts/validate_skills.py` 强制检查。

## 改 skill 的规矩

1. 改 `SKILL.md` 时同步维护触发词：改了能力或范围，就同步改 frontmatter 的 `description`，并和 README 表格里的「触发示例」保持一致。
2. **渐进披露**：内容长了拆到 `references/`，输出模板放 `assets/`，脚本放该 skill 自己的 `scripts/`。这些文件都必须能被 `SKILL.md` 用相对路径或文件名引用到，否则校验会报 warning。
3. `SKILL.md` 里的相对链接必须真实存在（校验会检查可达性）。
4. 改完必须跑校验，全绿再提交：
   ```bash
   python3 scripts/validate_skills.py
   ```
   改 `bilingual-pdf-reader` 的脚本时，额外跑它的自测：
   ```bash
   python3 skills/bilingual-pdf-reader/scripts/selftest.py
   ```

## 同步更新的地方

改完 skill（尤其是新增/删除 skill、改触发词、改交付物）后，检查并同步这三处：

- [ ] `.claude-plugin/marketplace.json`：`plugins[].skills` 列表、plugin `description`、`metadata.version`（新增 skill 时升一位）
- [ ] `README.md`：「包含的 skills」表格、「目录结构」、skill 说明章节
- [ ] `CHANGELOG.md`：在 `[Unreleased]` 下按 `新增` / `变更` 记一条，遵循 Keep a Changelog + semver

## 新增一个 skill

1. 新建 `skills/<skill-name>/SKILL.md`，`name` 与目录名一致，`description` 写清「做什么 + 什么时候用」。
2. 需要的内容按 `references/` / `assets/` / `scripts/` 拆分，并在 `SKILL.md` 里引用。
3. 加进 `.claude-plugin/marketplace.json` 的 `skills` 列表，`metadata.version` 升一位。
4. 更新 README 与 CHANGELOG。
5. 跑 `python3 scripts/validate_skills.py` 到全绿。

## 提交与 CI

- 提交信息用 Conventional Commits，中文描述，例如 `feat: 新增 xxx`、`docs: 明确 xxx`；PR 合并后带 `(#N)` 后缀。
- 改动以 Pull Request 交付，不直接推 `main`。
- CI：push 到 `main` 和每个 PR 都会跑 `.github/workflows/validate-skills.yml`（即上面的校验脚本 + `bilingual-pdf-reader` 自测）。
- 不提交 `.DS_Store`、`*.log`、`node_modules/`、`__pycache__/`、IDE 配置等（已在 `.gitignore`）。

## 常用命令

```bash
python3 scripts/validate_skills.py                              # 校验全部 skill
python3 skills/bilingual-pdf-reader/scripts/selftest.py         # 双语脚本自测
```
