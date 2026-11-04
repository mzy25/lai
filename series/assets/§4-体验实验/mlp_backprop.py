# MLP 全推 + 梯度检查：3→4→2 微型网络，手写前向、手写反向、数值对账
# 只做一件事：验证"我手推的反向传播公式"和"计算机 brute-force 算的梯度"完全一致。
import numpy as np

rng = np.random.default_rng(0)   # 固定种子：任何人重跑，数字逐字相同

# ---------- 初始化 ----------
# 网络：输入 3 维 → 隐藏 4 个神经元（tanh）→ 输出 2 类（softmax）
# 参数共 26 个 = W1(3×4=12) + b1(4) + W2(4×2=8) + b2(2)
W1 = rng.normal(0, 0.5, (3, 4))  # 第一层权重：每条"输入→隐藏"连线一个数
b1 = np.zeros(4)                 # 第一层偏置：每个隐藏神经元一个"起手值"
W2 = rng.normal(0, 0.5, (4, 2))  # 第二层权重：每条"隐藏→输出"连线一个数
b2 = np.zeros(2)                 # 第二层偏置

x = np.array([0.5, -0.3, 0.8])   # 输入样本：3 个数
y = np.array([0.0, 1.0])         # 真实标签：one-hot，意思是"正确答案是第 2 类"
print(f'参数量: W1 {W1.size} + b1 {b1.size} + W2 {W2.size} + b2 {b2.size} = '
      f'{W1.size + b1.size + W2.size + b2.size} 个')

# ---------- 前向传播 ----------
def forward(x, W1, b1, W2, b2):
    z1 = x @ W1 + b1             # 第一步：每个隐藏神经元 = 3 个输入各乘权重再相加，加偏置
    a1 = np.tanh(z1)             # 第二步：tanh 激活，把任意实数压进 (-1,1)，引入非线性
    z2 = a1 @ W2 + b2            # 第三步：输出层同样的加权求和
    e = np.exp(z2 - z2.max())    # 第四步：softmax，先指数化（减去最大防爆数）
    p = e / e.sum()              #        再除以总和，两个输出变成和为 1 的概率
    return z1, a1, z2, p

def loss(p, y):
    return -np.log(p[y.argmax()])  # 交叉熵：只看正确类别那个概率，取负对数

z1, a1, z2, p = forward(x, W1, b1, W2, b2)
L = loss(p, y)
print(f'\n前向结果: 输出概率 p = [{p[0]:.6f}, {p[1]:.6f}]（和={p.sum():.6f}）')
print(f'损失 L = -ln(p[正确类别]) = {L:.6f}')

# ---------- 反向传播（链式法则，一步一格，和公式推导一一对应） ----------
# 公式推导顺序：L → z2 → (W2,b2) 和 a1 → z1 → (W1,b1)
dz2 = p - y                      # ① softmax+交叉熵合起来的导数：预测概率 − 真实标签
dW2 = np.outer(a1, dz2)          # ② L 对 W2 的梯度 = 上游信号 dz2 × 本层输入 a1（外积：列×行）
db2 = dz2.copy()                 # ③ L 对 b2 的梯度 = 上游信号（偏置的输入恒为 1）
da1 = W2 @ dz2                   # ④ 误差沿连线回流：L 对隐藏层输出 a1 的梯度
dz1 = da1 * (1 - a1 ** 2)        # ⑤ 穿过 tanh：乘它的导数 1−a1²（a1 就是 tanh 的输出，直接可用）
dW1 = np.outer(x, dz1)           # ⑥ L 对 W1 的梯度 = 上游信号 dz1 × 本层输入 x
db1 = dz1.copy()                 # ⑦ L 对 b1 的梯度 = 上游信号

grads = {'W1': dW1, 'b1': db1, 'W2': dW2, 'b2': db2}

# ---------- 数值梯度（有限差分法：不靠任何公式，纯粹"捏一捏"看损失变化） ----------
# 中心差分：把参数 θ 先加一点点再减一点点，损失差除以 2ε 就是斜率
EPS = 1e-5
num_grads = {}
for name, W in [('W1', W1), ('b1', b1), ('W2', W2), ('b2', b2)]:
    g = np.zeros_like(W)
    it = np.nditer(W, flags=['multi_index'])
    while not it.finished:
        idx = it.multi_index
        old = W[idx]
        W[idx] = old + EPS
        lp = loss(forward(x, W1, b1, W2, b2)[3], y)   # θ+ε 的损失
        W[idx] = old - EPS
        lm = loss(forward(x, W1, b1, W2, b2)[3], y)   # θ−ε 的损失
        W[idx] = old
        g[idx] = (lp - lm) / (2 * EPS)                # 斜率 = 损失变化量 / 参数变化量
        it.iternext()
    num_grads[name] = g

# ---------- 逐参数对账 ----------
# 相对误差 = |解析 − 数值| ÷ (|解析| + |数值|)，双方面都接近 0 时也能给出合理读数
print('\n逐参数对账表（解析梯度 vs 数值梯度）')
print(f'{"参数":<8}{"解析梯度":>14}{"数值梯度":>14}{"相对误差":>13}')
print('-' * 51)
max_err = 0.0
for name in ['W1', 'b1', 'W2', 'b2']:
    for idx, _ in np.ndenumerate(grads[name]):
        a, n = grads[name][idx], num_grads[name][idx]
        err = abs(a - n) / (abs(a) + abs(n) + 1e-30)
        max_err = max(max_err, err)
        print(f'{name}{idx!s:<5}{a:>14.8f}{n:>14.8f}{err:>13.3e}')
print('-' * 51)
print(f'26 个参数中最大相对误差: {max_err:.3e}')
print(f'判定: 全部 < 1e-5 → {"PASS" if max_err < 1e-5 else "FAIL"}')
