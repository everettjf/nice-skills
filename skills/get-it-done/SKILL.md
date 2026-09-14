---
name: get-it-done
description: 把交办的事情真正落地成可交付、可验证的成果。当用户说「把这个事情搞定」「搞定它」「把这件事落地」「帮我做完」「做完收尾」「ship it」「get it done」「make it happen」「别问了直接做」，或要求把某个方案、需求、修复直接实施完成时使用。只要任务涉及 GitHub 仓库，就必须让 GitHub Actions 全部通过，并默认以 Pull Request 的形式交付（项目另有明确规定时遵从其规定）。
license: MIT
---

# 把事搞定（Get It Done）

「搞定」= **交付**。用户说这句话时，他要的是已经完成、可以验收的结果，不是"你可以这样做"的建议，也不是做了一半的草稿。

判断标准只有一条：**用户看完你的回复，还需要自己动手做什么吗？** 如果需要，就没有搞定。

## 不可退让的底线

1. **落地优先于讨论**。方案已经清楚就直接做；只有真正影响方向的歧义才值得先问。
2. **真实验证，不猜**。跑过、看过输出，才能说"通过"；没跑过就明说没跑过。
3. **GitHub 项目必须 CI 全绿**。Actions 没全绿就不算搞定。
4. **默认交付 Pull Request**。除非项目或用户有明确的其他要求（要求直接提交、要求先开 issue、要求用指定分支等）。
5. **不越权**。见文末「红线」。

## 流程

### 0. 明确「事情」是什么

动手前先在心里回答三个问题：

- **目标**：要达成什么可观察的结果？
- **范围**：动哪些文件/模块？明确不改什么？
- **验收**：怎么证明它成了？测试、命令、可访问的产物，还是 CI 状态？

能从上下文和仓库推断出来的，不要问。只有下面几种情况才值得停下来问用户：

- 存在两个以上都合理的实现方向，且选错代价很大；
- 涉及不可逆操作：删数据、改线上、花钱、对外发布；
- 缺少只有用户能提供的凭据、账号或业务判断。

要问就一次问完，不要挤牙膏。

### 1. 勘察项目约定

动手前先读项目自己的规矩，优先级从高到低：

- agent 约定：`AGENTS.md`、`CLAUDE.md`、`.cursor/rules` 等
- 开发文档：`CONTRIBUTING.md`、`DEVELOPMENT.md`、`docs/` 下的说明
- `README.md` 里的「开发 / 测试 / 贡献」章节
- CI 配置：`.github/workflows/*.yml`
- 任务入口：`Makefile`、`justfile`、`package.json` 的 `scripts`、`pyproject.toml`、`Cargo.toml`、`Package.swift`
- PR 模板：`.github/PULL_REQUEST_TEMPLATE.md`、`.github/PULL_REQUEST_TEMPLATE/`
- 提交与分支规范：`.commitlintrc*`、`commitlint.config.*`、`.gitmessage`，以及 `git log` 的实际风格

**项目规定 > 本文档的默认值。** 项目要求写 changelog、要求签名、要求 squash，就照做。

### 2. 判断是不是 GitHub 项目

```bash
git remote -v                      # remote 里有没有 github.com
ls .github/workflows 2>/dev/null   # 有没有 Actions
```

- **是 GitHub** → 走第 5、6、7 步的交付流程（命令与排障见 [references/github-pr.md](references/github-pr.md)）。
- **不是 GitHub** → 跳过开 PR，但「可交付 + 可验证」的要求不变：本地验证、提交到分支，最后说清产物和验证方式。
- **是 GitLab / 其他平台** → 有 `glab` 等对应 CLI 就用它开 MR；没有就推分支，并把开 MR 的链接和步骤给用户。

### 3. 实施

- **最小而完整的改动**：只做这件事需要的改动。不顺手重构、不顺手升级依赖、不格式化无关文件。
- **跟随现有风格**：命名、目录结构、错误处理、日志、注释语言都与周围代码保持一致。
- **补上验证**：新增行为要有测试；修 bug 要有能复现原问题的测试，或至少一个明确的验证步骤。
- **不留垃圾**：调试输出、被注释掉的代码、临时 TODO 在提交前清理干净。
- 改动大就拆成多个逻辑清晰的提交；但不要为了凑提交而拆。

### 4. 本地验证（提交前必须做）

按项目自己的门禁命令跑：`make test`、`npm test`、`pnpm lint`、`pytest`、`swift test`、`cargo test` 之类。**项目有什么就跑什么**，至少覆盖：

