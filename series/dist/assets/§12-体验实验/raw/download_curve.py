# 取数脚本：从 OLMo-2-1124-7B 的 wandb 公开日志取 TriviaQA-wiki 评测交叉熵曲线
# 数据源：AI2 公开 wandb 项目 ai2-llm/OLMo-2-1124-7B（GraphQL 匿名只读）
# 口径：eval/downstream_ce_loss/trivia_qa_wiki_ppl_ce_loss，每约 1000 步评测一次
# 训练分两程：stage-1-run-10（~5k→414,526 步）＋ stage-1-run-11（415,001→928,646 步）
# 步→token 换算：4,194,304 token/步（= 4096 序列 × 1024 token，与 run 末态
# summary 值 3.8950e12 token @ 928,646 步逐位吻合，见首次运行记录.md）
# 零第三方依赖（仅标准库），任何人重跑可得同一份 CSV。
import json
import urllib.request

GRAPHQL = "https://api.wandb.ai/graphql"
ENTITY, PROJECT = "ai2-llm", "OLMo-2-1124-7B"
KEY = "eval/downstream_ce_loss/trivia_qa_wiki_ppl_ce_loss"
RUNS = ["awwjyi5w", "uwjy7cji"]          # stage-1-run-10 / run-11
TOKENS_PER_STEP = 4_194_304

def query(q):
    body = json.dumps({"query": q}).encode()
    req = urllib.request.Request(GRAPHQL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())

def main():
    points = {}
    for run in RUNS:
        q = ('query { project(name: "%s", entityName: "%s") '
             '{ run(name: "%s") { h: history(samples: 4000, maxKeyLimit: 40) } } }'
             % (PROJECT, ENTITY, run))
        d = query(q)
        rows = d["data"]["project"]["run"]["h"]
        n = 0
        for row_s in rows:
            row = json.loads(row_s)
            if KEY in row and "_step" in row:
                points[row["_step"]] = row[KEY]
                n += 1
        print("run %s: %d eval points" % (run, n))
    steps = sorted(points)
    with open("olmo2_7b_trivia_ce.csv", "w", encoding="utf-8") as f:
        f.write("step,tokens,trivia_qa_wiki_ce\n")
        for s in steps:
            f.write("%d,%d,%.9f\n" % (s, s * TOKENS_PER_STEP, points[s]))
    print("total: %d points, step %d -> %d, tokens %.4e -> %.4e"
          % (len(steps), steps[0], steps[-1],
             steps[0] * TOKENS_PER_STEP, steps[-1] * TOKENS_PER_STEP))

if __name__ == "__main__":
    main()
