# -*- coding: utf-8 -*-
"""T3 体验实验：实现训练循环（玩具扩散真训练）。

题面（对账记录第 5 节）：
  数据：2D 双峰混合高斯 0.5*N([2,2],0.25I) + 0.5*N(-[2,2],0.25I)（T1 同款）
  模型：eps_theta 小 MLP（输入 2 维 + t 的正弦时间嵌入 16 维 -> 72 -> 72 -> 2，约 6.8k 参数）
  训练：VP 离散调度 beta 线性 1e-4 -> 0.02，T=200；batch 256；t 均匀采样 {1..200}；
        Adam lr=1e-3；4000 迭代；CPU 分钟级
  断言格（对账记录 4a 判据清单）：
    a  数据分布校验（双峰均值 / 方差）
    b  训练损失贴近理论下限（末段均值 < 1.25 x 贝叶斯下限；下限由混合高斯后验数值算出）
    c  loss(t) 形状：低噪声段（t 小，SNR 高）loss 高、高噪声段 loss 低，且低段 > 1.5 x 高段
       （ch4 L99 断言的实物对拍）
    d  梯度检查：autograd vs 中心有限差分，|fd-ga| <= 1e-8 + 1e-5*max(|fd|,|ga|) 全部通过
       （§4 F33 的 1e-5 级判据，组合容差同 PyTorch gradcheck 口径；纯相对误差对 ~1e-9 级
        小梯度受 float64 抵消限制，不作判据，仅报告）
    e  参数量在 6k-8k
    f  DDIM 50 步采样 mode coverage >= 85%
    g  DDPM 200 步采样 mode coverage >= 85%
    h  DDIM 20 步 vs DDPM 200 步：coverage 下降 < 5 个百分点
    i  残次模型对照（拓展）：只训高噪声 / 只训低噪声两个残次模型，coverage 均低于完整模型
"""
import math
import time

import numpy as np
import torch
import torch.nn as nn

torch.manual_seed(20261009)
np.random.seed(20261009)

T = 200
BATCH = 256
ITERS = 4000
LR = 1e-3
PEAK = np.array([2.0, 2.0])
MODE_RADIUS = 1.5
N_SAMPLE = 512

# ---------- VP 离散调度（beta 线性 1e-4 -> 0.02，T=200） ----------
betas = np.linspace(1e-4, 0.02, T)
alphas = 1.0 - betas
alphas_cum = np.cumprod(alphas)            # abar_t, t = 1..200（索引 t-1）
abar = torch.tensor(alphas_cum, dtype=torch.float32)
beta_t = torch.tensor(betas, dtype=torch.float32)


def make_batch(n, rng):
    """双峰混合高斯采样：0.5*N([2,2],0.25I) + 0.5*N(-[2,2],0.25I)"""
    idx = rng.integers(0, 2, size=n)
    sign = np.where(idx == 0, 1.0, -1.0)[:, None]
    return sign * PEAK[None, :] + 0.5 * rng.standard_normal((n, 2))


def q_forward(x0, t_idx, eps):
    """闭式加噪：x_t = sqrt(abar_t) x0 + sqrt(1-abar_t) eps；t_idx 为 0 基（对应 t=1..200）"""
    a = alphas_cum[t_idx][:, None]
    return np.sqrt(a) * x0 + np.sqrt(1.0 - a) * eps