- 本次改动相关的测试
- 项目主测试套件
- lint / format / typecheck / build（项目有的都要跑）

失败就修，修到过。**不要**用 `--no-verify`、跳过测试、注释掉失败用例来"让它过"。

### 5. 提交

```bash
git checkout -b <type>/<short-slug>     # 例如 fix/upload-timeout、feat/csv-export
git add -A
git commit -m "<遵循仓库规范的提交信息>"
```

- 分支名和提交信息格式**先看仓库历史再决定**；没有约定时用 Conventional Commits（`fix:`、`feat:`、`docs:`、`refactor:`、`test:`、`chore:`）。
- 提交信息说清"为什么改"，细节放正文。
- 不把构建产物、密钥、本地配置提交进去。

### 6. 推送并开 Pull Request

```bash
git push -u origin HEAD

gh pr create --base <默认分支> --title "<简洁标题>" --body-file <PR 描述文件>
```

- **有 PR 模板就按模板填**（`gh pr create` 会自动带出模板，也可以自己对齐结构）。
- PR 描述必须包含：**改了什么、为什么这么改、怎么验证的**，并给出可执行的验证命令或结果输出。
- 目标分支默认是仓库默认分支；fork 场景注意 `--head <owner>:<branch>`。
- 除非用户要求，不要开 draft PR——开出来就该是能合的状态。
- 不要自己合并（用户明确要求且项目允许时除外）。

### 7. 盯 GitHub Actions，直到全绿

这是「确保 Actions 全部通过」的具体做法：

```bash
gh pr checks                     # 一次性看所有检查状态
gh pr checks --watch             # 实时盯到结束
gh run list --branch <branch>    # 看 workflow 运行列表
gh run view <run-id>             # 看某次运行的概要
gh run view <run-id> --log-failed    # 只看失败步骤的日志
gh run watch <run-id>            # 盯某一次运行
```

循环：

1. 等检查结束（`gh pr checks --watch`，需要快速失败时加 `--fail-fast`）。
2. 有失败 → `gh run view <id> --log-failed` 找根因 → **改代码** → 提交 → 推送。
3. 回到第 1 步，直到全部通过。

处理细节：

- **确实偶发**（flaky）：可以 `gh run rerun <id> --failed` 重跑一次；同一处连续两次失败就当真实问题修。
- **一直 pending**：可能是首次贡献者需要维护者批准、并发额度已满、或 runner 排队。不要傻等，把状态和链接告诉用户。
- **被 skipped**：区分「路径过滤导致的正常跳过」和「配置写错」。前者可接受，后者要修。
- **required 与可选检查**：全绿指失败的都要处理。可选的失败也要么修掉，要么在回复里说明为什么不影响。
- **外部原因失败**（上游服务故障、额度用尽、需要项目 secret）：修不了就停下，把失败链接和原因清楚告诉用户。
- **仓库没有 CI**：做等价的本地验证，并在回复里说明「该仓库没有 GitHub Actions，我用 X 命令验证」。

### 8. 收尾

- 分支落后于 base 且有冲突 → 用 `git rebase origin/<base>`（或 merge）解决；解决后重新推送，并**重新等 CI 全绿**。
- 确认 PR 里没有无关改动、没有调试代码、没有敏感信息。
- 确认 PR 描述与实际改动一致。

## 汇报格式

搞定时用这个结构，简短为主：

```
已完成：<一句话结论>

改动：<文件/模块列表，关键文件给路径>
验证：<跑过的命令与结果；GitHub 项目给出 CI 状态>
PR：<链接>（CI：全绿 / N 项失败及原因）
遗留：<没有就写「无」>
```

被外部条件卡住时，明确写清：**卡在哪、为什么、需要用户做什么**。

## 红线

- ❌ 直接推默认分支（项目另有约定或用户明确要求时除外）。
- ❌ 对共享分支 force push（用户明确要求且已知后果时除外）。
- ❌ 绕过 CI、用 `--no-verify`、删测试或跳测试来让门禁变绿。
- ❌ 提交密钥、token、`.env`、个人配置。
- ❌ 顺手做大范围重构、升级依赖、改公共 API。
- ❌ CI 没绿就宣称「搞定了」。
- ❌ 擅自合并 PR、关闭 issue、改仓库设置。

## 参考

- GitHub 全流程命令、PR 模板处理、CI 排障与冲突处理：[references/github-pr.md](references/github-pr.md)
