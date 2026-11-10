# series/tools 索引

所有工具从仓库根目录运行。构建产物一律写 `series/dist/`，不要手改。

## 任务 → 工具 → 门禁（单一入口）

| 任务 | 先跑 | 门禁/收尾 |
| --- | --- | --- |
| 写/改一章 | `series-writing` skill：首稿契约/句子配方 → 首稿自检；兜底再跑 `style-scan --series` + `sentence_stats --row` + `first_use_scan` | `finish_round.py` |
| 单章审阅（改动后） | `prose_diff.py --since HEAD --summary-only` → `section_map.py` → `coherence_scan.py`；按改动类型跑 `ripple_check.py` | `unit_closeout.py` / `finish_round.py` |
| 工具自检 | `selftest_tools.py`（新审阅工具）；`--all` 追加核心工具 | 改 `series/tools/*.py` 后 |
| 答案/正文镜像 | `answer_mirror_check.py "series/§N-….md"` | 人工裁决；`--strict` 可用于审阅批 |
| 单章精修取证 | `unit_closeout.py "series/§N-….md"` | 人工把摘要抄进修订记录；提交前仍跑 `finish_round` |
| 一轮/多章收尾 | `finish_round.py` | 收尾表全过；提交前不要用 `--no-build` |
| 内容审计 | `series-audit` skill：`table_check` / `reference_lint --strict` / `first_use_scan` / `metaphor_scan --strict` / `symbol_coverage --strict` / `residue_scan` / `row_check` | `series_check` |
| Phase 0/1 体检 | `phase01.py --gates`：语病/条件候选＋第N部/§N 指针＋术语多释；报告写 `series/.tmp/phase01/` | 人工分诊；`--strict` 有 L0/指针错/术语多释退 1 |
| 配图 | `series-figures` skill：`generate_figures.py` | `series_check` 配图 31/31 |
| 构建/发布 | `build-pipeline` skill：`build_site.py` | `series_check` + `check_artifact_fresh` |
| 规划/重排 | `series-planning` skill | `route_lint --check` + `build_readme --check` + anchors 漂移门 |

**收尾契约**：`finish_round.py` 是批量硬门禁；`unit_closeout.py` 是单章证据，不替代
全量门禁。`symbol_coverage --strict` 已入 `finish_round`；`cliche_scan`/`taste_probe`
只定位，不入硬门禁。公开数据 `series/data/` 由 `sync_public_data.py` 维护，本地有
私有 `series/edit/术语总账.tsv` 时 `finish_round` 会校验同步。行文 pass 在
`series-writing`，不在本目录的机械工具里。

**正文审阅工具边界**：`prose_diff`/`section_map`/`coherence_scan`/`answer_mirror_check`/
`ripple_check` 都是候选态，默认退出 0，不进入 `finish_round` 硬门禁；判断仍归
`series-writing`/`series-audit`。`prose_diff` 需要 git 基线（默认 `HEAD` 对工作区，
`HEAD~1` 对上一提交）；`review_log` 默认写私有 `series/edit/`，公开 clone 退回
`series/.tmp/`。新工具都有 `--selftest`；改工具后先跑自检，再跑 `series_check`。

**生成物/归档边界**：`series/.tmp/` 是可随时清空的运行产物；`series/dist/` 是发布产物，
只由 `build_site.py` 重建；`series/data/` 是公开构建数据（术语/符号/引用规则，随仓提交）；
`series/edit/` 是本地编辑档案（完整台账、提案、报告），整体不随公开仓提交，也不当垃圾删。
清理只动 `.tmp`/缓存，不动 archive。

