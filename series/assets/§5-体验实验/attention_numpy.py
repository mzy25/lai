"""§5 教学版单头自注意力（纯 NumPy，无外部依赖）：3 token × 4 维输入、2 维投影，
与旧版第5章四步手算例共用同一组 X/W_Q/W_K/W_V，输出可逐格对拍。"""
import numpy as np

X = np.array([[0.1, 0.2, 0.3, 0.4],   # 3 个 token，各 4 维
              [0.5, 0.6, 0.7, 0.8],
              [0.9, 1.0, 1.1, 1.2]])
W_Q = np.array([[1, 0], [0, 1], [1, 0], [0, 1]])  # 提问投影（4×2）
W_K = np.array([[1, 1], [0, 1], [1, 0], [0, 1]])  # 报专长投影
W_V = np.array([[0, 1], [1, 0], [0, 1], [1, 0]])  # 给建议投影


def attention(X, W_Q, W_K, W_V):
    """单头自注意力 softmax(QK^T/√d_k)V，四步逐一对应旧版公式1–4"""
    Q = X @ W_Q                                   # 公式1：投影出 Q、K、V
    K = X @ W_K
    V = X @ W_V
    S = (Q @ K.T) / np.sqrt(Q.shape[1])           # 公式2：匹配度分数，除以 √d_k
    A = np.exp(S - S.max(axis=1, keepdims=True))  # 公式3：先减 max（§4.5）再取指数
    A = A / A.sum(axis=1, keepdims=True)          #   按行归一化，每行和为 1
    O = A @ V                                     # 公式4：按注意力权重加权汇总
    return O, A


if __name__ == "__main__":
    np.set_printoptions(precision=4, suppress=True)
    O, A = attention(X, W_Q, W_K, W_V)
    print("注意力权重 A（3×3，每行和=1）：")
    print(A)
    print("行和校验：", A.sum(axis=1))
    print("加权输出 O（3×2）：")
    print(O)
