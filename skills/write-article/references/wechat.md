# 微信公众号图文流程

配合 [SKILL.md](../SKILL.md) 的「写微信公众号」一节使用。目标是产出**可直接粘贴到公众号编辑器**的正文，加上一套已经生成好的图和一份待生成图的提示词。

## 平台约束（决定了怎么写）

| 约束 | 影响 |
| --- | --- |
| 编辑器不认 Markdown | 正文要按「粘贴后仍然整齐」的方式写：短段落、空行分隔、小标题层级清晰 |
| 外链基本不可点 | 不写 markdown 外链；引用改写成「可搜索的名称 + 来源」，确实要给地址时写成 `标题 : URL` 的纯文本 |
| 代码块没有高亮 | 关键代码用图片（截图或渲染图）呈现 |
| 图片会被压缩 | 每张图控制在 2MB 以内；文字类图用 PNG，照片用 JPG |
| 首图比例固定 | 封面用 2.35:1；分享卡片另需 1:1 |
| 手机阅读 | 一段 1–3 句；一段最多一处加粗；不用嵌套列表 |

## 整体流程

1. 按 [SKILL.md](../SKILL.md) 完成事实收集与提纲。
2. **先写配图清单**（见 [../assets/figure-plan-template.md](../assets/figure-plan-template.md)）。
3. 生成能自动生成的图，落盘到 `images/`。
4. 写正文，在对应位置插入图片引用和图注。
5. 生成封面方案。
6. 整理 `prompts.md`（待生成的图）和 `sources.md`（事实来源）。
7. 过一遍发布前检查清单。

## 配图清单

每张图至少写清五项：

| 字段 | 说明 |
| --- | --- |
| 位置 | 放在哪一节之后 |
| 目的 | 这张图要替读者解决什么理解困难 |
| 类型 | 流程图 / 结构图 / 时序图 / 数据图 / 截图 / 照片 / 插画 |
| 生成方式 | Mermaid / SVG / matplotlib / 截图 / AI 生成 / 外部素材 |
| 图注 | 一句话说明图里是什么，以及来源 |

**原则：每张图都要有存在的理由。** 纯装饰性的图，如果拿不到合适的素材，宁可不放。一篇 2000 字的文章通常 3–6 张图足够。

## 图片来源决策树

```
需要一张图
├── 能表达为流程 / 结构 / 时序 / 状态？ → Mermaid 渲染成 PNG
├── 是示意图、对比图、标注图？          → 手写 SVG 再转 PNG
├── 是数据图？                          → matplotlib / 图表库
├── 是界面或网页？                      → 浏览器自动化截图
├── 是真实照片、实景？                  → AI 生成提示词 + 占位（或使用许可明确的素材）
└── 是抽象氛围、概念插画？              → AI 生成提示词 + 占位
```

### Mermaid 流程图

```bash
mkdir -p figures images
cat > figures/flow.mmd <<'EOF'
flowchart LR
  A[请求] --> B{缓存命中?}
  B -- 是 --> C[返回缓存]
  B -- 否 --> D[查数据库]
  D --> E[写回缓存]
EOF

npx -y @mermaid-js/mermaid-cli \
  -i figures/flow.mmd \
  -o images/fig01-flow.png \
  -w 1200 -b white -t neutral
```

- 输出宽度建议 1200px（公众号正文宽度约 677px，2 倍图更清晰）。
- mermaid-cli 依赖 Chromium。若下载受限，写一个 `puppeteer-config.json` 指定本机 Chrome 路径，用 `-p puppeteer-config.json`。
- 图里的文字用中文没问题，但节点标签要短，渲染才不会挤。

### SVG 示意图

手写 SVG 后转 PNG：

```bash
rsvg-convert -w 1200 figures/diagram.svg -o images/fig02-diagram.png
# 或者
npx -y sharp-cli -i figures/diagram.svg -o images/fig02-diagram.png resize 1200
```

注意：**公众号不支持 SVG**，必须转成 PNG/JPG。

### 数据图

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Noto Sans CJK SC", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
ax.bar(["改造前", "改造后"], [820, 130], color=["#9aa4b2", "#2f6feb"])
ax.set_ylabel("P95 延迟（ms）")
ax.set_title("改造前后 P95 延迟对比")
for i, v in enumerate([820, 130]):
    ax.text(i, v + 15, str(v), ha="center")
fig.tight_layout()
fig.savefig("images/fig03-latency.png")
```

- 必须配置中文字体，否则中文变方框。
- 图上标注数值，读者不用去数柱子。
- 数据来源写进图注。

### 界面 / 网页截图

```bash
npx -y playwright screenshot \
  --viewport-size=1280,800 --full-page \
  https://example.com images/fig04-home.png
