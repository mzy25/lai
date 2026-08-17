# AI 认知大模型技术导引
> **版本**：0.1

本仓库按章节保存 Markdown 源稿、配图脚本、配图；最终发布产物是 `html/index.html`（响应式 HTML），`docx/` 下的 DOCX 作为参考副本。定位是**认知大模型技术和前景的入门导引，也教思路、养直觉、练技能**。

## 怎么看 AI：三个视角、三个问题

AI 没有唯一本质，不同学科各取一个视角，合起来用三个互补的视角看它，每个视角回答一个问题：

| 视角 | 问的问题 | 对应篇章 |
|:---|:---|:---|
| 动力学（数学/物理） | 模型是怎么造出来的？ | 《AI数学》《扩散》 |
| 几何与表示（数学） | 造出来后，学到的知识长什么样、怎么组织？ | 《基座模型》 |
| 社会-工程（工程/社会） | 把 AI 放进真实世界，怎么从有用变好用？ | 《用好AI》 |

三个问题连成一条追问链——怎么造、造出什么、怎么用。核心三步是《AI数学》→《基座模型》→《用好AI》：《AI数学》讲模型怎么造（训练是优化），《基座模型》讲造出来的知识长什么样（潜空间结构、能力涌现），《用好AI》讲怎么把 AI 用出可靠结果（后训练让模型可用、Harness 让系统可靠、使用有章法）。《扩散》是生成式 AI 的数学深入分支，从《AI数学》的分数匹配出发，讲另一条“怎么造”（生成是塑形）；它不是核心路径的前置，而是按需选读的深入篇。

## 四篇文档 & 推荐阅读顺序

四篇文档**独立可读**，也构成一条“核心三步 + 一条选读分支”的路径。跨篇引用统一用书名简称：《AI数学》《扩散》《基座模型》《用好AI》。

**核心路径（推荐按顺序读）**

1. **`1_ai_math/`** - AI数学：从起步到前沿（7 章）
   数学工具链--梯度下降、拉格朗日、Softmax、反向传播、Attention、LoRA、MoE。为《基座模型》和《用好AI》提供数学基础，也是《扩散》的数学起点。第 7 章前沿展望讲五场范式转移（混合架构、MoE、测试时算力、数据墙、扩散模型），收束到扩散模型作为数学桥梁。

2. **`2_foundation/`** - 基座模型：从咿呀到行动（6 章）
   AI 的当前主流。萃取->筑基->炼灵->应变->行动->收束。覆盖预训练与潜空间、SFT 与对齐起点、推理算力与 GRPO、RLHF/DPO/Safe RL、KV Cache 与全双工、VLA 与具身智能、世界模型六流派。§6.4 概念城市：潜空间可解释性与可干预性（SAE/电路追踪/知识编辑/激活引导/J-space/Latent Agents）。GPT-Live、DeepSeek-R1、Figure Helix 等 2024-2026 前沿。其中第2/3/6章内部分 Part A/B，便于按需深入：Ch2 潜空间与预训练/多模态接入，Ch3 推理与对齐/安全与落地，Ch6 世界模型与认知架构/可解释性与应用。

3. **`3_use_ai/`** - 用好AI：从有用到好用（10 章 + 附录）
   AI 已经有用，怎么把它用好？三站旅程：有用 → 可用（后训练四种反馈：例题/打分/对错/干活）→ 好用（Harness 六层 × 使用章法）。POMDP 眼镜、Harness 六层与选型地图、控制范式、规划与 Skill 双刃性、四类失效、评估与护栏、数字与物理、多 Agent 协作（AgentFail 三层十三类）、自演化三路线与三硬边界。附录 algo-coach 把全篇框架应用到一个真实产品；附录“如何实现一个 Agent/Harness”以 DeepSeek Harness 为参照给出从零落地清单。

**选读分支（可放在核心路径之后，也可在读完《AI数学》后直接深入）**

- **`1a_diffusion/`** - 扩散：从噪声生成（9 章 + 附录）
  生成式 AI 的另一条主线。从"加噪声"出发，一步步推导 SDE/ODE 框架、条件控制、离散扩散，收束到视频生成、世界模型和扩散策略。与《AI数学》共享数学基础（梯度→分数匹配），独立展开。第 9 章用"技法 × 工具"框架统一前沿变体（DiT、流匹配、一致性模型、SD3 工业配方）。数学预备附录 A 提供符号速查表与高斯/期望/梯度/ODE/反向传播条目。

## 自检怎么用

四篇的每章末尾都有"本章自检"。提示和答案的位置因发布产物而异，请在阅读时以当前产物版式为准：

- **HTML（`html/index.html`）**：提示与答案以折叠块形式放在各题旁边，先独立作答，需要时再点开。
- **DOCX（`docx/` 参考副本）**：提示保留在题目区，答案集中在文末答案区，以保持"先作答、再翻页对照"的隔离。

用法三步：

1. **先独立作答**（回想或默写），卡住再看提示——提示只给方向；
2. **对照答案**——答案句末的 §X.Y 就是回看正文的位置；
3. 自检有五种题型：知识点（回忆）、逻辑链（追溯链条）、迁移（换场景用）、边界（适用条件）、生成（画图/举例/列表）。生成题的答案自带"核对你的答案"清单，用它自评要点，不只对结论。

## 跨篇分工：概念地图

四篇之间有明确的分工边界，避免内容重复。下表把同一概念在不同文档中的位置标成“先读 → 深入 → 应用/延展”，方便按路径定位。

