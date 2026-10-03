# md 源稿结构约定（构建契约）

五篇书稿的 `.md` 是唯一内容权威；`html/`、`docs/` 是构建产物，只重建不回写。
构建脚本（`build/`）与校验器会按本约定做结构检查，**约定之外的写法会导致构建失败**。

## 1. 块结构：空行隔离（最容易出事的一条）

以下"块标记"行的前一行必须是空行（行首 `>` 引用块、列表项等内容同理）：

- 标题行：`# 标题`、`## 标题`…
- 独立分隔符：`---`、`***`、`* * *`（构建端统一归一为 `***`）
- 自检区标记：`**本章自检**：`
- 自检组标签：`**【知识点】**` 等
- `<details>` / `</details>` 与代码围栏

缺空行的后果是**静默内容事故**：pandoc 会把标记并入上一段——标题消失（曾发生：
§1.5 标题被吞）、组标签失效、分隔符变字面 `* * *`。
`build/lint_md.py` 以 error 拦截（`hr-merge` / `heading-merge` / `block-merge`），
`build/mdprep.py` 在构建端兜底补空行。

## 2. 标题层级与附录顺序

- `#` —— 篇内章（`# 第N章：…`）/ 一级附录（`# 附录：…`）
- `##` —— 节（`## 2.3 …`）；篇首可有 `## 引子`、`## 目录`
- `###` / `####` —— 小节；自检附录内的章标题也用 `###`
- 自检附录标题固定为 `# 附录：自检问题与答案`（构建/校验的拆分锚点，逐字一致）
- 附录建议顺序：`数学预备`（如有）→ `自检问题与答案` → `扩展题`（如有）→
  `逻辑链` / `术语速查` / `动手路径` 等 → `参考文献`
- 自检附录应位于其后的附录之前；`附录：扩展题` 视为自检同族（答案同样翻页隔离）

## 3. 自检区规范形

正文（每章末尾）：

```
**本章自检**：

**【组名】**            ← 可选；组内编号可重起，也可全章连续（与附录一致即可）

1. 题干……
2. 题干……              ← 有序列表；正文只放裸题，不放提示/答案
```

附录（每题一条记录）：

```
# 附录：自检问题与答案

### 第N章：<与该章 H1 标题逐字一致>

**【组名】**            ← 与正文同序（正文有才写）

Q1. 题干……             ← 与正文对应题逐字一致（不加粗，2026-09-15 裁决；镜像规则见下；不一致即构建错误）

<details>
<summary>卡住再看提示</summary>

提示（可选）
</details>

<details>
<summary>答案</summary>

答案（必填）
</details>
```

守恒规则（`build/selfcheck.py` + lint 强制）：正文题数 == 附录记录数（逐区），
每题恰好一个答案、至多一个提示，组序一致。

**题干镜像规则**：附录题头 = 正文题干去掉内联支架后的逐字文本。支架的两种
登记形式（比对时自动剥离，正文可带、附录不带）：

- 括号提示：`（提示：…）`
- 句尾提示：`…题干？提示：…`

例题、子问题、交付物要求、方法指路属于**题目内容**，两侧必须一致；不一致、
少题或多题都是 **error**（构建中止）。类型标签（如 `（反事实・边界情况）`）
由附录题头 `**Qn（标签）. 题干**` 承载，正文内联标签不参与比对。

`# 附录：扩展题` 独立成段（正文无对应题干），其 Q/A 同样走 `<details>` 折叠。

## 4. 引用与链接

- 上标引用两种写法均可：`^[N]^`、`<sup>[N]</sup>`（构建端统一）；
  参考文献区的裸 `[N]` 是列表编号，不受影响
- 跨篇引用：`《AI数学》§1.5`、`《基座模型》第3章`（构建端自动转链接；
  解析不到目标会导致构建失败）
- 篇内目录锚点：`[文字](#锚点)`，锚点由 `build/md_links.py` 用 pandoc 实际 id 改写，
  解析失败会在构建日志告警

## 5. 图与表

- 图片引用：`![alt](figures/xxx.png)`（相对篇目录）；构建复制到 `html/figures/`
  并加篇前缀（`aimath_`/`base_`/`use_`/`diff_`/`ailaw_`）
