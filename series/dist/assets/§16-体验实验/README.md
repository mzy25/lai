# §16 六站实验资产

- 依赖：Python 3.11 以上；`pip install smolagents`（开发机实测 smolagents 1.26.0 / Python 3.13）。
- 运行：`python3 station1.py` … `python3 station5.py`，逐站跑；零 API key（假模型按剧本逐句回复）。
- 文件：station1–5.py（五站脚本）、mock_model.py（假模型）、my_harness.py（第五站骨架参考实现）、
  run_log.txt / run_log_正式.txt（运行记录与对账）。
- 说明：正文检查点与脚本输出逐字对应；第五站含一处参数解析的最小修正，理由见运行记录。
