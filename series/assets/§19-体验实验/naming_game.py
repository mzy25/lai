#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""naming_game.py —— 命名游戏（§19 外延节配对脚本，无第三方依赖）

经典命名游戏（Steels 1995）的简化版：群体要给一批"事物"起名字，开局没有任何公共词表。
- 24 个智能体、8 件事物；每个智能体对每件事物记住一个词（开局为空）。
- 每轮随机挑两个智能体与一件事物：说的人有词就说出、没词就现造；听的人没词就学会，
  词不一样就把自己那页改成对方的。
- 读数：全群体达成"每件事物只剩 1 个词"所需轮数、累计造词数、每件事物的胜出词。
- 对照 A（切断交互）：每个智能体只自造自记、从不互学——词聚不拢。
- 对照 B（发公共词表）：开局所有智能体持同一套词——第 0 轮即"一致"，但没有相互作用。

运行：python3 naming_game.py
"""
import random

N, K = 24, 8          # 智能体数、事物数
SEED_SWEEP = (1, 2, 3, 4, 5)


def run(seed=7, mode="interact", rounds_cap=200000):
    rng = random.Random(seed)
    vocab = [[None] * K for _ in range(N)]
    counter = [0]

    def invent():
        counter[0] += 1
        return "w%d" % counter[0]

    if mode == "shared":                      # 对照 B：开局发同一张词表
        vocab = [["w%d" % (o + 1) for o in range(K)] for _ in range(N)]

    def converged():
        for o in range(K):
            words = {vocab[i][o] for i in range(N)}
            if len(words) != 1 or None in words:
                return False
        return True

    if mode == "solo":                        # 对照 A：只自造、从不互学
        for _ in range(100000):
            if all(vocab[i][o] is not None for i in range(N) for o in range(K)):
                break
            i, o = rng.randrange(N), rng.randrange(K)
            if vocab[i][o] is None:
                vocab[i][o] = invent()
        distinct = [len({vocab[i][o] for i in range(N)}) for o in range(K)]
        return None, counter[0], [vocab[0][o] for o in range(K)], distinct

    for r in range(rounds_cap + 1):           # 交互组／对照 B
        if converged():
            winners = [vocab[0][o] for o in range(K)]
            return r, counter[0], winners, None
        if mode == "shared":                  # 发公共词表：不做任何事
            continue
        i, j = rng.sample(range(N), 2)
        o = rng.randrange(K)
        wi = vocab[i][o]
        if wi is None:
            wi = invent()
            vocab[i][o] = wi
        wj = vocab[j][o]
        if wj is None:
            vocab[j][o] = wi
        elif wj != wi:
            vocab[j][o] = wi
    return None, counter[0], None, None       # 未在上限内收敛


if __name__ == "__main__":
    rc, made, winners, _ = run(7)
    print("命名游戏（24 个智能体、8 件事物；交互组，种子 7）")
    print("全群体收敛轮数：%s｜累计造词：%d" % (rc, made))
    print("胜出词：" + " ".join(winners))

    print()
    print("换种子对照（同一套规则、不同历史）：")
    winner_table = {}
    for s in SEED_SWEEP:
        rc_s, made_s, win_s, _ = run(s)
        winner_table[s] = win_s
        print("  种子 %d：收敛 %s 轮、造词 %d、胜出 %s" % (s, rc_s, made_s, " ".join(win_s)))
    diff_all = sum(
        1
        for o in range(K)
        if len({winner_table[s][o] for s in SEED_SWEEP}) > 1
    )
    print("  五种子合并：%d/%d 件事物的胜出词随种子改变" % (diff_all, K))

    print()
    rcA, madeA, winA, distinctA = run(7, mode="solo")
    print("对照 A（切断交互）：收敛 %s（不收敛）｜各事物词数 %s" % (rcA, distinctA))
    rcB, madeB, winB, _ = run(7, mode="shared")
    print("对照 B（发公共词表）：第 %s 轮即一致｜造词 %d" % (rcB, madeB))
