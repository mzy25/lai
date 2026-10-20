# T1 动手节对拍脚本：手算加噪 + 混合高斯分数（铁律三：正文显示值按显示舍入值逐格闭合）
# 断言链照 edit/T1.素材挖掘笔记.md 第 4 节数字总账（4a/4c 口径）
import numpy as np

ok = []
def check(name, cond):
    assert cond, f"FAIL: {name}"
    ok.append(name)

# (a) t=2 闭式跳步 vs 逐步加噪对拍（ch1 L64-72 展开验证）
a1, a2 = 0.9, 0.8
x0 = 2.0
rng = np.random.default_rng(7)
E = rng.normal(size=(200000, 2))
x_two_step = np.sqrt(a2) * (np.sqrt(a1) * x0 + np.sqrt(1 - a1) * E[:, 0]) + np.sqrt(1 - a2) * E[:, 1]
abar2 = a1 * a2
# 闭式：x2 = √ᾱ₂·x0 + (√a₂√(1−a₁)·ε₁ + √(1−a₂)·ε₂)，括号内仍是高斯（独立高斯之和）
x_closed = np.sqrt(abar2) * x0 + E @ np.array([np.sqrt(a2) * np.sqrt(1 - a1), np.sqrt(1 - a2)])
check("t=2 闭式=逐步(轨迹)", np.allclose(x_two_step, x_closed))
check("方差闭合 a2(1-a1)+(1-a2)=1-a1a2", abs(a2*(1-a1)+(1-a2) - (1-abar2)) < 1e-12)

# (b) 正文 1D 手算加噪（ch1 L262-268 版，显示值逐格闭合）
r = lambda v: round(v, 3)
check("√0.3×2.0≈1.095", r(np.sqrt(0.3)*2.0) == 1.095)
check("√0.7×0.5≈0.418", r(np.sqrt(0.7)*0.5) == 0.418)
check("1.095+0.418=1.513", r(1.095+0.418) == 1.513)
check("幅度口径 缩小约45%", abs(1 - np.sqrt(0.3) - 0.45) < 0.01)

# (c) 动手题面 sec3.4 两步版（两行独立：x1 单步、x2 闭式另取 ε_eq=1.5；显示链逐格闭合）
check("√0.9×2.0≈1.897", r(np.sqrt(0.9)*2.0) == 1.897)
check("√0.1×0.5≈0.158", r(np.sqrt(0.1)*0.5) == 0.158)
check("x1≈2.055 显示链 1.897+0.158", r(1.897+0.158) == 2.055 and r(np.sqrt(0.9)*2.0+np.sqrt(0.1)*0.5) == 2.055)
check("x1 精确 2.0554", abs(np.sqrt(0.9)*2.0+np.sqrt(0.1)*0.5 - 2.0554) < 1e-3)
check("√0.8×2.0≈1.789", r(np.sqrt(0.8)*2.0) == 1.789)
check("√0.2×1.5≈0.671", r(np.sqrt(0.2)*1.5) == 0.671)
check("x2≈2.460 显示链 1.789+0.671", r(1.789+0.671) == 2.460 and r(np.sqrt(0.8)*2.0+np.sqrt(0.2)*1.5) == 2.460)
check("x2 精确 2.4597", abs(np.sqrt(0.8)*2.0+np.sqrt(0.2)*1.5 - 2.4597) < 1e-3)
check("终点 ᾱ=0.01: 0.2+0.995ε", r(np.sqrt(0.01)*2.0) == 0.2 and r(np.sqrt(0.99)) == 0.995)

