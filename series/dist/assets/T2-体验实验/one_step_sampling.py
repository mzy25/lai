# -*- coding: utf-8 -*-
# T2 体验实验：手算一步采样（VP/DDPM 一步 + VE/Langevin 一步）
# 断言口径 = 对账记录 4a 复算链（中间值显示值闭合判例：显示值由精确值一次性舍入，
# 再按"显示值逐格重加"验证与正文显示值闭合）
# 旧版勘误：Langevin 链第二维 z 旧版排印 "[0.2, -1]" 应为 [0.2, -0.1]（支线符号总规 #13）

import math

def disp(v, nd=3):
    """显示口径：精确值一次性舍入到 nd 位小数（round-half-even 风险用格式化规避）"""
    return [float(f"{a:.{nd}f}") for a in v]

def approx(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))

fails = []
def check(name, got, want, tol):
    ok = approx(got, want, tol)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got={got} want={want} (tol={tol})")
    if not ok:
        fails.append(name)

# ---- 题面（照旧版 L277，σ_t=0.8 悬空已删——两个欧拉公式均不使用它）----
x_t = [1.0, 0.5]
s_theta = [-0.3, 0.4]
ds = 0.1          # 步长 Δs（支线符号总规 #6：不写作 η，η 是 §2 学习率）
eps = [0.2, -0.1]  # 旧版勘误后口径；正文记 ε（支线符号总规 #1：不立 z，撞 §3 logits）

# ---- (a)(b)(g) 漂移与分数贡献 ----
half_x = [0.5 * a for a in x_t]                      # ½x_t
check("a  ½x_t", half_x, [0.5, 0.25], 1e-12)

drift = [ds * a for a in half_x]                     # 漂移贡献 Δs·½x_t
score = [ds * a for a in s_theta]                    # 分数贡献 Δs·s_θ
check("g1 漂移贡献", drift, [0.05, 0.025], 1e-12)
check("g2 分数贡献", score, [-0.03, 0.04], 1e-12)

# ---- (c)(d) DDPM（VP）一步 ----
det_ddpm = [d + s for d, s in zip(drift, score)]     # 确定部分 Δs(½x_t+s_θ)
check("b  Δs(½x_t+s_θ)", det_ddpm, [0.02, 0.065], 1e-12)

noise1 = [math.sqrt(ds) * a for a in eps]              # √Δs·z 精确值
check("c  √Δs·ε 精确", noise1, [0.06324555320336758, -0.03162277660168379], 1e-12)
check("c  √Δs·ε 显示", disp(noise1), [0.063, -0.032], 5e-4)

final_ddpm = [x + d + n for x, d, n in zip(x_t, det_ddpm, noise1)]
print(f"     DDPM 末值精确: {final_ddpm}")
check("d  DDPM 末值精确", final_ddpm, [1.0832455532033676, 0.5333772233983162], 1e-12)
check("d  DDPM 末值显示", disp(final_ddpm), [1.083, 0.533], 1e-3)
# 铁律三：正文显示值按显示舍入值逐格重算闭合
recon = [1.0 + 0.02 + 0.063, 0.5 + 0.065 - 0.032]
check("d' 显示值逐格重加", recon, [1.083, 0.533], 1e-12)
# 贡献拆解对拍：三项之和 = 总增量（显示口径）
inc = [1.083 - 1.0, 0.533 - 0.5]
check("g3 三项和=总增量", [drift[0]+score[0]+0.063, drift[1]+score[1]-0.032], inc, 1e-12)

# ---- (e)(f) Langevin（VE）一步 ----
noise2 = [math.sqrt(2 * ds) * a for a in eps]          # √(2Δs)·z 精确值
check("e  √(2Δs)·ε 精确", noise2, [0.08944271909999159, -0.044721359549995794], 1e-12)
check("e  √(2Δs)·ε 显示", disp(noise2), [0.089, -0.045], 5e-4)

final_lang = [x + s + n for x, s, n in zip(x_t, score, noise2)]
print(f"     Langevin 末值精确: {final_lang}")
check("f  Langevin 末值精确", final_lang, [1.0594427190999916, 0.4952786404500042], 1e-12)
check("f  Langevin 末值显示", disp(final_lang), [1.059, 0.495], 1e-3)
recon2 = [1.0 - 0.03 + 0.089, 0.5 + 0.04 - 0.045]
check("f' 显示值逐格重加", recon2, [1.059, 0.495], 1e-12)

# ---- (h) 两法噪声对照 ----
print(f"     √Δs={math.sqrt(ds):.4f}  √(2Δs)={math.sqrt(2*ds):.4f}  "
      f"差 {(math.sqrt(2*ds)-math.sqrt(ds))/math.sqrt(ds)*100:.1f}%")
check("h  噪声系数对照", [round(math.sqrt(ds), 3), round(math.sqrt(2 * ds), 3)], [0.316, 0.447], 1e-3)
diff_pct = (math.sqrt(2 * ds) - math.sqrt(ds)) / math.sqrt(ds)
check("h  差 41%", [round(diff_pct, 2)], [0.41], 0.005)

# ---- 变式 ①：z' = [-0.2, 0.1]（符号翻转）----
eps_p = [-0.2, 0.1]
f1 = [x + d + math.sqrt(ds) * n for x, d, n in zip(x_t, det_ddpm, eps_p)]
f2 = [x + s + math.sqrt(2 * ds) * n for x, s, n in zip(x_t, score, eps_p)]
print(f"     变式① DDPM={f1} Langevin={f2}")

# ---- 变式 ②：步长 0.1 → 0.01（漂移/分数贡献 ×0.1；噪声幅度 ×1/√10 ≈ 0.316）----
ds2 = 0.01
det2 = [ds2 * (hx + s) for hx, s in zip(half_x, s_theta)]
g1 = [x + d + math.sqrt(ds2) * n for x, d, n in zip(x_t, det2, eps)]
g2 = [x + ds2 * s + math.sqrt(2 * ds2) * n for x, s, n in zip(x_t, s_theta, eps)]
print(f"     变式② DDPM={g1} Langevin={g2}")
check("② 噪声项新幅度", [math.sqrt(ds2) * eps[0]], [0.02], 1e-12)
check("② 噪声幅度比 = 1/√10", [math.sqrt(ds2) / math.sqrt(ds)], [1 / math.sqrt(10)], 1e-12)

# ---- 变式 ③：z = 0（只去随机项，ODE 一步的纸面预习）----
h1 = [x + d for x, d in zip(x_t, det_ddpm)]
h2 = [x + s for x, s in zip(x_t, score)]
print(f"     变式③ ε=0: DDPM={h1} Langevin={h2}")

print()
if fails:
    print(f"断言失败 {len(fails)} 项: {fails}")
    raise SystemExit(1)
print("全部断言通过（exit 0）")
