# GRPO 群组优势手算验证：8 个回答的规则验证奖励 R=[1,0,1,0,0,1,0,0]
# 按"组内比高低"口径复算 mean/std/Â，与对账记录 4a（旧版基座 L524–535）逐格对账。
import numpy as np

R = np.array([1, 0, 1, 0, 0, 1, 0, 0])   # 对=1，错=0；同一道题采的一组回答
N = R.size
mean = R.sum() / N                       # 手算第一步：3/8 = 0.375
var = ((R - mean) ** 2).sum() / N        # 手算第二步：1.875/8 = 0.234375（除以 N，不是 N−1）
std = np.sqrt(var)                       # 总体 std ≈ 0.484（样本口径 0.517 对不上正文表）
A = (R - mean) / std                     # 手算第三步：Â_i = (R_i − mean) / std

print(f'N = {N} 个回答, R = {R.tolist()}, 答对 {int(R.sum())} 个')
print(f'mean = {R.sum()}/{N} = {mean:.6f}')
print(f'方差 = 1.875/{N} = {var:.6f},  std(总体, ÷N) = {std:.6f}'
      f'  （对照：样本 std ÷N−1 = {R.std(ddof=1):.6f}，正文不采此口径）')
print('\n逐样本对账表（手算 Â vs 笔记值）')
print(f'{"样本":<6}{"R":>3}{"R−mean":>10}{"Â(手算)":>12}{"笔记":>8}')
print('-' * 41)
for i in range(N):
    print(f'{i+1:<6}{R[i]:>3}{R[i]-mean:>10.3f}{A[i]:>12.2f}'
          f'{( "+1.29" if R[i] == 1 else "-0.77"):>8}')
print('-' * 41)

expected = np.array([1.29, -0.77, 1.29, -0.77, -0.77, 1.29, -0.77, -0.77])
assert abs(mean - 0.375) < 1e-9 and abs(std - 0.4841) < 1e-3
assert np.all(np.abs(np.round(A, 2) - expected) < 0.01)   # 容差 0.01，容四舍五入
print('对账: mean/std/Â 与笔记 4a 逐格一致 → PASS')

for name, R0 in [('全对组', np.ones(8)), ('全错组', np.zeros(8))]:
    s0 = R0.std()                        # 全同奖励 → std = 0
    with np.errstate(invalid='ignore'):  # 0/0 = nan 是预期结果，屏蔽告警
        A0 = (R0 - R0.mean()) / s0       # 无定义：组内没有可比对象，跳过该组
    print(f'{name}: std = {s0:.1f}, Â = {A0[0]}（nan = 无定义，跳过该组）')
