#!/usr/bin/env python3
"""基座模型：从咿呀到行动 -- 配图生成脚本
生成23张dpi=200的教学配图（P0/P1/P2/P3四批）

使用方法:
    python3 generate_figures.py

输出: 当前目录下的 figures/ 文件夹
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fig_common  # noqa: E402  (sys.path 就绪后再导入共享模块)
from fig_common import CJK_FONT_NAME, setup_rc  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "figures"


def save(fig, name):
    fig_common.save_fig(fig, name, OUTPUT_DIR, dpi=200)


def setup():
    setup_rc(dpi=200)
    print(f"输出目录: {OUTPUT_DIR}")
    print("开始生成23张配图...")

# ============================================================
# Ch1 - ViT patch 切分
# ============================================================

def fig_ch1_vit_patch():
    """ViT: 把224x224图片切成14x14=196个patch"""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # --- 左图：原始图片 + patch网格 ---
    ax = axes[0]
    # 用渐变模拟一张图片
    img = np.zeros((224, 224, 3))
    for i in range(224):
        for j in range(224):
            img[i, j] = [i/224*0.8+0.2, j/224*0.6+0.3, (1-(i+j)/448)*0.7+0.2]
    ax.imshow(img)
    # 画14x14网格
    for k in range(15):
        ax.axhline(y=k*16, color='white', lw=0.5, alpha=0.7)
        ax.axvline(x=k*16, color='white', lw=0.5, alpha=0.7)
    # 高亮一个patch
    rect = mpatches.Rectangle((32, 48), 16, 16, linewidth=2.5, edgecolor='red', facecolor='none')
    ax.add_patch(rect)
    ax.annotate('16x16\npatch', (40, 56), color='red', fontsize=8, ha='center',
                fontproperties=CJK_FONT_NAME, fontweight='bold')
    ax.set_title('224x224 像素图片\n切14x14=196个patch', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_xlabel('224 px', fontsize=10)
    ax.set_ylabel('224 px', fontsize=10)
    ax.set_xticks([0, 112, 224])
    ax.set_yticks([0, 112, 224])

    # --- 中图：单个patch拉平成768维向量 ---
    ax = axes[1]
    # 画一个16x16的小图块
    patch = img[48:64, 32:48]
    ax_inset = fig.add_axes([0.30, 0.45, 0.06, 0.25])
    ax_inset.imshow(patch)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    ax_inset.set_title('16x16x3', fontsize=8, fontproperties=CJK_FONT_NAME)

    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axis('off')
    # 箭头：拉平
    ax.annotate('', xy=(4.5, 5), xytext=(2, 5),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2196F3'))
    ax.text(2.0, 5.8, '拉平', fontsize=10, fontproperties=CJK_FONT_NAME, color='#2196F3', ha='center')
    # 画768维向量条
    np.random.seed(42)
    vec = np.random.randn(40) * 0.3 + 0.5
    bar_x = np.linspace(5, 9.4, len(vec))
    ax.barh(5, [0.08]*len(vec), left=bar_x, height=0.8,
            color=[plt.cm.coolwarm(v) for v in vec], alpha=0.8)
    ax.text(7.2, 3.8, '768维向量', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold')
    ax.text(7.2, 3.0, '16x16x3=768', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    # 线性投影标注
    ax.annotate('', xy=(5, 2), xytext=(9.5, 2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#4CAF50'))
    ax.text(7.2, 1.3, '线性投影 Wx+b', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#4CAF50')
    ax.text(7.2, 0.5, '768维 → d维', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.set_title('patch → 向量', fontsize=12, fontproperties=CJK_FONT_NAME)

    # --- 右图：196个token序列 ---
    ax = axes[2]
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')
    # 画token序列（14x14简化为7x7方阵展示）
    for i in range(7):
        for j in range(7):
            x, y = 1 + j*2, 7 - i*1.1
            color = plt.cm.viridis((i*7+j)/49)
            rect = FancyBboxPatch((x-0.7, y-0.35), 1.4, 0.7,
                                   boxstyle="round,pad=0.1", facecolor=color, edgecolor='gray', lw=0.5)
            ax.add_patch(rect)
    ax.text(8, 9.2, '196个图片 token', fontsize=12, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold')
    ax.text(8, 0.5, '+ 位置编码 → 喂进 Transformer', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#FF9800')
    ax.annotate('', xy=(8, 1.2), xytext=(8, 0.9),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#FF9800'))
    ax.set_title('与文字 token 同构\n可走标准 Transformer', fontsize=12, fontproperties=CJK_FONT_NAME)

    plt.suptitle('ViT = patch 投影 + Transformer encoder', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME)
    # inset axes (fig.add_axes) 不受 tight_layout 管理——用 h_pad 参数时 matplotlib 仍会警告。
    # 视觉验证：inset 位于中图固定坐标，布局警告不影响输出；保留 tight_layout 对主 axes 的收缩。
    fig.tight_layout()
    save(fig, 'fig_ch1_vit_patch.png')

# ============================================================
# Ch2 - token 旅程
# ============================================================

def fig_ch2_token_journey():
    """一个token在Transformer中的旅程：查表→96层→输出"""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14); ax.set_ylim(0, 10)
    ax.axis('off')

    # 颜色
    c_embed = '#E3F2FD'
    c_attn  = '#FFF3E0'
    c_ffn   = '#E8F5E9'
    c_out   = '#FFEBEE'
    c_resid = '#F3E5F5'

    # --- 输入 ---
    tokens = ['猫', '坐', '在', '垫子', '上']
    for i, t in enumerate(tokens):
        x = 0.5 + i * 1.0
        rect = FancyBboxPatch((x-0.35, 8.5), 0.7, 0.8,
                               boxstyle="round,pad=0.1", facecolor='white', edgecolor='black', lw=1.2)
        ax.add_patch(rect)
        ax.text(x, 8.9, t, fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold')

    # --- 查表 ---
    ax.annotate('', xy=(3, 8.0), xytext=(3, 8.4),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))
    ax.text(3.0, 8.2, '查表 + 位置编码', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 画5个向量方块
    for i in range(5):
        x = 0.5 + i * 1.0
        rect = FancyBboxPatch((x-0.35, 7.0), 0.7, 0.8,
                               boxstyle="round,pad=0.1", facecolor=c_embed, edgecolor='#1565C0', lw=1)
        ax.add_patch(rect)
        ax.text(x, 7.4, f'v{i+1}', fontsize=9, ha='center', color='#1565C0')

    ax.text(7.5, 7.4, '4096维', fontsize=9, ha='center', color='gray', fontproperties=CJK_FONT_NAME)

    # --- Transformer layers ---
    layer_labels = [
        ('浅层 1-20', '语法·共现'),
        ('中层 20-60', '语义·关系'),
        ('深层 60-96', '推理·逻辑'),
    ]

    y_positions = [5.8, 4.2, 2.6]
    for idx, (label, desc) in enumerate(layer_labels):
        y = y_positions[idx]
        # Attention block
        rect_a = FancyBboxPatch((1.5, y), 4, 0.7,
                                 boxstyle="round,pad=0.1", facecolor=c_attn, edgecolor='#E65100', lw=1)
        ax.add_patch(rect_a)
        ax.text(3.5, y+0.35, 'Self-Attention', fontsize=9, ha='center', fontproperties=CJK_FONT_NAME, color='#E65100')

        # + 残差
        ax.text(5.8, y+0.35, '+', fontsize=12, ha='center', fontweight='bold', color='#7B1FA2')

        # FFN block
        rect_f = FancyBboxPatch((6.2, y), 3, 0.7,
                                 boxstyle="round,pad=0.1", facecolor=c_ffn, edgecolor='#2E7D32', lw=1)
        ax.add_patch(rect_f)
        ax.text(7.7, y+0.35, 'FFN (整理笔记)', fontsize=9, ha='center', fontproperties=CJK_FONT_NAME, color='#2E7D32')

        # + 残差
        ax.text(9.4, y+0.35, '+', fontsize=12, ha='center', fontweight='bold', color='#7B1FA2')

        # 层标注
        ax.text(11.5, y+0.35, f'{label}\n{desc}', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center',
                color='#E65100', fontweight='bold')

        # 层间箭头
        if idx < 2:
            ax.annotate('', xy=(5.5, y-0.5), xytext=(5.5, y-0.1),
                        arrowprops=dict(arrowstyle='->', lw=1.2, color='gray'))

    # 残差连接标注（虚线从输入到每层）
    ax.plot([0.3, 0.3], [7.0, 2.6], 'k--', lw=0.8, alpha=0.4)
    ax.text(0.1, 5.0, '残差\n高速\n公路', fontsize=7, fontproperties=CJK_FONT_NAME, ha='center',
            color='gray', alpha=0.6, rotation=90)

    # --- 输出 ---
    ax.annotate('', xy=(5.5, 2.0), xytext=(5.5, 2.4),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))
    ax.text(5.5, 2.2, '取最后一个 token', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # Unembedding
    rect_u = FancyBboxPatch((3.5, 0.8), 4, 0.7,
                             boxstyle="round,pad=0.1", facecolor=c_out, edgecolor='#C62828', lw=1)
    ax.add_patch(rect_u)
    ax.text(5.5, 1.15, 'Unembedding: 4096维 → 50000维', fontsize=9, ha='center', fontproperties=CJK_FONT_NAME, color='#C62828')

    # Softmax输出
    ax.annotate('', xy=(5.5, 0.5), xytext=(5.5, 0.7),
                arrowprops=dict(arrowstyle='->', lw=1.2, color='#C62828'))

    # 概率分布柱状图
    words = ['下', '面', '的', '睡', '...']
    probs = [0.31, 0.22, 0.15, 0.08, 0.24]
    colors_p = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', 'gray']
    for i, (w, p, c) in enumerate(zip(words, probs, colors_p)):
        x = 2 + i * 1.4
        ax.bar(x, p, width=0.8, bottom=0, color=c, alpha=0.8)
        ax.text(x, p + 0.02, f'{p:.0%}', fontsize=8, ha='center')
        ax.text(x, -0.08, w, fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold')

    ax.set_xlim(0, 14); ax.set_ylim(-0.3, 10)
    ax.set_title('"猫坐在垫子上" → 预测下一个 token', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch2_token_journey.png')

# ============================================================
# Ch3 - RLHF 三步走
# ============================================================

def fig_ch3_rlhf_pipeline():
    """RLHF三步走：偏好数据→奖励模型→PPO优化"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    # --- Step 1: 偏好数据 ---
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axis('off')

    # Prompt
    rect = FancyBboxPatch((1, 8), 8, 1.2, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    ax.text(5, 8.6, 'Prompt: "怎么治感冒？"', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')

    # Answer A (chosen)
    rect_a = FancyBboxPatch((1, 5.5), 8, 1.8, boxstyle="round,pad=0.1",
                             facecolor='#E8F5E9', edgecolor='#2E7D32', lw=1.5)
    ax.add_patch(rect_a)
    ax.text(5, 6.8, '回答A (chosen)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32', fontweight='bold')
    ax.text(5, 6.0, '"多休息，多喝水，\n症状严重吃退烧药"', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center')

    # Answer B (rejected)
    rect_b = FancyBboxPatch((1, 3), 8, 1.8, boxstyle="round,pad=0.1",
                             facecolor='#FFEBEE', edgecolor='#C62828', lw=1.5)
    ax.add_patch(rect_b)
    ax.text(5, 4.3, '回答B (rejected)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828', fontweight='bold')
    ax.text(5, 3.5, '"感冒要吃抗生素"', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center')

    # 标注员
    ax.annotate('', xy=(0.5, 6.4), xytext=(0.5, 4.0),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='#FF9800'))
    ax.text(0.2, 5.2, '标\n注\n员\n选', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#FF9800', fontweight='bold')

    # 三元组
    rect_t = FancyBboxPatch((1.5, 0.8), 7, 1.2, boxstyle="round,pad=0.1",
                             facecolor='#FFF8E1', edgecolor='#F57F17', lw=1)
    ax.add_patch(rect_t)
    ax.text(5, 1.4, '三元组 (x, y_w, y_l)', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17', fontweight='bold')

    ax.set_title('步骤1：收集偏好数据', fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold')

    # --- Step 2: 奖励模型 ---
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axis('off')

    # 输入
    rect = FancyBboxPatch((0.5, 7), 3, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1)
    ax.add_patch(rect)
    ax.text(2, 7.75, 'prompt +\n回答', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center')

    # 奖励模型
    rect = FancyBboxPatch((4, 6.5), 2.5, 2.5, boxstyle="round,pad=0.1",
                           facecolor='#F3E5F5', edgecolor='#7B1FA2', lw=1.5)
    ax.add_patch(rect)
    ax.text(5.25, 8.3, '奖励模型', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#7B1FA2')
    ax.text(5.25, 7.7, 'R_φ(x,y)', fontsize=11, ha='center', color='#7B1FA2')
    ax.text(5.25, 7.0, '神经网络', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    ax.annotate('', xy=(4, 7.75), xytext=(3.5, 7.75),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))

    # 输出分数
    rect = FancyBboxPatch((7.5, 7), 2, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#E8F5E9', edgecolor='#2E7D32', lw=1)
    ax.add_patch(rect)
    ax.text(8.5, 7.75, '分数\nR=2.5', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32', fontweight='bold')

    ax.annotate('', xy=(7.5, 7.75), xytext=(6.5, 7.75),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))

    # Bradley-Terry
    rect = FancyBboxPatch((1, 3.5), 8, 2.5, boxstyle="round,pad=0.1",
                           facecolor='#FFF8E1', edgecolor='#F57F17', lw=1)
    ax.add_patch(rect)
    ax.text(5, 5.5, 'Bradley-Terry 模型', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    ax.text(5, 4.7, r'$P(y_w \succ y_l) = \sigma(R(x,y_w) - R(x,y_l))$', fontsize=12, ha='center')
    ax.text(5, 3.9, '正样本分数 > 负样本分数', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 训练目标
    ax.text(5, 2.2, '训练目标', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold')
    ax.text(5, 1.4, r'$\mathcal{L} = -\log\sigma(R(x,y_w) - R(x,y_l))$', fontsize=12, ha='center')

    ax.set_title('步骤2：训练奖励模型', fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold')

    # --- Step 3: PPO 优化 ---
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axis('off')

    # 策略模型
    rect = FancyBboxPatch((0.5, 6.5), 2.5, 2, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    ax.text(1.75, 8.0, '策略 π_θ', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#1565C0')
    ax.text(1.75, 7.2, '(LLM)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 采样回答
    ax.annotate('', xy=(4, 7.5), xytext=(3, 7.5),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))
    ax.text(3.5, 7.9, '采样', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(4.5, 7.5, '回答 y', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center')

    # 奖励模型打分
    ax.annotate('', xy=(6, 7.5), xytext=(5.5, 7.5),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))
    rect = FancyBboxPatch((6, 6.5), 2, 2, boxstyle="round,pad=0.1",
                           facecolor='#F3E5F5', edgecolor='#7B1FA2', lw=1)
    ax.add_patch(rect)
    ax.text(7, 8.0, 'R_φ', fontsize=11, ha='center', color='#7B1FA2', fontweight='bold')
    ax.text(7, 7.2, '打分', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#7B1FA2')

    # 奖励信号
    ax.annotate('奖励 R', xy=(3, 5.5), xytext=(7, 6.3),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#FF9800', connectionstyle='arc3,rad=-0.3'),
                fontsize=10, fontproperties=CJK_FONT_NAME, color='#FF9800', fontweight='bold')

    # PPO 更新
    rect = FancyBboxPatch((1, 3.5), 6, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#E8F5E9', edgecolor='#2E7D32', lw=1.5)
    ax.add_patch(rect)
    ax.text(4, 4.6, 'PPO 策略更新', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#2E7D32')
    ax.text(4, 3.9, r'$\max R_\phi(x,y) - \beta \cdot KL(\pi_\theta \| \pi_{ref})$', fontsize=10, ha='center')

    # 更新箭头
    ax.annotate('', xy=(1.75, 6.4), xytext=(1.75, 5.1),
                arrowprops=dict(arrowstyle='->', lw=2, color='#2E7D32'))

    # KL约束标注
    rect = FancyBboxPatch((7.5, 3.5), 2, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#FFEBEE', edgecolor='#C62828', lw=1)
    ax.add_patch(rect)
    ax.text(8.5, 4.5, 'KL约束', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828', fontweight='bold')
    ax.text(8.5, 3.8, '别偏离\n太远', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828')

    # 奖励黑客警告
    ax.text(5, 1.8, '风险：奖励黑客', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828', fontweight='bold')
    ax.text(5, 1.0, 'RM给高分 ≠ 人觉得好\nKL约束是防线', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    ax.set_title('步骤3：PPO 优化策略', fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold')

    plt.suptitle('RLHF 三步走：偏好数据 → 奖励模型 → PPO 优化', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch3_rlhf_pipeline.png')

# ============================================================
# Ch4 - KV Cache 对比
# ============================================================

def fig_ch4_kv_cache():
    """无cache vs有cache：FLOPs对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # --- 左图：无cache vs有cache 计算量对比 ---
    ax = axes[0]
    n_tokens = np.arange(1, 101)

    # 无cache: 每步O(n^2 * d * L), 累计 O(N^3)
    no_cache = n_tokens**2 * 4096 * 32 / 1e9  # GFLOPs per step
    no_cache_cum = np.cumsum(no_cache)

    # 有cache: 每步O(n * d * L), 累计 O(N^2)
    with_cache = n_tokens * 4096 * 32 / 1e9
    with_cache_cum = np.cumsum(with_cache)

    ax.plot(n_tokens, no_cache_cum, 'r-', lw=2.5, label='无 cache: O(N³·d·L)')
    ax.plot(n_tokens, with_cache_cum, 'b-', lw=2.5, label='有 cache: O(N²·d·L)')
    ax.fill_between(n_tokens, with_cache_cum, no_cache_cum, alpha=0.1, color='red')

    # 标注加速比
    ax.annotate(f'~54× 加速', xy=(80, with_cache_cum[79]),
                xytext=(60, no_cache_cum[79]*0.5),
                fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold', color='#C62828',
                arrowprops=dict(arrowstyle='->', lw=2, color='#C62828'))

    ax.set_xlabel('生成的 token 数', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('累计 FLOPs (GFLOPs)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('无 cache vs 有 cache\n(7B模型, 32层, d=4096)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.legend(fontsize=10, prop=CJK_FONT_NAME)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')

    # --- 右图：KV Cache 显存 ---
    ax = axes[1]
    categories = ['模型参数\n(FP16)', 'KV Cache\n(batch=1)', 'KV Cache\n(batch=8)']
    values = [14, 2.1, 17.2]
    colors = ['#2196F3', '#4CAF50', '#F44336']

    bars = ax.bar(categories, values, color=colors, width=0.5, edgecolor='black', lw=0.5)
    ax.set_ylabel('显存 (GB)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('7B模型推理显存分布\n(上下文4096 tokens)', fontsize=12, fontproperties=CJK_FONT_NAME)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{val} GB', ha='center', fontsize=11, fontweight='bold')

    # 标注
    ax.annotate('KV Cache > 模型参数!', xy=(2, 17.2), xytext=(1.5, 19),
                fontsize=11, fontproperties=CJK_FONT_NAME, color='#C62828', fontweight='bold',
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#C62828'))

    ax.set_ylim(0, 22)
    ax.grid(True, axis='y', alpha=0.2)
    for label in ax.get_xticklabels():
        label.set_fontproperties(CJK_FONT_NAME)
        label.set_fontsize(9)

    plt.suptitle('KV Cache：累计计算量从 O(N³) 降到 O(N²)（每步从 O(N) 降到 O(1)）', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch4_kv_cache.png')

# ============================================================
# Ch4 - 三代语音架构对比
# ============================================================

def fig_ch4_voice_generations():
    """三代语音架构：级联→回合制→全双工"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 9))

    # --- 第一代：级联式 ---
    ax = axes[0]
    ax.set_xlim(0, 14); ax.set_ylim(0, 4)
    ax.axis('off')
    ax.text(0.2, 3.5, '第一代\n级联式', fontsize=11, fontproperties=CJK_FONT_NAME, fontweight='bold', color='#1565C0')

    blocks = [
        ('STT\n语音→文字', 2, 3, '#E3F2FD', '#1565C0'),
        ('LLM\n文字→文字', 5.5, 3, '#E8F5E9', '#2E7D32'),
        ('TTS\n文字→语音', 9, 3, '#FFEBEE', '#C62828'),
    ]
    for label, x, w, fc, ec in blocks:
        rect = FancyBboxPatch((x, 1), w, 2, boxstyle="round,pad=0.1", facecolor=fc, edgecolor=ec, lw=1.5)
        ax.add_patch(rect)
        ax.text(x+w/2, 2, label, fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color=ec)

    for x_start, x_end in [(5, 5.5), (8.5, 9)]:
        ax.annotate('', xy=(x_end, 2), xytext=(x_start, 2),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))

    # 延迟标注
    delays = [('300ms', 3.5), ('500ms', 7), ('200ms', 10.5)]
    for txt, x in delays:
        ax.text(x, 0.5, txt, fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#FF9800')
    ax.text(7, 0.0, '总延迟 1000ms+ | 信息损失：语气/停顿/情感全部丢失', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # --- 第二代：回合制 ---
    ax = axes[1]
    ax.set_xlim(0, 14); ax.set_ylim(0, 4)
    ax.axis('off')
    ax.text(0.2, 3.5, '第二代\n回合制', fontsize=11, fontproperties=CJK_FONT_NAME, fontweight='bold', color='#7B1FA2')

    # 单一模型
    rect = FancyBboxPatch((4, 1), 6, 2, boxstyle="round,pad=0.1",
                           facecolor='#F3E5F5', edgecolor='#7B1FA2', lw=1.5)
    ax.add_patch(rect)
    ax.text(7, 2.3, '单一模型 (GPT-4o)', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#7B1FA2')
    ax.text(7, 1.5, '音频 → 音频 (端到端)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 输入输出
    ax.annotate('语音输入', xy=(4, 2), xytext=(1.5, 2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#1565C0'),
                fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')
    ax.annotate('语音输出', xy=(12.5, 2), xytext=(10, 2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#C62828'),
                fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828')

    # VAD问题
    ax.text(7, 0.5, '延迟 ~500ms | VAD静音检测：用户停顿思考 → 模型抢答', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#FF9800')
    ax.text(7, 0.0, '保留了语气和情感，但"说完了没"靠猜', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # --- 第三代：全双工 ---
    ax = axes[2]
    ax.set_xlim(0, 14); ax.set_ylim(0, 4)
    ax.axis('off')
    ax.text(0.2, 3.5, '第三代\n全双工', fontsize=11, fontproperties=CJK_FONT_NAME, fontweight='bold', color='#E65100')

    # GPT-Live 交互层
    rect1 = FancyBboxPatch((1.5, 2), 5, 1.5, boxstyle="round,pad=0.1",
                            facecolor='#FFF3E0', edgecolor='#E65100', lw=1.5)
    ax.add_patch(rect1)
    ax.text(4, 3.1, '实时交互层\n(GPT-Live)', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#E65100')
    ax.text(4, 2.5, '实时对话 | <500ms', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # GPT-5.5 推理层
    rect2 = FancyBboxPatch((8, 2), 5, 1.5, boxstyle="round,pad=0.1",
                            facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect2)
    ax.text(10.5, 3.1, '深度推理层\n(GPT-5.5)', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#1565C0')
    ax.text(10.5, 2.5, '深度推理 | 3-5s', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 委托箭头（双向）
    ax.annotate('委托', xy=(8, 2.75), xytext=(6.5, 2.75),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#7B1FA2'),
                fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#7B1FA2')
    ax.annotate('返回', xy=(6.5, 2.25), xytext=(8, 2.25),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#2E7D32'),
                fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32')

    # 连续音频流
    ax.annotate('连续音频流', xy=(4, 2.0), xytext=(4, 1.2),
                arrowprops=dict(arrowstyle='<->', lw=1.5, color='#1565C0'),
                fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')

    ax.text(7, 0.5, '边听边说 | 自然应答("嗯嗯") | 委托深度任务', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#E65100')
    ax.text(7, 0.0, '不需要等用户说完才回应，10Hz决策频率', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    plt.suptitle('三代语音架构：级联 → 回合制 → 全双工', fontsize=14, y=0.98, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch4_voice_generations.png')

# ============================================================
# Ch5 - VLA 端到端流程
# ============================================================

def fig_ch5_vla_pipeline():
    """VLA架构：摄像头→ViT→LLM→动作token→电机指令"""
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.set_xlim(0, 18); ax.set_ylim(0, 8)
    ax.axis('off')

    # --- 摄像头输入 ---
    # 画一个简化的摄像头视角
    rect = FancyBboxPatch((0.3, 3), 2.5, 3, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    # 模拟场景：红色积木 + 盒子
    ax.add_patch(mpatches.Rectangle((0.8, 3.5), 0.8, 0.6, color='#F44336'))  # 红积木
    ax.add_patch(mpatches.Rectangle((1.8, 3.5), 0.7, 0.5, color='#9E9E9E'))  # 盒子
    ax.text(1.55, 6.3, '摄像头', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#1565C0')
    ax.text(1.55, 2.5, '224x224\nRGB', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # --- ViT 编码 ---
    ax.annotate('', xy=(3.5, 4.5), xytext=(2.8, 4.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

    rect = FancyBboxPatch((3.5, 3), 2.5, 3, boxstyle="round,pad=0.1",
                           facecolor='#E8F5E9', edgecolor='#2E7D32', lw=1.5)
    ax.add_patch(rect)
    ax.text(4.75, 5.2, 'ViT', fontsize=12, ha='center', fontweight='bold', color='#2E7D32')
    ax.text(4.75, 4.5, 'patch 投影\n196 token', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(4.75, 3.5, '视觉编码', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32')

    # --- 连接器 ---
    ax.annotate('', xy=(6.5, 4.5), xytext=(6.0, 4.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

    rect = FancyBboxPatch((6.5, 3.5), 1.5, 2, boxstyle="round,pad=0.1",
                           facecolor='#FFF8E1', edgecolor='#F57F17', lw=1)
    ax.add_patch(rect)
    ax.text(7.25, 4.5, '连接器\n投影', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17')

    # --- 语言指令 ---
    rect = FancyBboxPatch((6.5, 1.5), 1.5, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#F3E5F5', edgecolor='#7B1FA2', lw=1)
    ax.add_patch(rect)
    ax.text(7.25, 2.5, '"把红色\n积木放到\n盒子里"', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#7B1FA2')
    ax.text(7.25, 1.2, '语言指令', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # --- LLM ---
    ax.annotate('', xy=(9, 4.5), xytext=(8, 4.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))
    ax.annotate('', xy=(9, 3.5), xytext=(8, 2.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

    rect = FancyBboxPatch((9, 2.5), 3, 3.5, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    ax.text(10.5, 5.3, 'LLM', fontsize=12, ha='center', fontweight='bold', color='#1565C0')
    ax.text(10.5, 4.6, '(VLA 基座)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(10.5, 3.8, '视觉 token +\n文字 token', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')
    ax.text(10.5, 2.9, '→ 自回归生成', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # --- 动作 token 输出 ---
    ax.annotate('', xy=(13, 4.5), xytext=(12, 4.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

    # 7DOF x 4步 = 28 token
    for step in range(4):
        for dim in range(7):
            x = 12.5 + step * 0.5
            y = 5.5 - dim * 0.3
            color = plt.cm.viridis(dim / 7)
            ax.add_patch(mpatches.Rectangle((x, y), 0.35, 0.2, color=color, alpha=0.8))
    ax.text(13.7, 6.2, '动作 token', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#FF9800')
    ax.text(13.7, 2.8, '7DOF x 4步\n= 28 token', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # --- 动作执行 ---
    ax.annotate('', xy=(15.5, 4.5), xytext=(14.8, 4.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

    rect = FancyBboxPatch((15.5, 3), 2.2, 3, boxstyle="round,pad=0.1",
                           facecolor='#FFEBEE', edgecolor='#C62828', lw=1.5)
    ax.add_patch(rect)
    ax.text(16.6, 5.2, '机械臂', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#C62828')
    ax.text(16.6, 4.5, '7个关节\n力矩/角度', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(16.6, 3.5, '抓→搬→放', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828')

    # --- 底部：延迟分解 ---
    delays = [
        ('摄像头\n33ms', 1.55, '#1565C0'),
        ('ViT\n10ms', 4.75, '#2E7D32'),
        ('连接器\n2ms', 7.25, '#F57F17'),
        ('LLM\n60-90ms', 10.5, '#1565C0'),
        ('电机\n50ms', 16.6, '#C62828'),
    ]
    for txt, x, color in delays:
        ax.text(x, 0.5, txt, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color=color)

    # 延迟箭头
    ax.annotate('', xy=(17, 0.8), xytext=(1, 0.8),
                arrowprops=dict(arrowstyle='->', lw=1, color='gray', alpha=0.5))
    ax.text(9, 0.1, '总延迟 ~155-185ms (约5-6帧@30fps, 5Hz控制周期内完成)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    ax.set_title('VLA 架构：摄像头 → ViT → LLM → 动作 token → 机械臂', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch5_vla_pipeline.png')

# ============================================================
# P1 配图
# ============================================================

def fig_ch1_token_zoo():
    """六种模态的token化全景：万物皆token"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis('off')

    modalities = [
        ('文字', 'BPE\n子词切分', '#E3F2FD', '#1565C0', '今天\n天气不错', '~20 tokens'),
        ('图像', 'ViT\npatch 切分', '#E8F5E9', '#2E7D32', '224x224\n图片', '196 tokens'),
        ('音频', 'EnCodec\n离散码本', '#FFF3E0', '#E65100', '1秒\n24kHz', '75 tokens'),
        ('视频', 'Tubelet\n时空块', '#F3E5F5', '#7B1FA2', '16帧\n224x224', '1568 tokens'),
        ('3D', 'Point\nTransformer', '#FFEBEE', '#C62828', '10万点\n点云', '~1000 tokens'),
        ('触觉', 'VQ-VAE\n力反馈', '#E0F7FA', '#006064', '1秒\n1000Hz', '~30 tokens'),
    ]

    for i, (name, method, fc, ec, inp, tokens) in enumerate(modalities):
        x = 0.5 + i * 2.2
        # 模态名称
        ax.text(x + 0.8, 7.3, name, fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color=ec)
        # 输入框
        rect = FancyBboxPatch((x, 5.5), 1.6, 1.2, boxstyle="round,pad=0.1", facecolor='white', edgecolor=ec, lw=1.2)
        ax.add_patch(rect)
        ax.text(x + 0.8, 6.1, inp, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
        # 箭头
        ax.annotate('', xy=(x+0.8, 5.0), xytext=(x+0.8, 5.4),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color=ec))
        ax.text(x + 0.8, 5.2, method, fontsize=7, fontproperties=CJK_FONT_NAME, ha='center', color=ec)
        # token输出
        rect = FancyBboxPatch((x, 3.2), 1.6, 1.5, boxstyle="round,pad=0.1", facecolor=fc, edgecolor=ec, lw=1.5)
        ax.add_patch(rect)
        ax.text(x + 0.8, 4.3, 'token', fontsize=9, ha='center', color=ec, fontweight='bold')
        ax.text(x + 0.8, 3.6, tokens, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color=ec)
        # 汇聚箭头
        ax.annotate('', xy=(7, 2.0), xytext=(x+0.8, 3.1),
                    arrowprops=dict(arrowstyle='->', lw=0.8, color='gray', alpha=0.5))

    # 底部：统一token序列
    rect = FancyBboxPatch((2, 0.8), 10, 1.2, boxstyle="round,pad=0.1",
                           facecolor='#FFFDE7', edgecolor='#F57F17', lw=1.5)
    ax.add_patch(rect)
    ax.text(7, 1.8, '统一的 token 序列', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    ax.text(7, 1.2, '喂进同一个 Transformer', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    ax.set_title('万物皆可 token 化：六种模态 → 统一向量序列', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch1_token_zoo.png')

def fig_ch1_clip_space():
    """CLIP：图文在同一向量空间对齐"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # --- 左图：4x4相似度矩阵 ---
    ax = axes[0]
    # 模拟相似度矩阵
    S = np.array([
        [0.80, 0.12, 0.08, 0.15],
        [0.10, 0.82, 0.20, 0.05],
        [0.06, 0.18, 0.85, 0.10],
        [0.14, 0.08, 0.12, 0.78],
    ])
    im = ax.imshow(S, cmap='YlOrRd', vmin=0, vmax=1, aspect='auto')
    # 标注
    labels_img = ['猫图', '狗图', '车图', '房图']
    labels_txt = ['"猫"', '"狗"', '"车"', '"房"']
    for i in range(4):
        for j in range(4):
            color = 'white' if S[i,j] > 0.5 else 'black'
            weight = 'bold' if i == j else 'normal'
            ax.text(j, i, f'{S[i,j]:.2f}', ha='center', va='center', fontsize=11, color=color, fontweight=weight)
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    ax.set_xticklabels(labels_txt, fontproperties=CJK_FONT_NAME, fontsize=10)
    ax.set_yticklabels(labels_img, fontproperties=CJK_FONT_NAME, fontsize=10)
    ax.set_xlabel('文本向量', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('图像向量', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_title('4x4 余弦相似度矩阵\n(对角线=正样本)', fontsize=11, fontproperties=CJK_FONT_NAME)
    # 对角线高亮
    for i in range(4):
        ax.add_patch(mpatches.Rectangle((i-0.5, i-0.5), 1, 1, fill=False, edgecolor='green', lw=2.5))
    plt.colorbar(im, ax=ax, shrink=0.8)

    # --- 右图：向量空间对齐 ---
    ax = axes[1]
    ax.set_xlim(-3, 3); ax.set_ylim(-2.5, 2.5)
    # 画几个图文对在空间中靠近
    pairs = [
        ('猫', 'cat', -1.8, 1.5, '#E91E63'),
        ('狗', 'dog', -1.2, 0.8, '#2196F3'),
        ('车', 'car', 1.5, -0.5, '#4CAF50'),
        ('房', 'house', 1.8, 1.2, '#FF9800'),
    ]
    for cn, en, x, y, color in pairs:
        # 图像点（圆）
        ax.scatter(x - 0.15, y, s=150, c=color, marker='o', zorder=5, edgecolors='black', lw=0.5)
        ax.text(x - 0.15, y + 0.35, f'[{cn}图]', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color=color)
        # 文字点（方）
        ax.scatter(x + 0.15, y - 0.15, s=120, c=color, marker='s', zorder=5, edgecolors='black', lw=0.5, alpha=0.6)
        ax.text(x + 0.15, y - 0.5, f'"{cn}"', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color=color)
        # 连接线
        ax.plot([x - 0.15, x + 0.15], [y, y - 0.15], '--', color=color, alpha=0.5, lw=1)

    # 区域标注
    ax.text(-2.5, 2.2, '动物区域', fontsize=10, fontproperties=CJK_FONT_NAME, color='gray', alpha=0.6)
    ax.text(1.5, 2.2, '物体区域', fontsize=10, fontproperties=CJK_FONT_NAME, color='gray', alpha=0.6)
    ax.axvline(x=0, color='gray', ls=':', alpha=0.3)

    # 图例
    ax.scatter([], [], s=100, c='gray', marker='o', label='图像向量')
    ax.scatter([], [], s=80, c='gray', marker='s', alpha=0.6, label='文本向量')
    ax.legend(fontsize=10, prop=CJK_FONT_NAME, loc='lower left')

    ax.set_title('CLIP 向量空间：图文对齐', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.grid(True, alpha=0.15)
    ax.set_xlabel('维度 1', fontsize=10, fontproperties=CJK_FONT_NAME); ax.set_ylabel('维度 2', fontsize=10, fontproperties=CJK_FONT_NAME)

    plt.suptitle('CLIP：让图片和文字说同一种语言', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch1_clip_space.png')

def fig_ch2_latent_space():
    """潜空间：万能草稿纸概念图"""
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis('off')

    # 中心：潜空间
    from matplotlib.patches import Ellipse
    ellipse = Ellipse((7, 4), 5, 3.2, facecolor='#FFFDE7', edgecolor='#F57F17', lw=2.5, alpha=0.9)
    ax.add_patch(ellipse)
    ax.text(7, 4.5, '潜空间', fontsize=16, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    ax.text(7, 3.8, '(万能草稿纸)', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(7, 3.2, '稠密 · 可组合 · 多义叠加', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17')

    # 三个性质标注
    props = [
        ('稠密', '猫和狗的向量\n比猫和民主近', 5.5, 5.8, '#1565C0'),
        ('可组合', '国王-男+女\n≈女王', 8.5, 5.8, '#2E7D32'),
        ('多义叠加', '一个方向同时\n编码多个概念', 7, 2.2, '#7B1FA2'),
    ]
    for name, desc, x, y, color in props:
        ax.text(x, y, name, fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color=color, fontweight='bold')
        ax.text(x, y - 0.7, desc, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color=color)

    # 左侧：外界输入
    inputs = [
        ('文字 token', 0.5, 6.5, '#1565C0'),
        ('图像 token', 0.5, 5.0, '#2E7D32'),
        ('音频 token', 0.5, 3.5, '#E65100'),
        ('动作 token', 0.5, 2.0, '#7B1FA2'),
    ]
    for name, x, y, color in inputs:
        rect = FancyBboxPatch((x, y - 0.3), 1.8, 0.7, boxstyle="round,pad=0.1",
                               facecolor='white', edgecolor=color, lw=1.2)
        ax.add_patch(rect)
        ax.text(x + 0.9, y, name, fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color=color)
        ax.annotate('', xy=(4.5, 4), xytext=(x + 1.8, y),
                    arrowprops=dict(arrowstyle='->', lw=1, color=color, alpha=0.6))

    ax.text(1.4, 7.3, '外界模态\n(token化压入)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 右侧：能力输出
    outputs = [
        ('写作', 11.7, 6.5, '#1565C0'),
        ('编程', 11.7, 5.0, '#2E7D32'),
        ('思考', 11.7, 3.5, '#E65100'),
        ('多模态', 11.7, 2.0, '#7B1FA2'),
    ]
    for name, x, y, color in outputs:
        rect = FancyBboxPatch((x, y - 0.3), 1.8, 0.7, boxstyle="round,pad=0.1",
                               facecolor='white', edgecolor=color, lw=1.2)
        ax.add_patch(rect)
        ax.text(x + 0.9, y, name, fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color=color)
        ax.annotate('', xy=(x, y), xytext=(9.5, 4),
                    arrowprops=dict(arrowstyle='->', lw=1, color=color, alpha=0.6))

    ax.text(12.6, 7.3, '能力表达\n(不同接口)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 底部心法
    ax.text(7, 0.5, '基座在潜空间里做通用推理，写作/编程/思考是同一推理经不同接口的表达',
            fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17', fontstyle='italic')

    ax.set_title('潜空间：基座里到底在跑什么', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch2_latent_space.png')

def fig_ch2_multimodal_arch():
    """三件套架构 vs 原生多模态对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # --- 左：三件套 ---
    ax = axes[0]
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.axis('off')

    # 视觉编码器
    rect = FancyBboxPatch((0.5, 5), 2.5, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#E8F5E9', edgecolor='#2E7D32', lw=1.5)
    ax.add_patch(rect)
    ax.text(1.75, 6.1, '视觉编码器', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#2E7D32')
    ax.text(1.75, 5.4, 'CLIP ViT\n(冻结, 300M)', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # 连接器
    ax.annotate('', xy=(4, 5.75), xytext=(3, 5.75),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))
    rect = FancyBboxPatch((4, 5), 2, 1.5, boxstyle="round,pad=0.1",
                           facecolor='#FFF8E1', edgecolor='#F57F17', lw=1.5)
    ax.add_patch(rect)
    ax.text(5, 6.1, '连接器', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    ax.text(5, 5.3, 'MLP\n(20M, 可训)', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    # LLM
    ax.annotate('', xy=(8, 5.75), xytext=(6, 5.75),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='gray'))
    rect = FancyBboxPatch((7.5, 4.5), 2, 2.5, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    ax.text(8.5, 6.3, 'LLM', fontsize=11, ha='center', fontweight='bold', color='#1565C0')
    ax.text(8.5, 5.5, 'LLaMA\n(7B)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(8.5, 4.8, '文字续写', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')

    # 文字输入
    rect = FancyBboxPatch((4, 2.5), 2, 1, boxstyle="round,pad=0.1",
                           facecolor='#F3E5F5', edgecolor='#7B1FA2', lw=1)
    ax.add_patch(rect)
    ax.text(5, 3, '文字 token', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#7B1FA2')
    ax.annotate('', xy=(8.5, 4.4), xytext=(5, 3.6),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#7B1FA2'))

    # 标注：先训文本再接视觉
    ax.text(5, 1.5, '先训文本 → 再接视觉 (后接式)', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(5, 0.7, '代表: LLaVA, BLIP-2', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')

    ax.set_title('三件套架构', fontsize=12, fontproperties=CJK_FONT_NAME, fontweight='bold')

    # --- 右：原生多模态 ---
    ax = axes[1]
    ax.set_xlim(0, 10); ax.set_ylim(0, 8)
    ax.axis('off')

    # 统一模型
    rect = FancyBboxPatch((2.5, 3.5), 5, 3.5, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=2)
    ax.add_patch(rect)
    ax.text(5, 6.2, '统一 Transformer', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#1565C0')
    ax.text(5, 5.4, '每层 Attention 都允许\n图文 token 直接交互', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(5, 4.2, '从头联合训练', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0', fontweight='bold')

    # 多模态输入
    inputs = [
        ('文本', 1.5, '#1565C0'),
        ('图像', 3.5, '#2E7D32'),
        ('音频', 5.5, '#E65100'),
        ('视频', 7.5, '#7B1FA2'),
    ]
    for name, x, color in inputs:
        rect = FancyBboxPatch((x - 0.5, 7.2), 1.2, 0.6, boxstyle="round,pad=0.1",
                               facecolor='white', edgecolor=color, lw=1)
        ax.add_patch(rect)
        ax.text(x + 0.1, 7.5, name, fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color=color)
        ax.annotate('', xy=(x + 0.1, 7.0), xytext=(x + 0.1, 7.2),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color=color))

    ax.text(5, 2.5, '从预训练第一步就混合所有模态', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(5, 1.5, '代表: GPT-4o, Gemini, InternVL3', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')
    ax.text(5, 0.7, '视觉不是外挂，是原生能力', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32', fontstyle='italic')

    ax.set_title('原生多模态', fontsize=12, fontproperties=CJK_FONT_NAME, fontweight='bold')

    plt.suptitle('多模态基座：三件套 vs 原生多模态', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch2_multimodal_arch.png')

def fig_ch3_grpo_advantage():
    """GRPO组内相对优势的数字演示"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # --- 左图：8个回答的奖励和优势 ---
    ax = axes[0]
    responses = [f'$y_{{{i+1}}}$' for i in range(8)]
    rewards = [1, 0, 1, 0, 0, 1, 0, 0]
    advantages = [1.29, -0.77, 1.29, -0.77, -0.77, 1.29, -0.77, -0.77]

    colors = ['#4CAF50' if r == 1 else '#EF5350' for r in rewards]
    bars = ax.bar(responses, advantages, color=colors, width=0.6, edgecolor='black', lw=0.5)
    ax.axhline(y=0, color='black', lw=1)

    # 标注奖励值
    for i, (bar, r, a) in enumerate(zip(bars, rewards, advantages)):
        y_pos = a + 0.08 if a > 0 else a - 0.15
        ax.text(i, y_pos, f'R={r}\nA={a:+.2f}', ha='center', fontsize=8, fontweight='bold',
                color='#2E7D32' if a > 0 else '#C62828')

    ax.set_ylabel('组内相对优势 $\\hat{A}_i$', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('8个回答的奖励与优势\n$\\hat{A}_i=(R_i-\\mu)/\\sigma$  (mean=0.375, std=0.484)', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_ylim(-1.3, 1.8)
    ax.grid(True, axis='y', alpha=0.2)

    # 图例
    ax.scatter([], [], c='#4CAF50', marker='s', s=80, label='正确 (R=1) → 正优势 (被强化)')
    ax.scatter([], [], c='#EF5350', marker='s', s=80, label='错误 (R=0) → 负优势 (被弱化)')
    ax.legend(fontsize=9, prop=CJK_FONT_NAME, loc='upper right')

    # --- 右图：GRPO vs PPO 对比 ---
    ax = axes[1]
    ax.axis('off')
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)

    # PPO
    rect = FancyBboxPatch((0.5, 6), 4, 3, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    ax.text(2.5, 8.5, 'PPO', fontsize=13, ha='center', fontweight='bold', color='#1565C0')
    ppo_items = ['策略模型', '参考模型', '奖励模型', '价值网络 (critic)']
    for i, item in enumerate(ppo_items):
        ax.text(2.5, 8.0 - i * 0.45, f'• {item}', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')
    ax.text(2.5, 6.3, '4个模型, 显存翻倍', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828')

    # GRPO
    rect = FancyBboxPatch((5.5, 6), 4, 3, boxstyle="round,pad=0.1",
                           facecolor='#E8F5E9', edgecolor='#2E7D32', lw=1.5)
    ax.add_patch(rect)
    ax.text(7.5, 8.5, 'GRPO', fontsize=13, ha='center', fontweight='bold', color='#2E7D32')
    grpo_items = ['策略模型', '参考模型', '奖励模型', '组内相对排名 (代替critic)']
    for i, item in enumerate(grpo_items):
        color = '#2E7D32' if i < 3 else '#C62828'
        ax.text(7.5, 8.0 - i * 0.45, f'• {item}', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color=color)
    ax.text(7.5, 6.3, '3个模型, 省一半显存', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32')

    # 共同点
    rect = FancyBboxPatch((1.5, 3), 7, 2.5, boxstyle="round,pad=0.1",
                           facecolor='#FFFDE7', edgecolor='#F57F17', lw=1)
    ax.add_patch(rect)
    ax.text(5, 5.0, '共同保留', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    common = ['clip 机制 (限制更新幅度)', 'KL 惩罚 (不偏离参考模型)', '策略梯度上升']
    for i, item in enumerate(common):
        ax.text(5, 4.5 - i * 0.4, f'• {item}', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17')

    # 核心差异
    ax.text(5, 1.5, '核心差异：优势计算', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#7B1FA2')
    ax.text(2.5, 0.8, 'PPO: 价值网络估计', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')
    ax.text(7.5, 0.8, 'GRPO: 组内相对排名', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#2E7D32')

    plt.suptitle('GRPO：砍掉价值网络，用组内相对排名代替', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch3_grpo_advantage.png')

def fig_ch5_sim_to_real():
    """Sim-to-Real：模拟器→领域随机化→真实部署"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14); ax.set_ylim(0, 7)
    ax.axis('off')

    # 三个阶段
    stages = [
        ('模拟器\n(MuJoCo)', 1.5, '#E3F2FD', '#1565C0', '训练\n成功率 ~100%', 5.5),
        ('领域随机化\n(Domain Rand.)', 6.5, '#FFF8E1', '#F57F17', '随机化:\n摩擦/质量/光照/相机', 3.5),
        ('真实部署\n(Franka Panda)', 11.5, '#E8F5E9', '#2E7D32', '无随机化 60%\n+物理 85%\n+视觉 95%', 5.5),
    ]

    for name, x, fc, ec, desc, y_desc in stages:
        rect = FancyBboxPatch((x - 1.3, 3), 2.6, 2.5, boxstyle="round,pad=0.1",
                               facecolor=fc, edgecolor=ec, lw=1.5)
        ax.add_patch(rect)
        ax.text(x, 4.8, name, fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color=ec)
        ax.text(x, 3.8, desc, fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color=ec)

    # 箭头
    for x_start, x_end in [(2.8, 5.2), (7.8, 10.2)]:
        ax.annotate('', xy=(x_end, 4.25), xytext=(x_start, 4.25),
                    arrowprops=dict(arrowstyle='->', lw=2, color='gray'))

    # 随机化参数表
    params = [
        ('摩擦系数', '0.5', '[0.1, 1.0]'),
        ('物体质量', '1.0 kg', '[0.5, 2.0] kg'),
        ('光照强度', '500 lux', '[100, 1000] lux'),
        ('相机位置', '固定', '±5cm 偏移'),
    ]
    ax.text(6.5, 2.3, '随机化参数空间', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    for i, (param, default, rand) in enumerate(params):
        y = 1.8 - i * 0.4
        ax.text(4.5, y, param, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
        ax.text(6.0, y, f'默认: {default}', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
        ax.text(8.5, y, f'随机: {rand}', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17')

    # Gap标注
    ax.annotate('Sim-to-Real\nGap', xy=(9, 4.25), xytext=(9, 0.5),
                arrowprops=dict(arrowstyle='<->', lw=2, color='#C62828'),
                fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828', fontweight='bold')

    # 经验教训
    ax.text(1.5, 0.5, '被随机化的维度能迁移\n没被随机化的维度会失效', fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828')

    ax.set_title('Sim-to-Real：从模拟器到现实', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch5_sim_to_real.png')

def fig_ch6_capability_stack():
    """五层能力栈的汇流"""
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.set_xlim(-0.5, 8.0)
    ax.set_ylim(-0.5, 8.5)
    ax.axis('off')

    # 左侧五层竖排分组：前三章 = 感知-认知栈，后两章 = 输出端
    # 颜色分组：前三章冷色系蓝色渐变区分，后两章暖色系红色渐变区分
    layers = [
        # 感知-认知栈（前三章），整体垂直居中 -> y从1.5开始，蓝色系不同深浅
        ('Ch1 萃取', '把世界变成 token', '#E8F5FD', '#1565C0', 1.5, 1.8, 'left'),
        ('Ch2 筑基', '预训练→潜空间\n能力涌现', '#D1EFFF', '#0D47A1', 3.2, 1.8, 'left'),
        ('Ch3 炼灵', 'RLHF/DPO\n选对的话', '#BBDEFB', '#1976D2', 4.9, 1.8, 'left'),
        # 输出端（后两章），垂直居中对齐 -> 整体中心和左侧相同，红色系不同深浅
        ('Ch4 应变', 'KV Cache/流式\n实时交互', '#FFF3E0', '#F57C00', 2.8, 1.8, 'right'),
        ('Ch5 行动', 'VLA/Sim-to-Real\n物理世界', '#FFEBEE', '#C62828', 4.7, 1.8, 'right'),
    ]

    # 画五层，分左右两组，加宽框避免强制换行
    for name, desc, fc, ec, y, h, group in layers:
        if group == 'left':
            x = 0.5
        else:
            x = 4.5
        rect = FancyBboxPatch((x, y), 2.2, h-0.1, boxstyle="round,pad=0.15",
                               facecolor=fc, edgecolor=ec, lw=1.5)
        ax.add_patch(rect)
        # 分行排版，上下留空，不压线
        ax.text(x + 0.6, y + h/2 + 0.25, name, fontsize=11, fontproperties=CJK_FONT_NAME, ha='left', va='center', fontweight='bold', color=ec)
        ax.text(x + 0.6, y + h/2 - 0.25, desc, fontsize=8, fontproperties=CJK_FONT_NAME, ha='left', va='center', color=ec)

    # 分组大括号
    # 感知-认知栈：左侧列前三章，y 1.5 ~ 4.9+1.8 = 6.7 -> 垂直范围中心 ~4.1
    ax.plot([0.0, 0.0], [1.5, 6.7], '-', lw=2, color='#1565C0')
    ax.text(-0.3, 4.1, '感知-认知栈', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0', rotation=90, fontweight='bold')
    # 输出端：右侧列后两章，y 2.8 ~ 4.7+1.8 = 6.5 -> 垂直中心对齐左侧
    ax.plot([7.2, 7.2], [2.8, 6.5], '-', lw=2, color='#C62828')
    ax.text(7.5, 4.65, '输出端', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#C62828', rotation=90, fontweight='bold')

    # 标注Ch4-Ch5共享架构模式（同在输出端），虚线标注
    ax.plot([3.8, 3.8], [2.8, 6.5], '--', lw=2, color='#9C27B0')
    ax.text(4.0, 4.65, '共享\n架构模式\n实时+深度', fontsize=8, fontproperties=CJK_FONT_NAME, ha='left', va='center', color='#9C27B0', fontweight='bold')

    # 底部标题说明结构关系
    ax.text(3.75, 0.2, '全书结构：五章递进，前三章搭起感知-认知栈，后两章接不同输出模态', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    ax.set_title('五层能力栈结构', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch6_capability_stack.png')

# ============================================================
# P2 配图
# ============================================================

def fig_ch1_modality_scale():
    """多模态token规模对比"""
    fig, ax = plt.subplots(figsize=(12, 5.5))

    modalities = ['一句话\n"今天天气不错"', '图片\n224x224', '音频1s\nEnCodec', '音频1s\nmel-spec', '视频\n16帧224x224', '3D点云\n10万点', '触觉1s\n1000Hz']
    raw_numbers = [20, 150528, 24000, 8000, 2408448, 300000, 1000]
    token_counts = [20, 196, 75, 100, 1568, 1000, 30]
    colors = ['#1565C0', '#2E7D32', '#E65100', '#FF9800', '#7B1FA2', '#C62828', '#006064']

    x = np.arange(len(modalities))
    width = 0.35

    # 对数刻度
    ax2 = ax.twinx()
    bars1 = ax.bar(x - width/2, token_counts, width, color=colors, alpha=0.8, edgecolor='black', lw=0.5, label='token 数')
    bars2 = ax2.bar(x + width/2, raw_numbers, width, color=colors, alpha=0.3, edgecolor='gray', lw=0.5, label='原始数字量')

    ax.set_ylabel('token 数', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax2.set_ylabel('原始数字量 (对数)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax2.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(modalities, fontproperties=CJK_FONT_NAME, fontsize=8)
    ax.set_title('多模态 token 规模对比：同一句话 vs 一张图 vs 一秒音频', fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold')

    # 标注token数
    for bar, val in zip(bars1, token_counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 30,
                str(val), ha='center', fontsize=9, fontweight='bold')

    ax.legend(loc='upper left', fontsize=9, prop=CJK_FONT_NAME)
    ax2.legend(loc='upper right', fontsize=9, prop=CJK_FONT_NAME)
    ax.grid(True, axis='y', alpha=0.2)
    plt.tight_layout()
    save(fig, 'fig_ch1_modality_scale.png')

def fig_ch2_scaling_law():
    """Scaling Law与涌现现象"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # --- 左图：Scaling Law 幂律曲线 ---
    ax = axes[0]
    # 模拟 loss 随算力的幂律下降
    compute = np.logspace(20, 26, 100)
    loss = 2.5 * (compute / 1e20) ** (-0.05)

    ax.plot(compute, loss, 'b-', lw=2.5)
    ax.fill_between(compute, loss * 0.9, loss * 1.1, alpha=0.15, color='blue')

    # 标注模型点
    models = [
        ('GPT-2', 3e21, 2.2, '#9E9E9E'),
        ('GPT-3', 3e23, 1.75, '#FF9800'),
        ('Chinchilla', 6e23, 1.65, '#4CAF50'),
        ('LLaMA-3-70B', 6e24, 1.4, '#2196F3'),
    ]
    for name, c, l, color in models:
        ax.scatter(c, l, s=80, c=color, zorder=5, edgecolors='black', lw=0.5)
        ax.annotate(name, (c, l), textcoords="offset points", xytext=(8, 8),
                    fontsize=9, fontproperties=CJK_FONT_NAME, color=color, fontweight='bold')

    ax.set_xscale('log')
    ax.set_xlabel('训练算力 (FLOPs)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('Cross-entropy Loss', fontsize=12)
    ax.set_title('Scaling Law: Loss 随算力平滑下降\n(幂律, Kaplan 2020 / Chinchilla 2022)', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.grid(True, alpha=0.3)

    # GPT-3 vs Chinchilla 对比标注：同算力，不同配方
    ax.annotate('GPT-3: 175B x 300B tokens\n(参数多, 数据少)', xy=(3e23, 1.75),
                xytext=(8e21, 2.5), fontsize=8.5, fontproperties=CJK_FONT_NAME, color='#FF9800',
                arrowprops=dict(arrowstyle='->', lw=1.2, color='#FF9800'))
    ax.annotate('Chinchilla: 70B x 1.4T tokens\n(参数少, 数据多)\n同算力 → loss 更低', xy=(6e23, 1.65),
                xytext=(8e21, 1.35), fontsize=8.5, fontproperties=CJK_FONT_NAME, color='#4CAF50',
                arrowprops=dict(arrowstyle='->', lw=1.2, color='#4CAF50'))

    # --- 右图：涌现现象 ---
    ax = axes[1]
    params = np.logspace(9, 12, 100)

    # 涌现曲线（sigmoid突变）
    def emergence_curve(x, threshold, sharpness):
        return 1 / (1 + np.exp(-sharpness * (np.log10(x) - np.log10(threshold))))

    # 多步算术
    ax.plot(params, emergence_curve(params, 5e10, 15) * 100, 'r-', lw=2.5, label='多步算术')
    # 上下文学习
    ax.plot(params, emergence_curve(params, 1e10, 12) * 100, 'b-', lw=2.5, label='上下文学习 (ICL)')
    # 指令跟随
    ax.plot(params, emergence_curve(params, 2e11, 10) * 100, 'g-', lw=2.5, label='指令跟随')

    # 阈值标注
    ax.axvline(x=1e10, color='blue', ls='--', alpha=0.3)
    ax.axvline(x=5e10, color='red', ls='--', alpha=0.3)

    ax.set_xscale('log')
    ax.set_xlabel('参数量', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('准确率 (%)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('涌现：能力在阈值处突然跳变（示意曲线）\n(Wei 2022 / Schaeffer 2023 争论)', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.legend(fontsize=9, prop=CJK_FONT_NAME, loc='center right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-5, 105)

    # 争论标注
    ax.text(2e9, 50, 'Schaeffer:\n指标幻觉?\nvs\nWei: 真实跃迁',
            fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='#7B1FA2',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#F3E5F5', alpha=0.8))

    plt.suptitle('Scaling Law 与涌现', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch2_scaling_law.png')

def fig_ch3_reward_hacking():
    """奖励黑客：RM分 vs 人评 分叉曲线"""
    fig, ax = plt.subplots(figsize=(12, 5))

    rounds = np.arange(0, 35)

    # RM分持续上升
    rm_score = 3 + rounds * 0.15
    # 人评先升后降
    human_score = np.where(rounds <= 5, 3 + rounds * 0.3,
                  np.where(rounds <= 15, 4.5 - (rounds - 5) * 0.05,
                           4.0 - (rounds - 15) * 0.08))

    ax.plot(rounds, rm_score, 'r-', lw=2.5, label='RM 分 (奖励模型)', marker='o', ms=4)
    ax.plot(rounds, human_score, 'b-', lw=2.5, label='人评分数', marker='s', ms=4)

    # 分叉区域
    ax.fill_between(rounds, human_score, rm_score, where=(rm_score > human_score),
                    alpha=0.15, color='red', label='黑客区域 (RM高/人评低)')

    # 关键标注点
    annotations = [
        (0, '短句\n"基本可用"', 3, 3.5),
        (5, '三点列表\n"清晰了"', 4.5, 4.8),
        (15, '分节+列表 200t\n"冗余"', 4.0, 5.5),
        (30, '客套+泛论 500t\n"太长"', 2.8, 7.5),
    ]
    for r, desc, h, rm in annotations:
        ax.annotate(desc, (r, rm), textcoords="offset points", xytext=(10, 10),
                    fontsize=8, fontproperties=CJK_FONT_NAME, color='#C62828',
                    arrowprops=dict(arrowstyle='->', lw=1, color='#C62828'))

    ax.set_xlabel('PPO 训练轮次', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_ylabel('分数', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('奖励黑客：RM 分持续上升，人评却停在下落\n(RM 与人评的分歧 = 黑客的痕迹)', fontsize=12, fontproperties=CJK_FONT_NAME, fontweight='bold')
    ax.legend(fontsize=10, prop=CJK_FONT_NAME, loc='center left')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(2, 9)

    plt.tight_layout()
    save(fig, 'fig_ch3_reward_hacking.png')

def fig_ch3_jailbreak():
    """多模态越狱：对抗patch从优化到攻破"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # --- 左图：对抗patch优化过程 ---
    ax = axes[0]
    steps = [0, 20, 50, 100]
    break_rate = [0, 15, 60, 95]
    loss = [2.30, 1.80, 0.90, 0.15]

    ax2 = ax.twinx()
    bars = ax.bar([str(s) for s in steps], break_rate, color=['#4CAF50', '#FF9800', '#F44336', '#C62828'],
                  width=0.5, edgecolor='black', lw=0.5, alpha=0.8)
    ax2.plot([str(s) for s in steps], loss, 'ko-', lw=2, ms=8)

    for bar, val in zip(bars, break_rate):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{val}%', ha='center', fontsize=11, fontweight='bold')

    ax.set_ylabel('攻破率 (%)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax2.set_ylabel('Loss', fontsize=12)
    ax.set_xlabel('优化步数', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('对抗 patch 优化过程\n32x32=1024个像素的梯度下降', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_ylim(0, 110)

    # --- 右图：拦截率对比 ---
    ax = axes[1]
    attacks = ['纯文本\n有害请求', '文字嵌入\n图片', '对抗\npatch']
    rates = [99, 40, 10]
    colors = ['#4CAF50', '#FF9800', '#F44336']

    bars = ax.barh(attacks, rates, color=colors, height=0.5, edgecolor='black', lw=0.5)
    for bar, val in zip(bars, rates):
        ax.text(val + 2, bar.get_y() + bar.get_height()/2,
                f'{val}%', va='center', fontsize=12, fontweight='bold')

    ax.set_xlabel('拦截率 (%)', fontsize=12, fontproperties=CJK_FONT_NAME)
    ax.set_title('不同攻击方式的拦截率\n视觉通道是薄弱环节', fontsize=11, fontproperties=CJK_FONT_NAME)
    ax.set_xlim(0, 115)
    ax.invert_yaxis()
    for label in ax.get_yticklabels():
        label.set_fontproperties(CJK_FONT_NAME)
        label.set_fontsize(9)
    ax.grid(True, axis='x', alpha=0.2)

    # 标注
    ax.annotate('文本护栏强', xy=(99, 0), xytext=(85, 0.5),
                fontsize=9, fontproperties=CJK_FONT_NAME, color='#4CAF50',
                arrowprops=dict(arrowstyle='->', color='#4CAF50'))
    ax.annotate('视觉通道弱', xy=(10, 2), xytext=(50, 1.8),
                fontsize=9, fontproperties=CJK_FONT_NAME, color='#F44336',
                arrowprops=dict(arrowstyle='->', color='#F44336'))

    plt.suptitle('多模态越狱：视觉通道的攻击面', fontsize=14, y=1.02, fontproperties=CJK_FONT_NAME, fontweight='bold')
    plt.tight_layout()
    save(fig, 'fig_ch3_jailbreak.png')

def fig_ch5_helix_layered():
    """Figure Helix 分层决策：System 1 + System 2"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis('off')

    # System 2: 低频场景理解
    rect = FancyBboxPatch((7.5, 4.5), 5.5, 2.5, boxstyle="round,pad=0.1",
                           facecolor='#E3F2FD', edgecolor='#1565C0', lw=1.5)
    ax.add_patch(rect)
    ax.text(10.25, 6.3, 'System 2: LLM (低频)', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#1565C0')
    ax.text(10.25, 5.6, '场景理解 · 任务规划 · 自然语言', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(10.25, 5.0, '频率: ~1-5 Hz', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')

    # System 1: 高频动作控制
    rect = FancyBboxPatch((1, 4.5), 5.5, 2.5, boxstyle="round,pad=0.1",
                           facecolor='#FFF3E0', edgecolor='#E65100', lw=1.5)
    ax.add_patch(rect)
    ax.text(3.75, 6.3, 'System 1: 控制器 (高频)', fontsize=11, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#E65100')
    ax.text(3.75, 5.6, '关节力矩 · 路径执行 · 避障', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
    ax.text(3.75, 5.0, '频率: ~50-100 Hz', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#E65100')

    # 双向通信
    ax.annotate('高层指令\n(子目标)', xy=(7.5, 5.75), xytext=(6.5, 5.75),
                arrowprops=dict(arrowstyle='->', lw=2, color='#1565C0'),
                fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0')
    ax.annotate('状态反馈\n(传感器)', xy=(6.5, 5.0), xytext=(7.5, 5.0),
                arrowprops=dict(arrowstyle='->', lw=2, color='#E65100'),
                fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#E65100')

    # 时序对比
    # System 1 时间轴
    ax.text(3.75, 3.8, 'System 1 时间轴', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#E65100', fontweight='bold')
    for i in range(10):
        x = 1 + i * 0.55
        ax.add_patch(mpatches.Rectangle((x, 3.2), 0.4, 0.3, facecolor='#FFE0B2', edgecolor='#E65100', lw=0.5))
    ax.text(6.5, 3.35, '50Hz', fontsize=8, fontproperties=CJK_FONT_NAME, color='#E65100')

    # System 2 时间轴
    ax.text(10.25, 3.8, 'System 2 时间轴', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='#1565C0', fontweight='bold')
    for i in range(3):
        x = 7.5 + i * 1.8
        ax.add_patch(mpatches.Rectangle((x, 3.2), 0.8, 0.3, facecolor='#BBDEFB', edgecolor='#1565C0', lw=0.5))
    ax.text(13.0, 3.35, '2Hz', fontsize=8, fontproperties=CJK_FONT_NAME, color='#1565C0')

    # 对应：GPT-Live委托架构
    rect = FancyBboxPatch((2, 1.5), 10, 1.2, boxstyle="round,pad=0.1",
                           facecolor='#FFFDE7', edgecolor='#F57F17', lw=1.5)
    ax.add_patch(rect)
    ax.text(7, 2.4, '与 GPT-Live 委托架构同构', fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color='#F57F17')
    ax.text(7, 1.8, 'GPT-Live (快速语音) + GPT-5.5 (深度推理) = 同一个分层模式', fontsize=9, fontproperties=CJK_FONT_NAME, ha='center', color='gray')

    ax.text(7, 0.5, '应变(Ch4)和行动(Ch5)共享同一个前沿: 分层实时架构',
            fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17', fontstyle='italic')

    ax.set_title('Figure Helix 分层决策: System 1 (高频) + System 2 (低频)', fontsize=13, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch5_helix_layered.png')

def fig_ch6_world_model_factions():
    """世界模型六流派分类"""
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 8)
    ax.axis('off')

    # 六个流派，按两条路线配色+布局：
    # 左边两列 = 生成派（能生成像素）→ 暖色系/红色系渐变
    # 右边一列 = 非生成派（不生成像素）→ 冷色系/蓝色系渐变
    # 布局：(x=1, 5.5), (x=5, 5.5) 上排；(x=1, 2.5), (x=5, 2.5) 下排
    factions = [
        # 生成派（左上方）
        ('扩散世界模型派', 'GAIA-2, Sora', '学完整分布\n能生成像素', '#FFF3E0', '#F57C00', 1, 5.5),
        # 生成派（右上方）
        ('空间智能派', 'World Labs (Marble)', '3D 世界\n可交互', '#FFE0B2', '#EF6C00', 5, 5.5),
        # 生成派（左下方）
        ('生成式视频派', 'Genie 3, GWM-1', '物理自洽\n视频生成', '#FFEBEE', '#E64A19', 1, 2.5),
        # 生成派（右下方）
        ('具身仿真派', 'GigaWorld, Cosmos', '世界模型→\n合成数据→VLA', '#FFCDD2', '#C62828', 5, 2.5),
        # 非生成派（右上）
        ('JEPA 派', 'V-JEPA 2, AMI', '潜空间预测\n不生成像素', '#E3F2FD', '#1565C0', 9, 5.5),
        # 非生成派（右下）
        ('RL 世界模型派', 'DreamerV3', 'RL 内部想象\n不生成像素', '#E8F5E9', '#2E7D32', 9, 2.5),
    ]

    for name, rep, desc, fc, ec, x, y in factions:
        rect = FancyBboxPatch((x - 1.3, y - 1), 2.6, 2, boxstyle="round,pad=0.1",
                               facecolor=fc, edgecolor=ec, lw=1.5)
        ax.add_patch(rect)
        ax.text(x, y + 0.6, name, fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', fontweight='bold', color=ec)
        ax.text(x, y + 0.0, rep, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color='gray')
        ax.text(x, y - 0.6, desc, fontsize=8, fontproperties=CJK_FONT_NAME, ha='center', color=ec)

    # 分界线：生成派 vs JEPA派
    ax.axhline(y=4, color='gray', ls='--', alpha=0.3)
    ax.text(0.5, 6.8, '生成像素', fontsize=9, fontproperties=CJK_FONT_NAME, color='gray', fontweight='bold')
    ax.text(0.5, 3.0, '不/不一定\n生成像素', fontsize=9, fontproperties=CJK_FONT_NAME, color='gray', fontweight='bold')

    # 左右分界
    ax.axvline(x=3, color='gray', ls=':', alpha=0.2)
    ax.axvline(x=7, color='gray', ls=':', alpha=0.2)

    # 两条路线之争标注
    ax.annotate('生成派\n(扩散/视频/3D)', xy=(3, 7.3), fontsize=10, fontproperties=CJK_FONT_NAME, ha='center',
                color='#C62828', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFEBEE', alpha=0.8))
    ax.annotate('JEPA 派\n(潜空间预测)', xy=(5, 7.3), fontsize=10, fontproperties=CJK_FONT_NAME, ha='center',
                color='#2E7D32', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8F5E9', alpha=0.8))
    ax.annotate('', xy=(5.5, 7.0), xytext=(2.5, 7.0),
                arrowprops=dict(arrowstyle='<->', lw=2, color='#7B1FA2'))

    # 底部胜负手
    ax.text(6.5, 0.3, '胜负手: 物理状态维护 / 多智能体共享 / sim-to-real 校准',
            fontsize=10, fontproperties=CJK_FONT_NAME, ha='center', color='#F57F17', fontstyle='italic')

    ax.set_title('世界模型六流派分类', fontsize=14, fontproperties=CJK_FONT_NAME, fontweight='bold', y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch6_world_model_factions.png')

# ============================================================
# P3 配图 (4张): 三能力交互 / 动作表示 / 委托架构 / 概念城市
# ============================================================

def fig_ch2_three_capabilities():
    """Ch2 §2.7: 写作/编程/思考三角增强 + 涌现时间线"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_xlim(-1.8, 1.8); ax.set_ylim(-1.5, 1.6); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title('三种能力的相互增强', fontsize=15, fontweight='bold', pad=10, fontproperties=CJK_FONT_NAME)

    top, bl, br = (0, 1.2), (-1.3, -0.8), (1.3, -0.8)
    triangle = plt.Polygon([top, bl, br], fill=False, edgecolor='#AAA', linewidth=1.5, linestyle='--')
    ax.add_patch(triangle)

    ax.text(0, 1.35, '思考\n(多步推理)', ha='center', va='bottom', fontsize=13, fontweight='bold', color='#7B2D8B', fontproperties=CJK_FONT_NAME)
    ax.text(-1.35, -0.95, '写作\n(文本生成)', ha='center', va='top', fontsize=13, fontweight='bold', color='#2166AC', fontproperties=CJK_FONT_NAME)
    ax.text(1.35, -0.95, '编程\n(代码生成)', ha='center', va='top', fontsize=13, fontweight='bold', color='#1B7837', fontproperties=CJK_FONT_NAME)
    for pt, c in [(top,'#7B2D8B'),(bl,'#2166AC'),(br,'#1B7837')]:
        ax.plot(pt[0], pt[1], 'o', color=c, markersize=12, zorder=5)

    ax.text(-0.95, 0.35, '推理→长文逻辑连贯\n写作→意图描述能力', ha='right', va='center', fontsize=8.5, color='#555', fontproperties=CJK_FONT_NAME)
    ax.text(0.95, 0.35, '代码→结构化推理\nverifiable reward→RL稳定', ha='left', va='center', fontsize=8.5, color='#555', fontproperties=CJK_FONT_NAME)
    ax.text(0, -1.05, '写作→文档/注释 · 代码→语义方向精确', ha='center', va='top', fontsize=8.5, color='#555', fontproperties=CJK_FONT_NAME)
    ax.text(0, 0.05, '同一潜空间', ha='center', va='center', fontsize=12, fontweight='bold', color='#333',
            fontproperties=CJK_FONT_NAME, bbox=dict(boxstyle='round,pad=0.4', facecolor='#F5F5F5', edgecolor='#999'))

    ax.annotate('', xy=(1.5,-1.35), xytext=(-1.5,-1.35), arrowprops=dict(arrowstyle='->', color='#666', lw=1.5))
    for x, label, c in [(-1.0,'写作 (2019)','#2166AC'),(0,'编程 (2021)','#1B7837'),(1.0,'思考 (2024)','#7B2D8B')]:
        ax.text(x, -1.25, label, ha='center', va='bottom', fontsize=9, color=c, fontweight='bold', fontproperties=CJK_FONT_NAME)
    ax.text(0, -1.5, '潜空间塑形深度递增 →', ha='center', va='top', fontsize=9, color='#999', style='italic', fontproperties=CJK_FONT_NAME)
    save(fig, 'fig_ch2_three_capabilities.png')


def fig_ch5_action_representation():
    """Ch5 §5.4: 离散 bin 单峰 vs 连续多峰分布"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    bins = np.linspace(-np.pi, np.pi, 257)
    bar_vals = np.zeros(256); bar_vals[133] = 1.0
    ax1.bar(bins[:-1], bar_vals, width=0.02, color='#BBB', edgecolor='none')
    ax1.bar(bins[133], 1.0, width=0.02, color='#2166AC')
    ax1.set_xlabel('关节角度 (rad)', fontproperties=CJK_FONT_NAME); ax1.set_ylabel('选择概率', fontproperties=CJK_FONT_NAME)
    ax1.set_title('离散 bin (RT-2)\n256 个 bin，单峰输出', fontsize=11, fontweight='bold', color='#2166AC', fontproperties=CJK_FONT_NAME)
    ax1.set_xlim(-np.pi, np.pi); ax1.set_ylim(0, 1.3)
    ax1.text(0, 1.1, '分辨率 0.025 rad\n最坏误差 0.012 rad', ha='center', fontsize=9, color='#555', fontproperties=CJK_FONT_NAME)
    ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)

    x = np.linspace(-np.pi, np.pi, 500)
    y = sum(0.8*np.exp(-(x-mu)**2/(2*sig**2)) for mu,sig in [(-1.8,0.5),(0.2,0.6),(2.0,0.45)])
    y /= y.max()
    ax2.fill_between(x, y, alpha=0.3, color='#E66101')
    ax2.plot(x, y, color='#E66101', linewidth=2)
    for s in [-1.9,-1.6,0.1,0.3,2.1]:
        ax2.plot(s, 0.05, 'o', color='#E66101', markersize=8, zorder=5)
    ax2.set_xlabel('关节角度 (rad)', fontproperties=CJK_FONT_NAME); ax2.set_ylabel('概率密度', fontproperties=CJK_FONT_NAME)
    ax2.set_title('连续分布 (π0 / Diffusion Policy)\n无量化损失，多峰输出', fontsize=11, fontweight='bold', color='#E66101', fontproperties=CJK_FONT_NAME)
    ax2.set_xlim(-np.pi, np.pi); ax2.set_ylim(0, 1.3)
    ax2.text(-1.8, 0.92, '从左抓', ha='center', fontsize=9, color='#555', fontproperties=CJK_FONT_NAME)
    ax2.text(0.2, 1.05, '从右抓', ha='center', fontsize=9, color='#555', fontproperties=CJK_FONT_NAME)
    ax2.text(2.0, 0.82, '从上抓', ha='center', fontsize=9, color='#555', fontproperties=CJK_FONT_NAME)
    ax2.text(0, 1.2, '5 次采样 → 5 条不同轨迹', ha='center', fontsize=9, color='#555', fontproperties=CJK_FONT_NAME)
    ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
    save(fig, 'fig_ch5_action_representation.png')


def fig_ch4_delegation_architecture():
    """Ch4 §4.5: GPT-Live 委托架构时序图"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis('off')
    ax.set_title('GPT-Live 委托架构：实时交互与深度推理兼得', fontsize=14, fontweight='bold', pad=15, fontproperties=CJK_FONT_NAME)

    ax.fill_between([0.5,11.5], 3.8, 5.5, alpha=0.08, color='#2166AC')
    ax.fill_between([0.5,11.5], 0.8, 2.8, alpha=0.08, color='#E66101')
    ax.text(0.7, 5.2, 'GPT-Live（交互层）', fontsize=11, fontweight='bold', color='#2166AC', fontproperties=CJK_FONT_NAME)
    ax.text(0.7, 2.5, 'GPT-5.5（推理层）', fontsize=11, fontweight='bold', color='#E66101', fontproperties=CJK_FONT_NAME)
    ax.annotate('', xy=(11.5,0.3), xytext=(0.5,0.3), arrowprops=dict(arrowstyle='->', color='#999', lw=1))
    ax.text(11.3, 0.1, '时间', fontsize=9, color='#999', fontproperties=CJK_FONT_NAME)

    for x, label, c in [(1.5,'用户提问','#333'),(2.5,'"好的，我查一下"\n<500ms','#2166AC'),
                         (5.0,'"你主要关注\n哪个方向？"\n(继续闲聊)','#2166AC'),
                         (8.5,'"我刚看了下，\n最近几个趋势…"\n(带入结果)','#2166AC')]:
        ax.plot(x, 4.5, 'o', color=c, markersize=8, zorder=5)
        ax.text(x, 4.8, label, ha='center', va='bottom', fontsize=8.5, color=c, fontproperties=CJK_FONT_NAME)

    rect = FancyBboxPatch((3.2,1.2), 4.5, 1.0, boxstyle="round,pad=0.1", facecolor='#E66101', alpha=0.2, edgecolor='#E66101')
    ax.add_patch(rect)
    ax.text(5.45, 1.7, '深度推理 + 搜索 (3-5 秒)', ha='center', va='center', fontsize=9.5, color='#E66101', fontproperties=CJK_FONT_NAME)

    ax.annotate('', xy=(3.2,2.2), xytext=(2.8,3.8), arrowprops=dict(arrowstyle='->', color='#E66101', lw=1.5, linestyle='--'))
    ax.text(2.5, 3.0, '委托', fontsize=8, color='#E66101', ha='center', fontproperties=CJK_FONT_NAME)
    ax.annotate('', xy=(8.2,3.8), xytext=(7.7,2.2), arrowprops=dict(arrowstyle='->', color='#E66101', lw=1.5, linestyle='--'))
    ax.text(8.3, 3.0, '返回结果', fontsize=8, color='#E66101', ha='center', fontproperties=CJK_FONT_NAME)

    ax.annotate('', xy=(7.8,5.6), xytext=(2.4,5.6), arrowprops=dict(arrowstyle='<->', color='#1B7837', lw=1.5))
    ax.text(5.1, 5.75, '用户无等待感（GPT-Live 一直在说话）', ha='center', fontsize=9.5, color='#1B7837', fontweight='bold', fontproperties=CJK_FONT_NAME)
    save(fig, 'fig_ch4_delegation_architecture.png')


def fig_ch6_concept_city():
    """Ch6 §6.4: 概念城市——潜空间四结构层"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis('off')
    ax.set_title('概念城市：潜空间有结构，可观测，可干预', fontsize=14, fontweight='bold', pad=15, fontproperties=CJK_FONT_NAME)

    districts = [
        (0.5, 4.2, 5, 3.2, '#E8F4FD', '#2166AC', '地址：概念的方向',
         '• 线性方向编码概念\n• "国王"-"男"+"女"≈"女王"\n• 概念层次 = 几何嵌套\n• 跨语言迁移（英→法）'),
        (6.5, 4.2, 5, 3.2, '#FDF2E8', '#E66101', '道路：信息流电路',
         '• SAE 拆解叠加特征\n• 归因图追踪特征传递\n• 双跳推理: Dallas→Texas→Austin\n• 前瞻规划: 先选韵脚再填词'),
        (0.5, 0.5, 5, 3.2, '#F0F8E8', '#1B7837', '功能区：FFN 关联记忆',
         '• FFN = 键值存储器\n• 知识主要在中层 MLP\n• ROME/MEMIT 精准编辑\n• 涟漪效应: 改一处波及关联'),
        (6.5, 0.5, 5, 3.2, '#F8E8F4', '#7B2D8B', '城市规划：干预谱系',
         '• 知识编辑 (权重级)\n• 激活引导 (方向级)\n• SAE 特征引导 (特征级)\n• 越狱 = 压低拒绝方向'),
    ]
    for x, y, w, h, fc, ec, title, content in districts:
        rect = FancyBboxPatch((x,y), w, h, boxstyle="round,pad=0.15", facecolor=fc, edgecolor=ec, linewidth=2)
        ax.add_patch(rect)
        ax.text(x+w/2, y+h-0.35, title, ha='center', va='top', fontsize=11, fontweight='bold', color=ec, fontproperties=CJK_FONT_NAME)
        ax.text(x+0.3, y+h-0.8, content, ha='left', va='top', fontsize=8.5, color='#444', linespacing=1.5, fontproperties=CJK_FONT_NAME)

    ax.text(6, 4.0, '可观测性 = X 光\n可干预性 = 微创手术', ha='center', va='center', fontsize=10,
            fontweight='bold', color='#333', fontproperties=CJK_FONT_NAME,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#999', linewidth=1.5))
    ax.annotate('', xy=(6.5,5.8), xytext=(5.5,5.8), arrowprops=dict(arrowstyle='->', color='#999', lw=1))
    ax.annotate('', xy=(3,4.2), xytext=(3,3.7), arrowprops=dict(arrowstyle='->', color='#999', lw=1))
    ax.annotate('', xy=(9,4.2), xytext=(9,3.7), arrowprops=dict(arrowstyle='->', color='#999', lw=1))
    save(fig, 'fig_ch6_concept_city.png')


# ============================================================
# 主入口
# ============================================================

def main():
    setup()

    print("\n=== Ch1: 萃取 (1张) ===")
    fig_ch1_vit_patch()

    print("\n=== Ch2: 筑基 (1张) ===")
    fig_ch2_token_journey()

    print("\n=== Ch3: 炼灵 (1张) ===")
    fig_ch3_rlhf_pipeline()

    print("\n=== Ch4: 应变 (2张) ===")
    fig_ch4_kv_cache()
    fig_ch4_voice_generations()

    print("\n=== Ch5: 行动 (1张) ===")
    fig_ch5_vla_pipeline()

    print("\n✅ P0 全部6张配图生成完成！")

    print("\n=== P1 配图 (7张) ===")
    print("-- Ch1 --")
    fig_ch1_token_zoo()
    fig_ch1_clip_space()
    print("-- Ch2 --")
    fig_ch2_latent_space()
    fig_ch2_multimodal_arch()
    print("-- Ch3 --")
    fig_ch3_grpo_advantage()
    print("-- Ch5 --")
    fig_ch5_sim_to_real()
    print("-- Ch6 --")
    fig_ch6_capability_stack()

    print("\n✅ 全部13张配图生成完成！")

    print("\n=== P2 配图 (6张) ===")
    print("-- Ch1 --")
    fig_ch1_modality_scale()
    print("-- Ch2 --")
    fig_ch2_scaling_law()
    print("-- Ch3 --")
    fig_ch3_reward_hacking()
    fig_ch3_jailbreak()
    print("-- Ch5 --")
    fig_ch5_helix_layered()
    print("-- Ch6 --")
    fig_ch6_world_model_factions()

    print("\n✅ 全部19张配图生成完成！")

    print("\n=== P3 配图 (4张) ===")
    print("-- Ch2 --")
    fig_ch2_three_capabilities()
    print("-- Ch4 --")
    fig_ch4_delegation_architecture()
    print("-- Ch5 --")
    fig_ch5_action_representation()
    print("-- Ch6 --")
    fig_ch6_concept_city()

    print("\n✅ 全部23张配图生成完成！")

if __name__ == '__main__':
    main()
