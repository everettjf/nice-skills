# GitHub 交付参考

配合 [SKILL.md](../SKILL.md) 第 5–7 步使用。这里的命令都是可直接复制执行的，`<...>` 是占位符。

## 1. 开工前先摸清仓库

```bash
# 默认分支
gh repo view --json defaultBranchRef -q .defaultBranchRef.name
# 或者
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'

# 当前分支与工作区状态
git status --short --branch

# 近期提交风格（决定你的 commit message 怎么写）
git log --oneline -20

# CI 配置与 PR 模板
ls -la .github/workflows/ 2>/dev/null
ls -la .github/ 2>/dev/null

# 仓库自己的门禁命令
cat Makefile justfile package.json 2>/dev/null
```

如果仓库配置了 `.github/PULL_REQUEST_TEMPLATE.md`，`gh pr create` 交互模式会自动带出来；用 `--body-file` 时请手动按模板结构填。

## 2. 同步与建分支

```bash
git fetch origin
git checkout -b <type>/<slug> origin/<default-branch>
```

分支名前缀跟随仓库历史。没有约定时用 `fix/` `feat/` `docs/` `chore/`。

## 3. 提交前自检

```bash
git status --short          # 有没有不该提交的文件
git diff --stat             # 改动范围是否符合预期
git diff                    # 逐行看一遍，找调试残留
```

常见误提交：`.env`、`*.log`、`node_modules/`、`.build/`、`.DS_Store`、IDE 配置、临时脚本。

## 4. 开 PR

### 普通情况（同仓库分支）

先把 PR 描述写进 `pr.md`（临时文件，不要提交进仓库）：

```markdown
## 改了什么
<一句话结论 + 关键文件>

## 为什么
<动机、背景、关联 issue>

## 怎么验证
<可执行的验证命令与实际结果>

Closes #<issue>
```

再推送并开 PR：

```bash
git push -u origin HEAD

gh pr create \
  --base <default-branch> \
  --head <your-branch> \
  --title "<type>: <简短说明>" \
  --body-file pr.md
```

### fork 场景

```bash
git remote add fork git@github.com:<you>/<repo>.git   # 如果还没加
git push -u fork HEAD

gh pr create \
  --repo <upstream-owner>/<repo> \
  --base <default-branch> \
  --head <you>:<your-branch> \
  --title "..." --body-file pr.md
```

### PR 描述的硬要求

- **改了什么**：一句话结论 + 关键文件/模块。
- **为什么**：动机、背景、被修的问题（关联 issue）。
- **怎么验证**：具体命令和实际结果，不是"应该没问题"。
- 涉及界面/输出的改动，附截图或文本输出。
- 有取舍和已知局限，写清楚。

## 5. 等 CI 全绿

```bash
# 列出这个 PR 的检查项
gh pr checks <pr-number>

# 盯到全部结束（--fail-fast 遇到失败立即返回）
gh pr checks <pr-number> --watch --fail-fast

# 只看必需项
gh pr checks <pr-number> --required

# 结构化输出，便于脚本判断
gh pr checks <pr-number> --json name,state,link,bucket
```

`bucket` 取值：`pass`、`fail`、`pending`、`skipping`、`cancel`。

### 失败后定位

```bash
# 该分支最近的运行
gh run list --branch <branch> --limit 10

# 某次运行的整体状态与失败 job
gh run view <run-id>

# 只打印失败步骤日志（信息密度最高）
gh run view <run-id> --log-failed

# 完整日志
gh run view <run-id> --log

# 下载失败运行的产物（截图、测试报告等）
gh run download <run-id>
```

### 常见失败类型与处理

| 现象 | 常见原因 | 处理 |
| --- | --- | --- |
| lint / format 失败 | 本地没跑格式化 | 跑项目 formatter，单独提交 |
| 类型检查失败 | 类型不匹配、缺注解 | 改代码，别加 `any`/`# type: ignore` 糊过去 |
| 测试失败 | 行为确实错了，或环境差异 | 本地复现同一命令；复现不了就看 CI 环境变量/版本差异 |
| 构建失败 | 依赖版本、平台差异 | 对齐 CI 里的工具链版本 |
| 超时 | 测试变慢、死锁 | 找新增的慢路径，别直接调大 timeout |
| 只在 CI 挂 | 时区/本地化/并发/随机顺序 | 固定随机种子、排序、显式时区 |
| 需要 secret 的 job | fork PR 拿不到 secret | 正常现象，说明情况；不要试图绕过 |
| 一直 queued | 并发限制、runner 不足 | 等待或说明；不要反复重推 |
| 首次贡献者待批准 | 安全策略 | 请维护者点批准，把链接给用户 |

### 重跑

```bash
gh run rerun <run-id>            # 整个运行重跑
gh run rerun <run-id> --failed   # 只重跑失败的 job
```

**同一处失败超过两次就不要再重跑了**，当真实问题修。

### 卡住时的判断

如果 10–15 分钟没有任何状态变化，先看是不是 `pending` 在等批准或排队，再决定是否继续等。把 `gh pr checks` 的输出贴给用户，比默默等待更有用。

## 6. 处理冲突与落后分支

```bash
git fetch origin
git rebase origin/<default-branch>

# 逐个解决冲突后
git add <resolved-files>
git rebase --continue

git push --force-with-lease
```

- 优先 `rebase`；项目使用 merge 策略或有明确的 merge 约定时改用 `git merge origin/<base>`。
- 只对自己的 PR 分支使用 `--force-with-lease`，绝不 force push 共享分支。
- **解决冲突后 CI 会重新跑，必须重新等全绿。**

## 7. 收尾检查

```bash
gh pr view <pr-number>              # 标题、描述、状态
gh pr checks <pr-number>            # 最终 CI 状态
gh pr diff <pr-number> --name-only  # 确认没有多余文件
gh pr view <pr-number> --json mergeable,mergeStateStatus
```

确认：

- [ ] 所有检查通过（或失败项已说明且被接受）
- [ ] 没有 merge 冲突
- [ ] PR 描述与实际改动一致
- [ ] 没有无关文件、调试代码、密钥
- [ ] 关联的 issue 已引用（`Closes #N`，如果项目这样用）

## 8. 没有 CI 的仓库

明确告诉用户："该仓库没有配置 GitHub Actions。"然后做等价验证并给出证据：

```bash
<项目自己的测试/构建/lint 命令>
```

至少跑一次完整测试。把命令和结果写进 PR 描述的「怎么验证」一节。

## 9. 非 GitHub 平台

- **GitLab**：`glab mr create --source-branch <branch> --target-branch <base>`；`glab ci status` 看流水线。
- **其他**：推分支，把「新建 PR/MR」的 URL 和步骤给用户（多数平台支持形如 `https://<host>/<owner>/<repo>/compare/<base>...<branch>` 的链接）。