| 工具 | 用途 | 状态 |
| --- | --- | --- |
| `build_site.py` | 章稿 → `series/dist/`（HTML／print／index／anchors）；`--selftest` 原子替换回归 | 构建 |
| `site_template.html` | 页面模板与样式（`build_site.py` 读取） | 数据 |
| `build_readme.py` | 生成／校验 `series/README.md` 章节表 | 构建／CI |
| `generate_figures.py` | 重生成 `series/figures/`（需 numpy／matplotlib） | 构建 |
| `fig_common.py` | 配图共用色板与函数（被 `generate_figures.py` 引用） | 模块 |
| `sub_sup_convert.py` | 上下标与 `^`／`~` 字形转换（被 `build_site.py` 引用） | 模块／CLI |
| `series_check.py` | 页面／锚／路线／资产／配图／print 门禁；`--selftest` 页面夹具回归 | 门禁（本地＋CI） |
| `route_lint.py` | 路线卡与正文引用断链审计 | 门禁（本地＋CI） |
| `route_js_check.py` | 路线层 JavaScript 与视图表对拍 | 门禁（本地） |
| `table_check.py` | Markdown 表格结构检查 | 门禁（本地＋CI） |
| `sentence_stats.py` | 句长／破折号密度测量；`--update` 刷基准表 | 测量 |
| `selftest_tools.py` | 工具自检总入口；默认跑新审阅工具，`--all` 追加核心工具 | 维护 |
| `prose_common.py` | 正文审阅共用切分/测量模块（被 section_map/coherence_scan/answer_mirror_check/prose_diff 引用） | 模块 |
| `reader_packet.py` | 冷读包生成：本章正文＋截至本章之前的术语；排除后文/答案/edit；`--selftest` | 手动 |
| `prose_diff.py` | 改动感知审阅：hunk＋前后段＋影响分类＋ripple 清单；`--since` 指定基线 | 测量 |
| `section_map.py` | 按 H2 输出段落/句长/节奏地图，供反向提纲；节级读数为相对比较，章级基准看 `sentence_stats` | 测量 |
| `coherence_scan.py` | 段首指代/上下文引用/孤岛术语/重复开头/超长段候选；`--max-orphans` 限条数 | 测量 |
| `logic_lint.py` | 语病/条件/二分/约数候选（L0/L1/L2；只定位，不判罚）；`--include-absolute` 才列绝对化 | 测量 |
| `consistency_scan.py` | 第N部/第N章/§N 指针、术语多释、数字台账 | 测量 |
| `phase01.py` | Phase 0/1 一键体检：logic_lint + consistency_scan + 可选 series_check；`--recall` 出机器面全量候选，`--coverage N` 出覆盖抽样单；报告写 `series/.tmp/phase01/` | 手动 |
| `answer_mirror_check.py` | 答案块数字/术语/引语回正文对账；数字比较归一化（3.20=3.2）；`--strict` 有候选退 1 | 测量 |
| `ripple_check.py` | 按改动类型跑涟漪检查；标“本章/全系列”，全系列默认只提示 | 手动 |
| `blind_pair.py` | 原文/改写随机 A/B 盲评表；`score` 读 votes/key 算胜率并可写 `review_log` | 手动 |
| `review_log.py` | 审阅裁决日志与接受率汇总（默认 `series/edit/review_log.tsv`） | 手动 |
| `row_check.py` | `style/句长基准.md` 与实测逐列对账 | 门禁（收尾链） |
| `first_use_scan.py` | 术语首现／总账核对；`--all --ledger-only --strict`；`--check-rules` | 门禁（收尾链＋CI） |
| `residue_scan.py` | 修复批残留模式复扫（EXPECT0；可传章文件限定） | 门禁（收尾链） |
| `metaphor_scan.py` | 喻体候选扫描；`--strict` 进收尾链 | 门禁（收尾链） |
| `reference_lint.py` | 跨章回指、旧词残留与“后文简称”承诺检查；`--strict` 进收尾链 | 门禁（收尾链） |
| `cliche_scan.py` | 套话词表扫描（只定位，不判罚） | 测量 |
| `taste_probe.py` | 品味层探针（S/F/C/Q/B/E 六节） | 测量 |
| `symbol_coverage.py` | 符号台账对查；`--strict` 有 FAIL 退出 1 | 门禁（收尾链） |
| `sync_public_data.py` | 从私有 `edit/` 导出公开 `data/`；`--check` 校验是否过期 | 维护（本地） |
| `apply_edits.py` | 断言式批量落文（锚全过才写） | 手动 |
| `unit_closeout.py` | 单章收尾取证：first_use／句长／残留／套话／品味；`--card` 加节地图/衔接/答案镜像 | 手动 |
| `finish_round.py` | 轮次收尾一条龙：改动章 → 总账/规则表 → 符号/表格/残留 → 四仪 → build 双跑；`--no-build` 快速循环 | 收尾链 |

