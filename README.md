# AI 大模型技术导引（v0.3.5）

> **在线阅读**：<https://mzy25.github.io/lai/> —— 30 个阅读单元（含导言与补页）的 hub、分章阅读、全文打印、术语总表与路线卡，浏览器打开即读，可离线。
>
> **源稿**：`series/`。

一套关于大模型技术与前景的中文入门读物：教知识，也教思路、养直觉、练技能。全书按一条主线组织：

```text
开篇 总览与读法（3 节）
   ↓
第一篇 建造：模型怎样获得能力（§1–§9）
   ↓
支线 生成深潜（导言＋T1–T4＋补页，选修）
   ↓
第二篇 规律与边界：能力为什么可信、里面有什么、哪里到头（§10–§14）
   ↓
第三篇 驾驭：把能力用成可靠系统（§15–§19）
   ↓
终篇 前沿与收束：走出屏幕之后（§20–§21）
```

主线链路：数 → 学 → 分 → 传 → 联 → 压 → 教 → 改 → 说 → 反常 → 凭什么 → 可预测 → 内部 → 边界 → 出错 → 装配 → 控 → 落成 → 群变 → 触界 → 回望。

## 怎么读

- **目录与路线向导**：<https://mzy25.github.io/lai/>。默认自由读；四个方向＋半日试读：应用 / Agent、训练 / 调参、生成、研究；每个方向两条路线（先拿结果／走得更全），另有尝鲜与自由读。
- **分章阅读**：hub 里的 30 个单元，各章有阅读时长与读法标记（▽ 可后读／○ 支线先补／◌ 延伸选读／◇ 主线依赖）；正文各章章末带自查。
- **全文打印**：`print.html`，适合打印与全文检索。
- **术语总表**：`terms.html`，按首现章排序，支持筛词。
- **路线与论文清单**：`routes.html`。
- **环境指南 / 数学自修自测 / 资产索引**：`env.html`、`selftest.html`、`assets.html`。

GitHub 上的章节目录见 [`series/README.md`](series/README.md)。

## 仓库结构

```text
series/                     # 源稿与构建工具（唯一内容权威）
├── §0.1…§21、T1–T4、支线导言与补页.md
├── profiles/               # 章表、路线库、发布元数据
├── figures/                # 配图（generate_figures.py 单一来源）
├── assets/                 # 各章体验实验的脚本、笔记本、运行记录
├── supply/                 # 环境指南、数学自修自测
├── style/                  # 写作声音、句长基准、喻体台账、套话词表
├── data/                   # 术语/符号/引用规则（公开构建数据）
├── tools/                  # build_site / series_check / 行文与路线仪器
└── dist/                   # ★ 发布产物（GitHub Pages 直接上传此目录）
build/check_artifact_fresh.py  # 产物新鲜度门禁
```

## 构建

普通阅读不需要构建：`series/dist/` 已随仓库提供。二次开发或校订时：

```bash
python3 series/tools/build_site.py       # series/*.md → series/dist/
python3 series/tools/series_check.py     # 页面/锚点/路线/资产/配图/print 门禁
python3 series/tools/build_readme.py --check
python3 series/tools/first_use_scan.py --all --ledger-only --strict  # 术语首现/总账
python3 build/check_artifact_fresh.py    # 与 HEAD 比对，源稿改了忘重建会报红
```

环境要求：

- **Python 3.10+**（构建脚本使用新式类型标注）
- **pandoc**（HTML 构建；开发与 CI 使用 3.1.3）
- **Node.js**（`series_check` 的路线层 JS 对拍）
- 配图另需 **matplotlib/numpy** 与中文字体（Noto Sans CJK）；配图已入库，普通构建不需要重生成

## 写稿与门禁

- 系列文风：`series/style/写作声音.md`、`series/style/句长基准.md`、`series/style/喻体台账.md`
- 术语/符号：`series/data/*.tsv`；完整编辑台账在本地 `series/edit/`，不随公开仓
- 改稿收尾：`python3 series/tools/finish_round.py`（首现/总账、句长、表格、残留、路线、构建双跑）
- 工具索引：`series/tools/README.md`（构建、门禁、测量、手动工具各在哪）
- 实验三条铁律：引用已有数字必复算；新实验必真跑并留档 `series/assets/`；正文数字与运行记录逐条对账

## 更新日志

版本变化见 [CHANGELOG.md](./CHANGELOG.md)。

## 勘误与反馈

内容勘误、表述建议或排版问题，欢迎在 [GitHub 仓库](https://github.com/mzy25/lai) 提 Issue / PR；引用本书内容请注明出处。

## 许可

本仓库全部内容以宽松许可开放，可自由使用、修改、再分发（含商业用途），保留署名/版权声明即可：

- **正文与配图**（`series/` 下 `.md`、`figures/`、`assets/`、`dist/`）：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh-hans)
- **构建脚本与代码**（`series/tools/`、`build/`）：MIT

详见 [`LICENSE`](LICENSE)。