- 每张引用图必须存在；`figures/` 里不允许有未被引用的 PNG（lint 检查）
- 图注写 `图N：…`（**不加粗**，2026-09-15 裁决）；表格用标准 pipe 语法，构建端自动包 `.table-wrap`

## 6. 构建与校验

```bash
.venv/bin/python build/build_html.py          # 构建 HTML（内含 lint + 产物校验）
.venv/bin/python build/build_docx.py          # 构建 DOCX（内含 lint）
.venv/bin/python build/build_docx.py --verify-only   # 标题/答案/图片/锚点完整性
.venv/bin/python build/lint_md.py             # 只跑结构 lint
.venv/bin/python build/check_html.py          # 只跑 HTML 产物校验
.venv/bin/python build/build_cards.py         # 构建学习卡（html/cards.html + cards/*.tsv）
.venv/bin/python build/check_cards.py --report /tmp/cards_report.md  # 清晰度/链接报告
```

- lint 规则自检夹具：`build/lint_md.py --selftest`、`build/mdprep.py --selftest`、
  `build/selfcheck.py --selftest`、`build/check_cards.py --selftest`
- 新增/改名书册：只改 `build/books.py`（路径/书名/doc-id/图前缀/跨篇别名）

## 7. 约定变更流程

1. 先改本文件 + linter 夹具（`--selftest` 证明新规则有效）
2. 再改源稿使其通过
3. 重建两条产物并跑 `check_html.py` + `build_docx.py --verify-only`

## 8. 学习卡源结构（cards 构建接口）

学习卡（`html/cards.html` + `cards/ai-primer_cards.tsv`）从以下既有结构抽取，
均为**构建接口**——改动这些结构必须同步 `build/build_cards.py` 的抽取器与断言：

| 卡堆 | 源结构 | 抽取依据 |
|---|---|---|
| 章核心 | 章首 blockquote：`> **核心概念/核心推导/核心心智模型/核心决策**：` + 有序列表 | 每章一块；标签四选一 |
| 误解 | `**误解N**："…"`（扩散/基座）、`**常见误解**："…"`（用好AI）、`**误解一："…"**`（AI规律/数学） | 每书 profile；逐书计数断言 |
| 术语 | `build/glossary.json`（术语 → 释义） | 自动定位书中首现小节 |
| 自检题 | §3 规范形（正文题 ↔ 附录答案）+ `# 附录：扩展题` | `build/selfcheck.py` 解析 |

自含性要求（防断章取义）：卡片背面固定回显误解句/题干；`§X.Y` 自动超链到
`html/index.html` 锚点；确实不足的用 `build/cards_overrides.json` 定向桥接
（只许引用书中既有内容，`note` 记录理由）；复核豁免登记在 `build/cards_review.json`。
计数断言：章核心 37 / 误解 101 / 自检题 299（含扩展题）/ 术语 44；不到数即构建失败（与 README 481 张同源）。

## 9. 学习卡 overrides / review 体例（O1/O2，2026-10）

- **键**：卡 id（如 `quiz-1_ai_math-7-逻辑链-2`）或**限定题 ID** `q-…@<篇目键>`
  （如 `q-c7-lc02@1_ai_math`，取自题干 `{#q-…}`；qid 是篇内 ID，跨书重复是常态）。
  解析优先卡 id，其次限定题 ID；裸 qid 仅**全局唯一**时可解析，跨书歧义 = 冲突；
  同书同 qid 重复 = 冲突（防重编号/改名后误配）。
- **cards_overrides.json**：`{键: {字段}}`，字段白名单
  `front / echo / back / hint / context / source_label / note`——`validate_overrides`
  构建期校验，未知字段即告警。
- **cards_review.json**：`accepted` 下两类豁免——`short_back`（背面过短）、
  `deictic_echo_ok`（回显以指示词开头）；豁免指向不存在的卡 = 构建失败。
- 原则：override 只许引用书中既有内容，`note` 记录理由；改题号/重编号后重建，
  孤儿与冲突在构建期和 `check_cards` 报告暴露。