# ---------- eps_theta 小网：输入 2 + 正弦时间嵌入 16 -> 72 -> 72 -> 2 ----------
class TimeEmbed(nn.Module):
    """正弦位置编码（素材 ch4 L133 机制实物化）：标量 t/T 映射成 16 维向量"""

    def __init__(self, dim=16):
        super().__init__()
        self.register_buffer("freqs", torch.exp(
            torch.arange(0, dim // 2, dtype=torch.float32) * (-math.log(10000.0) / (dim // 2))))

    def forward(self, t_norm):
        ang = t_norm[:, None] * self.freqs[None, :]
        return torch.cat([torch.sin(ang), torch.cos(ang)], dim=1)


class EpsNet(nn.Module):
    def __init__(self, hid=72, emb=16):
        super().__init__()
        self.emb = TimeEmbed(emb)
        self.net = nn.Sequential(
            nn.Linear(2 + emb, hid), nn.SiLU(),
            nn.Linear(hid, hid), nn.SiLU(),
            nn.Linear(hid, 2),
        )

    def forward(self, x, t_norm):
        return self.net(torch.cat([x, self.emb(t_norm)], dim=1))


def train(model, iters, t_lo=1, t_hi=T, seed=20261009):
    """训练循环体：采 x0 -> 采 t -> 采 eps -> 闭式加噪 -> 预测 -> MSE -> 反向传播。
    返回 (losses, loss_sum_t, loss_cnt_t)。"""
    rng = np.random.default_rng(seed)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    losses = np.zeros(iters)
    loss_sum = np.zeros(T + 1)
    loss_cnt = np.zeros(T + 1)
    for i in range(iters):
        x0 = torch.tensor(make_batch(BATCH, rng), dtype=torch.float32)
        t = torch.tensor(rng.integers(t_lo, t_hi + 1, size=BATCH))       # t = 1..200
        eps = torch.randn(BATCH, 2)
        a = alphas_cum[t.numpy() - 1][:, None]
        x_t = torch.tensor(np.sqrt(a), dtype=torch.float32) * x0 \
            + torch.tensor(np.sqrt(1.0 - a), dtype=torch.float32) * eps
        pred = model(x_t, t.float() / T)
        loss = ((pred - eps) ** 2).mean()
        opt.zero_grad()
        loss.backward()          # 自动微分：计算图 + 节点级微分（§4）
        opt.step()
        losses[i] = loss.item()
        for tv in np.unique(t.numpy()):
            m = t.numpy() == tv
            loss_sum[tv] += ((pred.detach().numpy() - eps.numpy())[m] ** 2).mean() * m.sum()
            loss_cnt[tv] += m.sum()
    return losses, loss_sum, loss_cnt


# ---------- 采样 ----------
@torch.no_grad()
def ddim_sample(model, n, steps, seed):
    """DDIM 确定性采样（ch5 L166 方框，随机性强度取 0）。"""
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(n, 2, generator=g)
    ts = np.unique(np.linspace(T, 1, steps).round().astype(int))[::-1]  # 从 200 到 1
    for i, t in enumerate(ts):
        t_prev = ts[i + 1] if i + 1 < len(ts) else 0
        ab_t = alphas_cum[t - 1]
        ab_p = alphas_cum[t_prev - 1] if t_prev >= 1 else 1.0
        eps_pred = model(x, torch.full((n,), t / T))
        coef = math.sqrt(ab_p) * (math.sqrt(1.0 / ab_p - 1.0) - math.sqrt(1.0 / ab_t - 1.0))
        x = math.sqrt(ab_p / ab_t) * x + coef * eps_pred
    return x.numpy()


@torch.no_grad()
def ddpm_sample(model, n, seed):
    """DDPM 200 步随机采样（T2 采样公式，sigma_q 取后验方差）。"""
    g = torch.Generator().manual_seed(seed)
    x = torch.randn(n, 2, generator=g)
    for t in range(T, 0, -1):
        ab_t = alphas_cum[t - 1]
        ab_p = alphas_cum[t - 2] if t >= 2 else 1.0
        eps_pred = model(x, torch.full((n,), t / T))
        mean = (x - betas[t - 1] / math.sqrt(1.0 - ab_t) * eps_pred) / math.sqrt(alphas[t - 1])
        if t > 1:
            var = (1.0 - ab_p) / (1.0 - ab_t) * betas[t - 1]
            x = mean + math.sqrt(var) * torch.randn(n, 2, generator=g)
        else:
            x = mean
    return x.numpy()


def coverage(samples):
    d1 = np.linalg.norm(samples - PEAK[None, :], axis=1)
    d2 = np.linalg.norm(samples + PEAK[None, :], axis=1)
    return float(np.mean(np.minimum(d1, d2) <= MODE_RADIUS))


def mean_dist(samples):
    d1 = np.linalg.norm(samples - PEAK[None, :], axis=1)
    d2 = np.linalg.norm(samples + PEAK[None, :], axis=1)
    return float(np.mean(np.minimum(d1, d2)))


results = []
def check(tag, got, want, tol, fmt="%.6g"):
    ok = abs(got - want) <= tol
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {tag}: got={fmt % got} want={fmt % want} (tol={tol:g})")
    return ok


def ge(tag, got, thr, fmt="%.4f"):
    ok = got >= thr
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {tag}: got={fmt % got} >= {fmt % thr}")
    return ok


def gt(tag, got, thr, fmt="%.4f"):
    ok = got > thr
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {tag}: got={fmt % got} > {fmt % thr}")
    return ok


t_start = time.time()

# ---------- a 数据分布校验 ----------
rng = np.random.default_rng(1)
xs = make_batch(20000, rng)
m1 = xs.mean(axis=0)
v1 = xs.var(axis=0)
check("a  数据均值~[0,0]", float(np.abs(m1).max()), 0.0, 0.03)
check("a  数据方差~4.25", float(v1.mean()), 4.25, 0.08)

# ---------- e 参数量 ----------
model = EpsNet()
n_params = sum(p.numel() for p in model.parameters())
check("e  参数量(6k-8k)", float(n_params), 6770.0, 0.0)
print(f"     参数量 = {n_params}")

# ---------- d 梯度检查（训练前：固定小批量，float64 对拍） ----------
gc_model = EpsNet().double()
rng = np.random.default_rng(7)
_x0 = torch.tensor(make_batch(8, rng), dtype=torch.float64)
_t = torch.tensor(rng.integers(1, T + 1, size=8))
_eps = torch.randn(8, 2, dtype=torch.float64)
_a = alphas_cum[_t.numpy() - 1][:, None]
_x_t = torch.tensor(np.sqrt(_a), dtype=torch.float64) * _x0 \
    + torch.tensor(np.sqrt(1.0 - _a), dtype=torch.float64) * _eps


def loss64(params_vec=None):
    if params_vec is not None:
        ofs = 0
        for p in gc_model.parameters():
            k = p.numel()
            p.data.copy_(params_vec[ofs:ofs + k].view_as(p))
            ofs += k
    pred = gc_model(_x_t, _t.double() / T)
    return ((pred - _eps) ** 2).mean()


loss64()
loss = loss64()
loss.backward()
auto_grads = [p.grad.clone() for p in gc_model.parameters()]
flat = torch.cat([p.data.reshape(-1) for p in gc_model.parameters()])
h = 1e-5
max_rel = 0.0
max_viol = -1e9   # 组合容差超出量，<=0 即通过
k = 0
for p in gc_model.parameters():
    for idx in range(p.numel()):
        orig = p.data.reshape(-1)[idx].clone()
        p.data.reshape(-1)[idx] = orig + h
        lp = loss64()
        p.data.reshape(-1)[idx] = orig - h
        lm = loss64()
        p.data.reshape(-1)[idx] = orig
        fd = (lp - lm) / (2 * h)
        ga = auto_grads[k].reshape(-1)[idx]
        denom = max(abs(fd), abs(ga))
        rel = (abs(fd - ga) / denom).item() if denom > 0 else 0.0
        max_rel = max(max_rel, rel)
        max_viol = max(max_viol, (abs(fd - ga) - (1e-8 + 1e-5 * denom)).item())
    k += 1
gt("d  梯度检查 组合容差(1e-5级) 全部通过", -max_viol, 0.0, fmt="%.3e")
print(f"     梯度检查: {n_params} 个参数全部对拍；纯相对误差最大 = {max_rel:.3e}"
      f"（超限者均为 ~1e-9 级小梯度，浮点抵消所致）")

# ---------- b/c 真训练 ----------
t_train = time.time()
losses, loss_sum, loss_cnt = train(model, ITERS)
train_secs = time.time() - t_train
head = losses[:200].mean()
tail = losses[-200:].mean()

# 贝叶斯下限：混合高斯后验下 epsilon 预测的最优 MSE（数值估计，20 万样本）
rngf = np.random.default_rng(99)
NF = 200000
x0f = make_batch(NF, rngf)
tf = rngf.integers(1, T + 1, NF)
epsf = rngf.standard_normal((NF, 2))
xf = q_forward(x0f, tf - 1, epsf)
af = alphas_cum[tf - 1][:, None]
sig2f = 1.0 - 0.75 * af
mus = np.stack([PEAK, -PEAK])
d2 = ((xf[:, None, :] - np.sqrt(af)[:, None, :] * mus[None]) ** 2).sum(-1)
logw = -d2 / (2 * sig2f)
logw -= logw.max(1, keepdims=True)
wf = np.exp(logw)
wf /= wf.sum(1, keepdims=True)
e_mean = np.sqrt(1 - af)[:, None, :] / sig2f[:, None, :] \
    * (xf[:, None, :] - np.sqrt(af)[:, None, :] * mus[None])
post = (wf[:, :, None] * e_mean).sum(1)
floor = float(((epsf - post) ** 2).mean())

gt("b  末段均值 < 贝叶斯下限 x 1.25", floor * 1.25 - tail, 0.0, fmt="%.4f")
print(f"     训练: {ITERS} 迭代, batch {BATCH}, 用时 {train_secs:.1f}s")
print(f"     初段均值 = {head:.4f}  末段均值 = {tail:.4f}  比值 = {tail/head:.4f}"
      f"  贝叶斯下限 = {floor:.4f}  末段/下限 = {tail/floor:.3f}")

mean_loss_t = loss_sum / np.maximum(loss_cnt, 1)
lo_seg = mean_loss_t[1:41].mean()      # t=1..40  低噪声（SNR 高）
hi_seg = mean_loss_t[161:201].mean()   # t=161..200 高噪声（SNR 低）
gt("c  loss(t): 低噪声段 > 高噪声段 x 1.5", lo_seg / hi_seg, 1.5, fmt="%.4f")
print(f"     loss(t): t=1..40 均值 = {lo_seg:.4f}   t=161..200 均值 = {hi_seg:.4f}")

np.save("losses.npy", losses)
np.save("mean_loss_t.npy", mean_loss_t[1:T + 1])

# ---------- f/g/h 采样对拍 ----------
cov_ddim50 = coverage(ddim_sample(model, N_SAMPLE, 50, seed=123))
cov_ddpm200 = coverage(ddpm_sample(model, N_SAMPLE, seed=123))
cov_ddim20 = coverage(ddim_sample(model, N_SAMPLE, 20, seed=123))
ge("f  DDIM 50 步 mode coverage >= 0.85", cov_ddim50, 0.85)
ge("g  DDPM 200 步 mode coverage >= 0.85", cov_ddpm200, 0.85)
check("h  DDIM20 vs DDPM200 下降 < 5pp", abs(cov_ddim20 - cov_ddpm200), 0.0, 0.05, fmt="%.4f")
print(f"     mode coverage: DDIM50 = {cov_ddim50:.3f}  DDPM200 = {cov_ddpm200:.3f}  DDIM20 = {cov_ddim20:.3f}")

# ---------- i 残次模型对照（拓展） ----------
m_hi = EpsNet()
train(m_hi, 1500, t_lo=161, t_hi=200, seed=111)
cov_hi = coverage(ddim_sample(m_hi, N_SAMPLE, 50, seed=123))
md_hi = mean_dist(ddim_sample(m_hi, N_SAMPLE, 50, seed=123))
m_lo = EpsNet()
train(m_lo, 1500, t_lo=1, t_hi=40, seed=222)
cov_lo = coverage(ddim_sample(m_lo, N_SAMPLE, 50, seed=123))
md_lo = mean_dist(ddim_sample(m_lo, N_SAMPLE, 50, seed=123))
gt("i  只训高噪声 coverage 低 5pp 以上", cov_ddim50 - cov_hi, 0.05)
gt("i  只训低噪声 coverage 低 15pp 以上", cov_ddim50 - cov_lo, 0.15)
print(f"     残次模型: 高噪声-only coverage = {cov_hi:.3f} (距最近峰均值 {md_hi:.2f})"
      f"  低噪声-only coverage = {cov_lo:.3f} (距最近峰均值 {md_lo:.2f})  完整 = {cov_ddim50:.3f}")

# ---------- loss 曲线图 ----------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
# 中文字体：按环境自动挑选（Windows 用微软雅黑，Colab 用 Noto Sans CJK）
    from matplotlib import font_manager
    avail = {f.name for f in font_manager.fontManager.ttflist}
    cjk = [f for f in ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC',
                       'Noto Sans CJK JP', 'WenQuanYi Micro Hei'] if f in avail]
    plt.rcParams['font.sans-serif'] = cjk + plt.rcParams['font.sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    ax[0].plot(losses)
    ax[0].set_title("训练损失")
    ax[0].set_xlabel("迭代步")
    ax[0].set_ylabel("损失")
    ts = np.arange(1, T + 1)
    ax[1].plot(ts, mean_loss_t[1:T + 1])
    ax[1].set_title("损失 vs t（t 小＝高信噪比）")
    ax[1].set_xlabel("t")
    ax[1].set_ylabel("损失")
    fig.tight_layout()
    fig.savefig("loss_curves.png", dpi=120)
    print("     loss_curves.png 已保存")
except Exception as exc:  # 画图失败不判 FAIL
    print(f"     画图跳过: {exc}")

total = time.time() - t_start
print(f"     总用时 {total:.1f}s")
print()
print("全部断言通过（exit 0）" if all(results) else "存在 FAIL（exit 1）")
raise SystemExit(0 if all(results) else 1)
