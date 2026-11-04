# series/data（公开构建数据）

本目录是公开构建与 CI 的输入，随公开仓提交。`series/edit/` 是本地编辑档案
（完整台账、术语提案、审读报告），整体不随公开仓提交。

| 文件 | 用途 |
|---|---|
| `术语总账.tsv` | `terms.html` 与章末“本章新词”；备注已清洗 |
| `符号台账.tsv` | `symbol_coverage` 门禁所需字段 |
| `术语扫描规则.tsv` | `first_use_scan` 的指针/预览/多义/退役规则 |
| `引用一致性.tsv` | `reference_lint` 的旧词→新词规则 |

只读，不要手改。更新私有台账后运行：

```bash
python3 series/tools/sync_public_data.py
python3 series/tools/sync_public_data.py --check
```

`finish_round.py` 在本地存在 `series/edit/术语总账.tsv` 时会自动跑 `--check`。
