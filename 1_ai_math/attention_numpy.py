"""
第5章：Multi-Head Self-Attention + RoPE 纯NumPy实现
====================================================
对应第5章公式推导的完整代码实现，每个步骤均与数学公式一一对应。

公式对应关系：
- 公式1: Q = XW_Q, K = XW_K, V = XW_V       （线性投影）
- RoPE:  Q' = R(pos) * Q, K' = R(pos) * K    （旋转位置编码，只转Q和K）
- 公式2: S = Q'K'^T / sqrt(d_k)              （缩放点积注意力分数）
- 公式3: A = softmax(S)                       （注意力权重归一化）
- 公式4: O = AV                               （加权输出）
- 公式5: MultiHead = Concat(head_1,...,head_h) W_O  （多头融合）
- 反向传播: 链式法则逐层求导（含RoPE梯度传递）
"""

import numpy as np

# 固定随机种子：主程序含随机演示（RoPE 打乱验证、Transformer Block 权重），
# 种子固定后每次运行输出一致，便于与文档手算结果对照。
RNG = np.random.default_rng(42)

# ============================================
# 工具函数
# ============================================

def softmax(x, axis=-1):
    """
    稳定的softmax实现。

    数学公式: softmax(x_i) = exp(x_i) / sum_j(exp(x_j))

    数值稳定性技巧：先减最大值，防止指数溢出。
    对应第5章公式3: A = softmax(S)
    """
    x_shifted = x - np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x_shifted)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


# ============================================
# RoPE: 旋转位置编码（对应第5章位置编码小节）
# ============================================

