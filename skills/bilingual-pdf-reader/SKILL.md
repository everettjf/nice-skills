---
name: bilingual-pdf-reader
description: 把英文 PDF（短篇、教材课文、新闻、论文、说明书）做成逐段中英对照的精读稿：每段英文下面给地道中文译文，译文下面再用「生词」一行标出不常见词条的发音与中文释义。产出 Markdown 与排版好的 A4 PDF。当用户说「把这篇文章翻译成中英对照」「英文 PDF 转成中英文」「加生词和音标」「做一份双语阅读稿」「英文 PDF 输出成一段英文一段中文」时使用。
license: MIT
---

# 英文 PDF → 中英对照精读稿

一句话：**输入一个英文 PDF，产出「逐段英文 + 地道中文 + 生词（音标 / 词性 / 释义）」的 Markdown 和 A4 PDF。**

标准输出长这样（每段一个循环）：

```markdown
**1**

The dark sky, filled with angry, swirling clouds, reflected Greg Ridley's mood as he sat on the stoop of his building.

> 天空阴沉，乌云翻搅着，像在生谁的气。格雷格·里德利坐在自家楼门前的台阶上，这天色跟他的心情正好对得上。

生词：**stoop** /stuːp/ *n.* （美）楼门前的台阶 · **principal** /ˈprɪnsəpəl/ *n.* 校长
```

## 交付物

默认在**源 PDF 所在目录**（或用户指定的阅读目录）产出两个同名文件：

- `<标题>-中英对照.md`——可继续编辑的源文件；
- `<标题>-中英对照.pdf`——A4、封面独立成页、页脚带页码、中文字体内嵌。

用户只要中文、不要 PDF、或还想加英式音标等，按他说的裁剪；**不清楚就问一次**，不要反复确认。

## 流程

### 0. 先确认三件事

1. **范围**：整篇翻，还是只翻正文（跳过封面、版权页、练习题、参考文献）？
2. **形式**：要 Markdown、PDF，还是都要？生词要不要带音标？
3. **交付位置**：源目录 / 指定目录 / 直接贴在对话里。

用户一句话就交代清楚的，别追问，直接做。

### 1. 抽文本

```bash
python3 scripts/extract_pdf.py input.pdf -o original.md --start-page 2 --end-page 9
```

- 输出是编号段落（`**1**`、`**2**`…）+ frontmatter，末尾附「脚注」区（原书自带的注释——这些词**一定要进生词行**，并标注「原文脚注词」）。
- 脚本已经处理：双栏重排、跨页页眉页脚、页码、`[12]` 角标、粘在词尾的脚注数字（`gnarled9` → `gnarled`）。
- 封面页、练习题栏（`Name:` `Class:`）这类版式杂物**抽不干净是正常的**，下一步处理。

### 2. 复核分段（不可跳过）

机器初切一定会有 2%–5% 的段落边界错误。**必须对照原文读一遍**：

- 段落被切碎的 → 合并；两段被并成一段的 → 拆开；
- 删掉封面、版权页、练习题栏、图片说明等非正文内容；
- 对话必须一句一段；
- 重新连续编号，确认 1…N 无缺号。

快速自查：`python3 scripts/check_bilingual.py bilingual.md` 会报段号是否连续；段落数应与原文一致。

### 3. 逐段翻译

按 [references/translation-style.md](references/translation-style.md) 来。要点：

- **一段英文对一段中文**，不合并、不拆分、不漏译、不添油加醋；
- 叙述部分用干净顺畅的现代汉语，不要翻译腔；
- **人物对话按身份给口语层次**：方言、市井人物、黑人英语（AAVE）要译出「没读多少书但话讲得清楚」的味道（甭、瞅、撵、消停、稀罕、没跑、犯傻），既不能洗成标准书面语，也不能土到读不懂；
- 把结果写进双语稿，骨架照 [assets/bilingual-template.md](assets/bilingual-template.md)；
- 长文（100 段以上）分批译，**每批译完立刻写进文件**，避免上下文丢失后重来。