```

需要登录态或交互时，写一个小的 Playwright 脚本再截图。截图前把与正文无关的浏览器 UI、通知条隐藏掉。

### AI 配图提示词

生成不了的图，统一写进 `prompts.md`，格式：

```markdown
## fig05 · 文章第二节之后
- 用途：表现「数据在多个节点之间同步」这一抽象概念
- 尺寸：1200×675（16:9）
- 中文提示词：简洁的等距风格插画，四个圆形节点由发光线条连接，深蓝色背景，无文字
- English prompt: clean isometric illustration, four circular nodes connected by glowing lines, deep blue background, no text, flat vector style
- 备选：概念插画 / 抽象几何
```

正文里放占位：

```markdown
![图5：数据在多个节点之间同步](images/fig05-sync.png)

> 图 5：数据在多个节点之间同步。示意图，AI 生成。
```

**提示词要求**：写清风格、构图、配色、是否要文字（一般写 `no text`，因为 AI 生成的中文文字通常不可用）。

## 尺寸规范

| 用途 | 比例 | 建议尺寸 | 备注 |
| --- | --- | --- | --- |
| 封面首图 | 2.35:1 | 1170×500 或 900×383 | 公众号要求，超出会被裁 |
| 分享卡片 | 1:1 | 500×500 或更大 | 转发到会话时显示 |
| 正文宽图 | 16:9 | 1200×675 | 通用 |
| 正文竖图 | 4:3 | 1080×810 | 手机截图、照片 |
| 动图 | — | 宽度 600–800 | 体积小于 5MB，否则加载慢 |

## 封面设计

封面要给出：

1. **标题文案**：不超过 12 个字，和文章标题一致或更短。
2. **视觉方案**：用哪张图、还是单独做一张。能用 SVG 或 matplotlib 做就做出来。
3. **备用提示词**：需要 AI 生成时给中英双语提示词。

平实的做法：纯色或浅渐变背景 + 一句标题 + 一个简单图形。避免信息量过大的封面。

## 排版细则

- **开头**：不要「大家好」，直接进入导语；或一句话说明这篇讲什么。
- **段落**：1–3 句，段间空一行。
- **小标题**：用清晰的层级，可以直接是结论，例如「缓存失效的三种原因」。
- **加粗**：一段最多一处。到处都是加粗等于没有加粗。
- **列表**：少用。公众号里列表项换行显示不佳，能改成短段落就改。
- **代码**：用图片。真要用文字，就用短段落 + 缩进，且只保留关键几行。
- **引用**：用引用块（`>`）。
- **链接**：不写 markdown 外链。确实要给地址时写成 `标题 : URL` 的纯文本，例如 `vphone-cli : https://github.com/Lakr233/vphone-cli`；只是想让读者自己去找，就写「在 XX 官网搜索 YY」。
- **结尾**：可以放「参考来源」纯文字列表，或一句朴素的说明，不要二维码式硬广（除非用户要求）。
- **图片**：每张图下面都写图注，说明内容和来源/生成方式。

## 交付目录

```
<article-slug>/
├── article.md         # 正文，含图片引用和图注
├── images/            # 已生成的图，fig01-xxx.png 命名
├── figures/           # 图的源文件（.mmd / .svg / 绘图脚本）
├── prompts.md         # 待生成图的 AI 提示词（中英）
└── sources.md         # 事实来源与访问时间（链接用 `标题 : URL`）
```

保留 `figures/` 是为了图能改：改文案、改数据时重新渲染即可，不用重画。

## 发布前检查清单

- [ ] 标题准确，不做标题党；封面文案 ≤12 字
- [ ] 每张图都有图注，标明了来源或生成方式
- [ ] 图片尺寸符合上表，单张 < 2MB
- [ ] 正文无 markdown 外链；给出的链接写成 `标题 : URL` 纯文本
- [ ] 段落都是 1–3 句，手机上读不累
- [ ] 术语都解释过，外行能读懂导语和第一节
- [ ] 所有数据都有来源，写在 `sources.md` 里
- [ ] 没有营销腔、空话、感叹号
- [ ] `prompts.md` 覆盖了所有还没生成的图
- [ ] 文末有参考来源，每条是 `标题 : URL`，访问时间在开头统一说明

## 图片来源与版权

1. **优先自制**：Mermaid / SVG / 图表 / 自己的截图。
2. **次选许可明确的外部素材**：确认可商用、可修改，并在图注与文末标注作者和许可（如 CC BY 4.0）。
3. **不确定许可的一律不用。** 网上搜到的图片默认有版权，不要直接放进文章。
4. AI 生成的图，在图注里写明「AI 生成」。
