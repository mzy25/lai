# 梯度下降学习率轨迹实验：对 f(x)=x^2 从 x0=3 出发
import numpy as np
import matplotlib.pyplot as plt

# 中文字体：按环境自动挑选（Windows 用微软雅黑，Colab 用 Noto Sans CJK）
from matplotlib import font_manager
avail = {f.name for f in font_manager.fontManager.ttflist}
cjk = [f for f in ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC',
                   'Noto Sans CJK JP', 'WenQuanYi Micro Hei'] if f in avail]
plt.rcParams['font.sans-serif'] = cjk + plt.rcParams['font.sans-serif']
plt.rcParams['axes.unicode_minus'] = False

X0, N = 3.0, 250          # 起点与步数；f=x^2 的梯度是 2x，曲率 L=2
etas = [0.01, 0.3, 0.5, 1.0]

plt.figure(figsize=(9, 5.5))
for eta in etas:
    x = X0
    track = [1.0]                                   # 第 0 步 f/f0
    for step in range(1, N + 1):
        x = x - eta * 2 * x                         # 梯度下降一步
        track.append(x ** 2 / X0 ** 2)
    cross = next((i for i, v in enumerate(track) if v < 1e-3), None)
    print(f'η={eta:<4} 到千分之一步数: {cross}')
    plt.semilogy(track, label=f'η={eta}')

plt.ylim(1e-7, 10)
plt.axhline(1e-3, ls='--', c='gray', lw=1, label='1/1000 参考线')
plt.annotate('η=0.5：一步到碗底 (x1=0)', xy=(1, 1e-7), xytext=(6, 3e-6),
             fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
plt.annotate('η=0.3：第 4 步穿线', xy=(4, 2.4e-4), xytext=(10, 2e-5),
             fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
plt.annotate('η=0.01：第 171 步穿线', xy=(171, 9.6e-4), xytext=(185, 1e-4),
             fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
plt.annotate('η=1.0：在 ±3 间永久震荡，f/f0 恒为 1', xy=(200, 1.0), xytext=(110, 2.5),
             fontsize=9, arrowprops=dict(arrowstyle='->', lw=0.8))
plt.xlabel('步数'); plt.ylabel('f/f0（对数刻度）')
plt.title('学习率决定梯度下降的命运：f(x)=x²，x0=3')
plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
plt.savefig('lr_tracks.png', dpi=150)

# 专项验证：η=1.0 是否永久震荡，η=0.5 是否一步到底
x = X0
seq1 = [x := x - 1.0 * 2 * x for _ in range(6)]
print('η=1.0 前 6 步 x 轨迹:', seq1, '→ 在 3 与 -3 之间震荡' if all(abs(v) == 3 for v in seq1) else '')
x = X0
x1 = x - 0.5 * 2 * x
print(f'η=0.5 一步后 x1={x1}，f/f0={x1**2/X0**2:.0e} → 一步到碗底')