### 4. 标生词

按 [references/vocab-guide.md](references/vocab-guide.md) 的阈值选词，写成 JSON 再插入：

```json
{"1": [["stoop", "/stuːp/", "n.", "（美）楼门前的台阶"],
       ["principal", "/ˈprɪnsəpəl/", "n.", "校长"]]}
```

```bash
python3 scripts/insert_vocab.py bilingual.md vocab.json
```

- 每段 0–4 条，平均 1–2 条；原文脚注词全收；
- 词组、习语、语境义、老式说法都在收词范围内；
- **音标拿不准就不写**，宁缺勿错；格式与词性取值由脚本校验。

### 5. 审校与译注

- 通读中文，凡是读起来拗口的句子改掉；
- 正文后加 3–8 条「译注」，只写真正需要交代的取舍（难译点、双关、方言策略、原文排印问题）；
- 开头写版权提示，提醒用户仅供个人学习、不要公开发布受版权保护的全文。

### 6. 排版 PDF

```bash
python3 scripts/render_pdf.py bilingual.md -o 标题-中英对照.pdf
```

封面信息取自 frontmatter 的 `title` / `original` / `author` / `year`。脚本会做封面页、段落号、译文细线、生词行、译注列表、页脚页码；中文字体按 `Songti SC → Noto Serif CJK SC → Source Han Serif` 依次回退，西文用 Georgia。

### 7. 自检 + 目检 + 汇报

```bash
python3 scripts/check_bilingual.py bilingual.md --source input.pdf --pdf 标题-中英对照.pdf
```

脚本检查：段号连续性、每段中英齐全、生词行格式与词性取值、生词是否真的出现在该段、**英文与源 PDF 的词流比对**（漏译/多译）、PDF 页数与 HTML 标签泄漏、字体内嵌。

脚本之外还必须做一次**目检**：抽 1–2 页渲染成图（`page.get_pixmap(dpi=110)`）看一眼，确认封面、生词行、断页没有明显问题。

最后汇报：交付文件路径、段落数、生词条数、PDF 页数、自检结论、以及需要用户拍板的地方（比如原文里的明显错字怎么处理、某处译法有两个选择）。

## 红线

1. **版权**：受版权保护的全文翻译只供个人学习，文件头必须写版权提示，并提醒用户不要公开发布；用户说要发到公众号、博客时，改为「导读 + 有限引文 + 解读」的形态。
2. **不遗漏、不杜撰**：英文必须与源文一一对应；补充说明只能进译注，不能混进译文。
3. **不合并段落**：中英段落必须一一对应，这是这份稿子的使用方式。
4. **不把方言洗白**：人物一开口就变成书面语，等于把人物删掉。
5. **音标宁缺勿错**。
6. **不只跑脚本不看页面**：脚本过了仍然要目检，排版问题只有眼睛能发现。

## 目录

- `scripts/extract_pdf.py`——PDF → 编号段落 Markdown（双栏、页眉页脚、脚注处理）
- `scripts/insert_vocab.py`——生词表 JSON → 按段插入「生词：」行（幂等）
- `scripts/render_pdf.py`——双语 Markdown → A4 PDF（封面 / 生词行 / 译注 / 页码）
- `scripts/check_bilingual.py`——交付自检（结构、生词、英文保真、PDF 成品）
- `scripts/selftest.py`——脚本自测（行距聚类、同视觉行合并、脚注数字剥离、生词幂等），不依赖外部库
- `assets/bilingual-template.md`——双语稿骨架，含 frontmatter 与各区块写法
- `references/translation-style.md`——翻译规范：忠实度、口语层次、难点处理、译注写法
- `references/vocab-guide.md`——生词规范：收词阈值、格式、音标约定、自检

## 依赖

```bash
pip install pymupdf weasyprint     # 抽文本与排 PDF
# macOS 上 weasyprint 若装不上：brew install weasyprint
```

PDF 相关步骤需要 PyMuPDF；只做 Markdown 不排 PDF 时可以跳过 weasyprint。