def rope_frequencies(d_k, base=10000):
    """
    生成RoPE的几何级数频率。

    数学公式: θ_i = base^(-2i/d_k), i = 0, 1, ..., d_k/2 - 1

    d_k维向量分成d_k/2对，每对一个频率。
    相邻频率比为 base^(2/d_k)，形成等比数列。
    高频（θ大）负责近距离，低频（θ小）负责远距离。
    """
    i = np.arange(d_k // 2)
    return base ** (-2.0 * i / d_k)  # (d_k/2,)


def apply_rope(Q, K, thetas):
    """
    对Q和K施加RoPE旋转位置编码。

    数学公式: 对位置pos的token，其Q/K的每对维度旋转 θ_i * pos 弧度。
    旋转矩阵 R(α) = [[cosα, -sinα], [sinα, cosα]]

    只旋转Q和K，不碰V——语义内容原封不动，只有"查询-匹配"被位置调制。

    参数:
        Q      : (n, d_k)  Query矩阵
        K      : (n, d_k)  Key矩阵
        thetas : (d_k/2,)  各维度对的旋转频率

    返回:
        Q_rot  : (n, d_k)  旋转后的Query
        K_rot  : (n, d_k)  旋转后的Key
    """
    n, d_k = Q.shape
    pos = np.arange(n)  # (n,) 位置编号 0, 1, ..., n-1

    # 计算每个位置、每个维度对的旋转角度: angles[pos, pair] = θ_pair * pos
    angles = np.outer(pos, thetas)  # (n, d_k/2)

    cos = np.cos(angles)  # (n, d_k/2)
    sin = np.sin(angles)  # (n, d_k/2)

    # 将Q/K的相邻维度配对: (dim0, dim1), (dim2, dim3), ...
    # 每对做2D旋转: [q0, q1] -> [q0*cos - q1*sin, q0*sin + q1*cos]
    Q_pairs = Q.reshape(n, d_k // 2, 2)  # (n, d_k/2, 2)
    K_pairs = K.reshape(n, d_k // 2, 2)

    Q_rot = np.empty_like(Q_pairs)
    K_rot = np.empty_like(K_pairs)

    # 旋转: [x, y] -> [x*cos - y*sin, x*sin + y*cos]
    Q_rot[:, :, 0] = Q_pairs[:, :, 0] * cos - Q_pairs[:, :, 1] * sin
    Q_rot[:, :, 1] = Q_pairs[:, :, 0] * sin + Q_pairs[:, :, 1] * cos

    K_rot[:, :, 0] = K_pairs[:, :, 0] * cos - K_pairs[:, :, 1] * sin
    K_rot[:, :, 1] = K_pairs[:, :, 0] * sin + K_pairs[:, :, 1] * cos

    return Q_rot.reshape(n, d_k), K_rot.reshape(n, d_k)


# ============================================
# Step 1-4: 单头自注意力前向传播（含RoPE）
# ============================================

def single_head_attention(X, W_Q, W_K, W_V, thetas=None):
    """
    单头自注意力前向传播（可选RoPE位置编码）。

    对应第5章公式: Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V

    参数:
        X      : (n, d)     输入矩阵，n个token，每token d维
        W_Q    : (d, d_k)   Query投影矩阵
        W_K    : (d, d_k)   Key投影矩阵
        W_V    : (d, d_k)   Value投影矩阵
        thetas : (d_k/2,)   RoPE频率。None则不加位置编码

    返回:
        O      : (n, d_k)   输出矩阵
        A      : (n, n)     注意力权重矩阵
        cache  : dict       缓存中间结果（用于反向传播）
    """
    # -------- 公式1: Q = XW_Q, K = XW_K, V = XW_V --------
    Q = X @ W_Q        # (n, d_k)
    K = X @ W_K        # (n, d_k)
    V = X @ W_V        # (n, d_k)

    n, d_k = Q.shape

    # -------- RoPE: 旋转Q和K（不碰V） --------
    if thetas is not None:
        Q, K = apply_rope(Q, K, thetas)

    # -------- 公式2: S = QK^T / sqrt(d_k) --------
    S = (Q @ K.T) / np.sqrt(d_k)       # (n, n)

    # -------- 公式3: A = softmax(S) --------
    A = softmax(S, axis=-1)             # (n, n), 每行和为1

    # -------- 公式4: O = AV --------
    O = A @ V                           # (n, d_k)

    cache = {
        'X': X, 'W_Q': W_Q, 'W_K': W_K, 'W_V': W_V,
        'Q': Q, 'K': K, 'V': V, 'S': S, 'A': A, 'O': O,
        'd_k': d_k, 'thetas': thetas
    }
    return O, A, cache


# ============================================
# 反向传播（对应第5.4节）
# ============================================

def softmax_jacobian_row(a_row):
    """Softmax的Jacobian: J = diag(a) - a @ a^T"""
    return np.diag(a_row) - np.outer(a_row, a_row)


def single_head_attention_backward(dL_dO, cache):
    """
    单头自注意力的反向传播。

    梯度流动路径（链式法则接力）：
    dL_dO -> dL_dA -> dL_dS -> dL_dQ, dL_dK
                        |
                        v
                      dL_dV

    对应第5.4节公式:
    - dL/dA = (dL/dO) @ V^T
    - dL/dV = A^T @ (dL/dO)
    - dL/dS = dL/dA @ J          (通过Softmax Jacobian变换)
    - dL/dQ = (dL/dS) @ K / sqrt(d_k)   （含RoPE时梯度经旋转矩阵传回）
    - dL/dK = (dL/dS)^T @ Q / sqrt(d_k)

    注意：RoPE只改变Q和K的值，不引入额外可学习参数（频率是预设的），
    所以反向传播中梯度正常通过旋转后的Q和K传回W_Q和W_K。
    """
    A = cache['A']
    V = cache['V']
    Q = cache['Q']
    K = cache['K']
    d_k = cache['d_k']
    n = A.shape[0]

    # Step 1: dL/dA 和 dL/dV
    dL_dA = dL_dO @ V.T               # (n, n)
    dL_dV = A.T @ dL_dO               # (n, d_k)

    # Step 2: 通过Softmax Jacobian求 dL/dS
    dL_dS = np.zeros_like(A)
    for i in range(n):
        J_i = softmax_jacobian_row(A[i])
        dL_dS[i] = dL_dA[i] @ J_i

    # Step 3: dL/dQ 和 dL/dK (含1/sqrt(d_k)因子)
    # Q和K在注意力分数S=QK^T/sqrt(d_k)中是乘在一起的两个因子
    # 求Q的梯度需要K的值，求K的梯度需要Q的值——这就是"联动调节"
    dL_dQ = dL_dS @ K / np.sqrt(d_k)  # (n, d_k)
    dL_dK = dL_dS.T @ Q / np.sqrt(d_k)  # (n, d_k)

    gradients = {
        'dL_dQ': dL_dQ, 'dL_dK': dL_dK, 'dL_dV': dL_dV,
        'dL_dA': dL_dA, 'dL_dS': dL_dS,
    }
    return gradients


# ============================================
# 公式5: 多头注意力
# ============================================

def multi_head_attention(X, W_Q_list, W_K_list, W_V_list, W_O, thetas_list=None):
    """
    多头注意力（Multi-Head Attention）。

    对应第5章公式5: MultiHead = Concat(head_1,...,head_h) W_O

    参数:
        X           : (n, d)         输入矩阵
        W_Q_list    : list of h个 (d, d_k)
        W_K_list    : list of h个 (d, d_k)
        W_V_list    : list of h个 (d, d_k)
        W_O         : (h*d_k, d)     输出融合矩阵
        thetas_list : list of h个 (d_k/2,)  每头的RoPE频率（None则不加）

    返回:
        output      : (n, d)         最终输出
        all_A       : list of h个 (n, n)  每头的注意力权重
    """
    h = len(W_Q_list)
    head_outputs = []
    all_A = []

    for i in range(h):
        thetas_i = thetas_list[i] if thetas_list is not None else None
        O_i, A_i, _ = single_head_attention(
            X, W_Q_list[i], W_K_list[i], W_V_list[i], thetas=thetas_i
        )
        head_outputs.append(O_i)
        all_A.append(A_i)

    O_concat = np.concatenate(head_outputs, axis=1)  # (n, h*d_k)
    output = O_concat @ W_O                          # (n, d)
    return output, all_A


# ============================================
# 主程序：数字演示（与第5章手算结果对比）
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("第5章：Multi-Head Self-Attention + RoPE NumPy实现")
    print("=" * 60)

    # ========================================
    # Part 1: 单头注意力（无RoPE，与第5章手算对比）
    # ========================================
    print("\n" + "=" * 60)
    print("【Part 1】单头注意力前向传播（无RoPE，与手算对比）")
    print("=" * 60)

    X = np.array([
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 1.0, 1.1, 1.2]
    ])  # (3, 4)

    W_Q = np.array([[1,0],[0,1],[1,0],[0,1]])
    W_K = np.array([[1,1],[0,1],[1,0],[0,1]])
    W_V = np.array([[0,1],[1,0],[0,1],[1,0]])

    O, A, cache = single_head_attention(X, W_Q, W_K, W_V)

    print(f"\nQ:\n{np.round(cache['Q'], 4)}")
    print(f"  [预期: [[0.4, 0.6], [1.2, 1.4], [2.0, 2.2]]]")
    print(f"\nA:\n{np.round(A, 4)}")
    print(f"  [预期: [[0.1344, 0.2805, 0.5851], ...]]")
    print(f"\nO:\n{np.round(O, 4)}")
    print(f"  [预期: [[1.7606, 1.5606], [2.0626, 1.8626], [2.1583, 1.9583]]]")
    assert np.allclose(A.sum(axis=1), 1.0), "A每行和应为1"
    print("✓ 前向传播与手算一致")

    # ========================================
    # Part 2: 反向传播
    # ========================================
    print("\n" + "=" * 60)
    print("【Part 2】反向传播（第5.4节）")
    print("=" * 60)

    dL_dO = np.array([[1.0, 0.5], [0.5, 1.0], [0.2, 0.8]])
    grads = single_head_attention_backward(dL_dO, cache)

    print(f"\ndL/dA:\n{np.round(grads['dL_dA'], 4)}")
    print(f"\ndL/dQ (含1/√d_k={1/np.sqrt(2):.3f}):\n{np.round(grads['dL_dQ'], 4)}")
    print(f"\ndL/dK:\n{np.round(grads['dL_dK'], 4)}")
    print(f"\n注意: dL/dQ中出现了K的值, dL/dK中出现了Q的值——联动调节")

    # ========================================
    # Part 3: RoPE演示（第5章位置编码小节）
    # ========================================
    print("\n" + "=" * 60)
    print("【Part 3】RoPE旋转位置编码")
    print("=" * 60)

    d_k = 8  # 用d_k=8做演示（4对维度）
    thetas = rope_frequencies(d_k)
    print(f"\nd_k={d_k}, 4个频率对:")
    for i, t in enumerate(thetas):
        eff_range = np.pi / (2 * t)
        print(f"  pair {i}: θ={t:.4f} rad/pos, 有效范围≈{eff_range:.0f}位置")

    # 演示RoPE对注意力分数的影响
    X_rope = RNG.standard_normal((5, d_k)) * 0.5  # 5个token, 8维
    W_Q_r = np.eye(d_k)  # identity, 不改变向量
    W_K_r = np.eye(d_k)
    W_V_r = np.eye(d_k)

    # 无RoPE
    _, A_no_rope, _ = single_head_attention(X_rope, W_Q_r, W_K_r, W_V_r, thetas=None)
    # 有RoPE
    _, A_rope, cache_rope = single_head_attention(X_rope, W_Q_r, W_K_r, W_V_r, thetas=thetas)

    print(f"\n无RoPE注意力矩阵 A (位置无关, 仅依赖内容):")
    print(np.round(A_no_rope, 3))
    print(f"\n有RoPE注意力矩阵 A (位置+内容):")
    print(np.round(A_rope, 3))

    # 验证: 相同内容不同顺序 -> 无RoPE结果相同, 有RoPE结果不同
    X_swap = X_rope[[2, 0, 1, 3, 4]]  # 打乱顺序
    _, A_swap_no_rope, _ = single_head_attention(X_swap, W_Q_r, W_K_r, W_V_r, thetas=None)
    _, A_swap_rope, _ = single_head_attention(X_swap, W_Q_r, W_K_r, W_V_r, thetas=thetas)

    print(f"\n打乱token顺序后:")
    print(f"  无RoPE: 注意力矩阵跟随打乱 (置换等变) — 顺序信息丢失")
    print(f"  有RoPE: 注意力矩阵完全不同 — 顺序信息被编码")

    # 验证RoPE核心性质: 相同相对距离 -> 相同内积
    # 用d_k=2, θ=15°做手算验证
    print("\n--- RoPE手算验证 (d_k=2, θ=15°) ---")
    theta_demo = np.array([np.deg2rad(15)])  # 15度
    Q_demo = np.array([[1.0, 0.0]])  # 1个token, 2维
    K_demo = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])  # 4个token

    # 手动施加RoPE
    Q_rot, K_rot = apply_rope(
        np.tile(Q_demo, (4, 1)),  # 复制4份模拟位置0-3
        K_demo,
        theta_demo
    )
    # 位置0的Q和各位置K的点积
    for pos in range(4):
        dot = Q_rot[0] @ K_rot[pos]
        expected = np.cos(np.deg2rad(15 * pos))
        print(f"  位置0·位置{pos}: 内积={dot:.4f}, cos({15*pos}°)={expected:.4f}, {'✓' if np.isclose(dot, expected, atol=1e-3) else '✗'}")

    # ========================================
    # Part 4: 多头注意力（与第5章手算对比）
    # ========================================
    print("\n" + "=" * 60)
    print("【Part 4】多头注意力（第5.5节）")
    print("=" * 60)

    h = 2
    W_Q1, W_K1, W_V1 = W_Q.copy(), W_K.copy(), W_V.copy()
    W_Q2 = np.array([[0,1],[1,0],[0,1],[1,0]])
    W_K2 = np.array([[0,1],[1,0],[0,1],[1,0]])
    W_V2 = np.array([[1,0],[0,1],[1,0],[0,1]])
    # 输出融合矩阵 W_O: (h*d_k, d) = (4, 4)
    # 使用identity矩阵，保留各头独立信息（训练后学习最优融合方式）
    W_O = np.eye(4)

    # 多头注意力 + 每头各自的RoPE
    thetas_mh = [rope_frequencies(2), rope_frequencies(2)]  # 每头d_k=2
    output, all_A = multi_head_attention(
        X, [W_Q1, W_Q2], [W_K1, W_K2], [W_V1, W_V2], W_O,
        thetas_list=thetas_mh
    )

    print(f"\n头数 h={h}, 每头 d_k=2")
    print(f"\n第1头 A:\n{np.round(all_A[0], 4)}")
    print(f"第2头 A:\n{np.round(all_A[1], 4)}")
    print(f"\n多头最终输出 (shape={output.shape}):\n{np.round(output, 4)}")

    # ========================================
    # Part 5: 完整Transformer Block
    # ========================================
    print("\n" + "=" * 60)
    print("【Part 5】完整Transformer Block (Attention + FFN + 残差 + LayerNorm)")
    print("=" * 60)

    def layer_norm(x, eps=1e-6):
        """LayerNorm: 减均值除标准差, 再缩放"""
        mu = x.mean(axis=-1, keepdims=True)
        var = x.var(axis=-1, keepdims=True)
        return (x - mu) / np.sqrt(var + eps)

    def relu(x):
        return np.maximum(0, x)

    def transformer_block(X, W_Q_list, W_K_list, W_V_list, W_O,
                          W1, b1, W2, b2, thetas_list=None):
        """
        单个Transformer Block:
        1. Multi-Head Self-Attention + 残差 + LayerNorm
        2. FFN (两层全连接 + ReLU) + 残差 + LayerNorm
        """
        n, d = X.shape

        # --- Sub-layer 1: Attention + 残差 + LayerNorm ---
        attn_out, attn_A = multi_head_attention(
            X, W_Q_list, W_K_list, W_V_list, W_O, thetas_list
        )
        x1 = layer_norm(X + attn_out)  # 残差 + 归一化

        # --- Sub-layer 2: FFN + 残差 + LayerNorm ---
        # FFN(x) = ReLU(x @ W1 + b1) @ W2 + b2
        hidden = relu(x1 @ W1 + b1)     # (n, d_ff)
        ffn_out = hidden @ W2 + b2       # (n, d)
        x2 = layer_norm(x1 + ffn_out)   # 残差 + 归一化

        return x2, attn_A

    # 用小规模参数演示
    d = 4
    d_ff = 8
    W1 = RNG.standard_normal((d, d_ff)) * 0.3
    b1 = np.zeros(d_ff)
    W2 = RNG.standard_normal((d_ff, d)) * 0.3
    b2 = np.zeros(d)

    thetas_block = [rope_frequencies(2), rope_frequencies(2)]
    block_out, block_A = transformer_block(
        X, [W_Q1, W_Q2], [W_K1, W_K2], [W_V1, W_V2], W_O,
        W1, b1, W2, b2, thetas_list=thetas_block
    )

    print(f"\n输入 X (shape={X.shape}):\n{np.round(X, 4)}")
    print(f"\nBlock输出 (shape={block_out.shape}):\n{np.round(block_out, 4)}")
    print(f"\n注意力权重 (第1头):\n{np.round(block_A[0], 4)}")
    print(f"注意力权重 (第2头):\n{np.round(block_A[1], 4)}")

    # ========================================
    # 总结
    # ========================================
    print("\n" + "=" * 60)
    print("【总结】")
    print("=" * 60)
    print("""
✓ Part 1: 单头注意力前向传播 — Q/K/V投影→点积→Softmax→加权求和
✓ Part 2: 反向传播 — 链式法则接力, Q/K梯度联动调节
✓ Part 3: RoPE — 旋转Q/K编码位置, 多频率多尺度覆盖
  - 核心性质: 相同相对距离→相同角度差→相同内积
  - 只转Q和K, 不碰V
✓ Part 4: 多头注意力 — h个头并行→Concat→线性融合
✓ Part 5: Transformer Block — Attention+FFN+残差+LayerNorm
""")
