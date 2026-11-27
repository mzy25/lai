# series/data（公开构建数据）

本目录是公开构建与 CI 的输入，随公开仓提交。`series/edit/` 是本地编辑档案
（首现登记、审读报告），整体不随公开仓提交。

| 文件 | 用途 |
|---|---|
| `术语总账.tsv` | `terms.html` 与章末“本章新词”；备注已清洗 |
| `符号台账.tsv` | `symbol_coverage` 门禁所需字段 |
| `术语扫描规则.tsv` | `first_use_scan` 的指针/预览/多义/退役规则 |
| `引用一致性.tsv` | `reference_lint` 的旧词→新词规则 |

本目录是台账唯一来源：直接编辑对应 TSV，然后跑门禁：

```bash
python3 series/tools/first_use_scan.py --all --ledger-only --strict
python3 series/tools/symbol_coverage.py --strict
python3 series/tools/reference_lint.py --strict
```

`finish_round.py` 会全量跑上述门禁。