| 概念 | 首次/场景直觉 | 深入/机制 | 应用/延展 | 推荐顺序 |
|:---|:---|:---|:---|:---|
| **POMDP** | 《基座模型》§5.2 讲机器人场景直觉（扫地机器人） | 《用好AI》第2章讲完整七元组与信念手算、第3章讲 Harness 六层映射 | 《用好AI》第6章四类失效归类、第7章长程规划、第9章多 Agent 根因 | 基座 §5.2 → 用好AI 第2章 → 用好AI 第6/7/9章 |
| **世界模型** | 《基座模型》§6.2 讲六流派全景与胜负手 | 《扩散》§8.2 讲扩散视角的 SDE 延伸 | 《扩散》§9.6 讲扩散在路线之争中的位置；《用好AI》第8章讲物理 Agent 约束 | 基座 §6.2 → 扩散 §8.2 → 扩散 §9.6 / 用好AI 第8章 |
| **扩散策略** | 《基座模型》§5.3-5.4 讲 VLA 与动作表示 | 《扩散》§8.3 讲多峰动作分布 | 《用好AI》第8章讲物理 Agent 约束 | 基座 §5.3-5.4 → 扩散 §8.3 → 用好AI 第8章 |
| **推理模型** | 《AI数学》§7 讲数学联系（test-time compute scaling） | 《基座模型》§3.3/§3.7 讲三代演进与 GRPO 算法 | 《用好AI》第1章 RLVR 使用侧、第5章规划成本与 Effort | AI数学 §7 → 基座 §3.3/§3.7 → 用好AI 第1/5章 |
| **推理加速** | 《AI数学》§6.8 落地表格给低秩定位 | 《基座模型》§4.2 讲 KV Cache 与加速全景（PagedAttention/推测解码/量化） | 《用好AI》第3章 Harness 选型、第8章物理端云分层 | AI数学 §6.8 → 基座 §4.2 → 用好AI 第3/8章 |
| **后训练** | 《用好AI》第1章讲使用侧四种反馈（例题/打分/对错/干活）；《基座模型》第3章讲算法起点 | 《基座模型》第3章讲算法与训练细节（SFT/RLHF/DPO/GRPO/Safe RL） | 《用好AI》第7章评估与护栏 | 先用《用好AI》第1章建立使用直觉，再读《基座模型》第3章；也可按核心路径先读基座第3章 |

## 目录结构

```
.
├── 1_ai_math/           # 《AI数学》：源稿 .md + generate_figures.py + figures/
├── 1a_diffusion/        # 《扩散》：源稿 .md + generate_figures.py + figures/ + references/
├── 2_foundation/        # 《基座模型》：源稿 .md + generate_figures.py + figures/
├── 3_use_ai/             # 《用好AI》：源稿 .md + generate_figures.py + figures/ + references/
├── html/                # 最终发布产物（index.html + 本地 KaTeX/figures）
├── docx/                # DOCX 参考副本（四篇）
├── build_html.py        # Markdown → HTML 最终发布构建脚本
├── build_docx.py        # Markdown → DOCX 参考副本构建脚本（Chapter 配置硬编码目录名）
├── style_docx.py        # DOCX 样式统一（字体/标题/表格/页眉/页码/图片尺寸）
├── fig_common.py        # 四篇配图脚本共享模块（CJK 字体探测/保存/rcParams）
└── requirements.txt     # 依赖（numpy、matplotlib、python-docx、lxml）
```

`references/` 存放写作时的参考资料（PDF/调研笔记），不参与构建。

## 生成发布产物

### 最终 HTML（推荐）

依赖：`pandoc`、`matplotlib`、`numpy`。

```bash
python3 build_html.py                # 生成 html/index.html
```

> 如果仓库中没有 `vendor/`，脚本会自动通过 `npm` 安装 KaTeX 和 highlight.js 到系统临时缓存（需要 Node.js/npm 和网络）。

生成流程：

1. `pandoc` 将四篇 Markdown 分别转为 HTML 片段。
2. `md_links.py` 修复目录锚点与跨篇链接。
3. `build_html.py` 合并为单个响应式 `html/index.html`，并复制本地 KaTeX/figures。

### DOCX 参考副本

依赖：`pandoc`、`python-docx`、`matplotlib`、`numpy`。

```bash
python3 build_docx.py              # 生成全部 DOCX 参考副本
python3 build_docx.py 1a_diffusion  # 只生成扩散模型章节
python3 build_docx.py --verify-only
```

生成流程：

1. `pandoc` 将章节 Markdown 转为 `*_raw.docx`（放在章节文件夹）。
2. 根目录 `style_docx.py` 统一字体、标题、表格、页眉、页码和图片尺寸。
3. DOCX 输出到 `docx/` 目录，成功后自动删除 `*_raw.docx` 中间文件。

`style_docx.py` 也可单独使用：

```bash
python3 style_docx.py --input path/to/input_raw.docx --output path/to/output.docx --fallback-title 文档标题
```

## 配图

- `fig_common.py`（根目录）：四篇配图脚本共享的基础模块——CJK 字体自动探测、统一保存函数、rcParams、批处理进度打印。
- `1_ai_math/generate_figures.py` 生成《AI数学》配图到 `1_ai_math/figures/`（20 张）。
- `1a_diffusion/generate_figures.py` 生成《扩散》配图到 `1a_diffusion/figures/`（41 张）。
- `2_foundation/generate_figures.py` 生成《基座模型》配图到 `2_foundation/figures/`（23 张）。
- `3_use_ai/generate_figures.py` 生成《用好AI》配图到 `3_use_ai/figures/`（19 张）。

依赖安装：`python3 -m pip install -r requirements.txt`（numpy、matplotlib、python-docx、lxml）。