## 常用命令

```bash
# 全量构建与读者面门禁
python3 series/tools/build_site.py
python3 series/tools/series_check.py
python3 series/tools/build_readme.py --check
python3 build/check_artifact_fresh.py

# 改稿收尾（有 edit 档案走档案，无档案走 --ledger-only）
python3 series/tools/finish_round.py --files "series/§0.3-这套读物怎么用？——路径、标记、环境与工具.md"
python3 series/tools/unit_closeout.py "series/§0.3-这套读物怎么用？——路径、标记、环境与工具.md"
python3 series/tools/unit_closeout.py "series/§0.3-这套读物怎么用？——路径、标记、环境与工具.md" --card

# 工具自检
python3 series/tools/selftest_tools.py
python3 series/tools/selftest_tools.py --all

# 改动感知审阅（候选态，不入硬门禁）
python3 series/tools/prose_diff.py "series/§N-….md" --since HEAD --context 2 --summary-only
python3 series/tools/section_map.py "series/§N-….md"
python3 series/tools/coherence_scan.py "series/§N-….md"
python3 series/tools/answer_mirror_check.py "series/§N-….md"
python3 series/tools/ripple_check.py "series/§N-….md" --type claim --run
python3 series/tools/blind_pair.py series/.tmp/§N.pairs.tsv
python3 series/tools/blind_pair.py score --votes series/.tmp/blind/§N/votes.tsv \
  --key series/.tmp/blind/§N/key.json --chapter "§N" --pass prose
python3 series/tools/review_log.py summary --chapter "§N"

# 单项
python3 series/tools/row_check.py
python3 series/tools/first_use_scan.py "series/§0.3-这套读物怎么用？——路径、标记、环境与工具.md" --ledger-only
python3 series/tools/first_use_scan.py --all --ledger-only --strict
python3 series/tools/first_use_scan.py --check-rules
python3 series/tools/reference_lint.py --strict
python3 series/tools/first_use_scan.py --all --ledger-only --no-context-exempt  # 审计：只认显式规则
python3 series/tools/residue_scan.py
python3 series/tools/sentence_stats.py "series/§0.3-这套读物怎么用？——路径、标记、环境与工具.md" --row
```

## 公开仓说明

公开仓没有 `edit/<章>.edit.md` 私有档案。`first_use_scan.py` 因此提供
`--ledger-only`：只对账公开的 `data/术语总账.tsv`，不查加粗术语、幽灵登记与 gloss；
这些检查需要本地档案，仅在档案存在时启用。
`finish_round.py` 有本地档案时走档案模式，否则走 `--ledger-only`，并跑一次
`--all --strict` 的总账硬门禁。公开数据由 `sync_public_data.py` 从私有台账导出，
本地有 `edit/术语总账.tsv` 时收尾链会顺带校验它是否最新。

### 术语扫描契约

- `首现章` ＝ 该词的**首次正式处理**（定义、机制或主责节），不是第一次字面出现。
- 更早出现的指针、支线预览、同字不同义、普通词、概念名，走
  `data/术语扫描规则.tsv` 显式登记；退役/旧称/已并条目自动跳过。
- 真正的「首现章＝本章但正文未现」和未豁免的「提前裸现」是 **ERROR**。
- 单字词（值、键、矩、谱、秩）不做自动首现判定，避免 `关键/值得/规矩/离谱`
  一类子串误报。
- 阅读顺序由 `profiles/chapters.json` 的 `parts` 顺序＋部内章数组顺序导出；
  同部内章顺序即阅读顺序，重排会改扫描顺序。profile 不可用时退回旧硬编码。
- 每次修订规则都要在规则表写理由；`--report` 看分类计数，`--explain`
  逐条看被豁免/跳过的判断，`--check-rules` 校验规则表本身；`--all --strict`
  必须 0 错。`--no-context-exempt` 关闭上下文自动豁免、只认显式规则，用于审计。

`series_check.py` 会检查本索引是否收全 `tools/*.py`；新增工具时记得补表。