# (d) 2D 双峰表 VP 连续口径（ch1 L270-278）
check("t=1: a≈0.61 σ≈0.79", r(np.exp(-0.5)) == 0.607 and r(np.sqrt(1-np.exp(-1))) == 0.795)
check("t=5: a≈0.08 σ≈0.996", r(np.exp(-2.5)) == 0.082 and r(np.sqrt(1-np.exp(-5))) == 0.997)
check("表内显示链: 1-0.37=0.63 √0.63≈0.79", r(1-round(np.exp(-1),2)) == 0.63 and r(np.sqrt(0.63)) == 0.794)
check("表内显示链: e^-5≈0.007, 1-0.007=0.993, √0.993≈0.996",
      round(np.exp(-5),3) == 0.007 and r(1-0.007) == 0.993 and r(np.sqrt(0.993)) == 0.996)

# (e) 混合高斯分数（ch2 L160-184）
def logp(x):
    return np.log(0.5*np.exp(-(x-2)**2/0.5) + 0.5*np.exp(-(x+2)**2/0.5))
def score_fd(x, h=1e-5):
    return (logp(x+h)-logp(x-h))/(2*h)
check("s(0)=0(奇对称)", abs(score_fd(0.0)) < 1e-6)
check("s(1.5)≈2.0", abs(score_fd(1.5) - 2.0) < 1e-3)
check("e^-0.5 vs e^-24.5 比值 e^24≈2.65e10", r(np.exp(-0.5)/np.exp(-24.5)) == r(np.exp(24)) and r(np.exp(24)) == 26489122.0 or abs(np.exp(24)-2.65e10)/2.65e10 < 0.001)
check("(2-1.5)/0.25=2.0", (2-1.5)/0.25 == 2.0)

# (f) Tweedie δ 验证反推闭合（ch2 L174-184）
a_t, sig2 = 0.5, 0.75
sig = np.sqrt(sig2)
X0, eps = 2.0, 0.3
Xt = a_t*X0 + sig*eps
s = (a_t*X0 - Xt)/sig2
check("X_t≈1.260", r(Xt) == 1.260 and r(0.5*2.0 + r(0.866*0.3)) == 1.260)
check("s≈-0.347", r((1.0-1.260)/0.75) == -0.347 and r(s) == -0.346)
check("反推 显示链 -0.866×(-0.347)≈0.301", r(-0.866*(-0.347)) == 0.301)
check("反推 精确 -σ·s=0.300", r(-sig*s) == 0.300)

# (i) 数据流形开场像素数（ch2 L21 口径：1024×1024×3≈300 万，冷审 v1.1 补断言）
check("1024×1024×3≈315万（正文『300 多万』）", 1024*1024*3 == 3145728 and round(1024*1024*3/1e4, 1) == 314.6)

# (g) InfoNCE 手算（sec3.4 L18-28，F25 兑付数字）
sims = np.array([0.9, 0.5, 0.1]); ex = np.exp(sims)
Z, p_pos = ex.sum(), ex[0]/ex.sum()
check("Z≈5.22 显示链 2.46+1.65+1.11", r(2.46+1.65+1.11) == 5.22 and abs(Z-5.2135) < 1e-3)
check("p+≈0.47 显示链 2.46/5.22", r(2.46/5.22) == 0.471 and abs(p_pos-0.4718) < 1e-3)
check("损失 -ln(0.47)≈0.75", r(-np.log(0.47)) == 0.755 and abs(-np.log(p_pos)-0.7513) < 1e-3)

# (h) Langevin 反向手算画面（sec3.4 L68-74，η→Δs=0.5）
Ds = 0.5; x99 = 0.2 + Ds/2*1.8 + np.sqrt(Ds)*0.3
x98 = x99 + Ds/2*(2-x99) + np.sqrt(Ds)*(-0.1)
check("x99≈0.86 显示链 0.2+0.45+0.21", r(0.2+0.45+0.21) == 0.86 and r(x99) == 0.862)
check("x98≈1.08 显示链 0.86+0.29-0.07", r(0.86+0.29-0.07) == 1.08 and r(x98) == 1.076)

print(f"全部 {len(ok)} 项断言 PASS")
for n in ok: print(" PASS", n)
