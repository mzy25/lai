"""《用好AI：从有用到好用》配套可视化图表
18张图：POMDP循环 / Harness六层 / Agent Loop运行时剖面 / 规划四诊断 / ReAct循环 / 工具五步管道
        / 四类失效映射 / 成熟度梯度 / 上下文窗口 / 约束硬度梯度 / 数字vs具身 / 多Agent拓扑
        / AgentFail分类 / 自演化三路线 / 后训练阶段图谱 / 训练时vs推理时
        / 控制范式四阶段 / 状态图示意
风格：轻填充、粗边框、低饱和度、高清晰度
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon, FancyArrowPatch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fig_common  # noqa: E402  (sys.path 就绪后再导入共享模块)
from fig_common import setup_rc  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "figures"

# ============================================================
# 统一配色方案
# ============================================================
PALETTE = {
    'primary':    '#1B4965',
    'secondary':  '#5FA8D3',
    'tertiary':   '#62B6CB',
    'light':      '#E8F4F8',
    'lighter':    '#F0F9FB',
    'warm':       '#FF9F1C',
    'warm_fill':  '#FFF5E6',
    'danger':     '#E63946',
    'danger_fill':'#FFF0F0',
    'success':    '#2A9D8F',
    'success_fill':'#E8F8F5',
    'warning':    '#F4A261',
    'warning_fill':'#FFF3E0',
    'bg':         '#FFFFFF',
    'text':       '#1A1A2E',
    'subtext':    '#5F6B7A',
    'white':      '#FFFFFF',
    'border':     '#1B4965',
}

setup_rc(dpi=200, facecolor=PALETTE['bg'])
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Noto Sans CJK JP', 'DejaVu Sans']


def save(fig, name):
    fig_common.save_fig(fig, name, OUTPUT_DIR, dpi=200, facecolor=PALETTE['bg'])


# ============================================================
# 图3：POMDP 循环与七要素
# ============================================================
def fig_ch2_pomdp_cycle():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(-1, 17)
    ax.set_ylim(-1, 9)
    ax.axis('off')
    p = PALETTE

    # 主循环节点（横向流）：o_t → b_t → a_t → o_{t+1}
    nodes = [
        ('o_t', '观察', '用户输入·工具返回\n报错·传感器读数', 1.5, 3),
        ('b_t', '信念状态', 'Agent对任务·环境·\n历史的当前理解', 6, 3),
        ('a_t', '动作', '搜索·写代码\n调用API·移动机械臂', 10.5, 3),
        ('o_{t+1}', '新观察', '动作执行后的结果\n进入下一轮', 15, 3),
    ]

    node_colors = [p['tertiary'], p['primary'], p['secondary'], p['tertiary']]
    for i, (sym, name, desc, x, y) in enumerate(nodes):
        box = FancyBboxPatch((x-1.3, y-0.9), 2.6, 1.8,
                              boxstyle="round,pad=0.12,rounding_size=0.25",
                              facecolor=p['light'], edgecolor=node_colors[i], linewidth=3, zorder=8)
        ax.add_patch(box)
        ax.text(x, y+0.45, f'${sym}$', fontsize=14, fontweight='bold', ha='center', va='center',
                color=node_colors[i], zorder=9)
        ax.text(x, y-0.05, name, fontsize=11, fontweight='bold', ha='center', va='center',
                color=p['text'], zorder=9)
        ax.text(x, y-0.55, desc, fontsize=8, ha='center', va='center', color=p['subtext'], zorder=9)

    # L3/L1/L2 标注在箭头上方
    flow_labels = [
        ('L3 记忆', 3.75, 4.5),
        ('L1 推理', 8.25, 4.5),
        ('L2 工具', 12.75, 4.5),
    ]
    for label, x, y in flow_labels:
        ax.text(x, y, label, fontsize=9, ha='center', va='center', color=p['success'],
                fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', facecolor=p['white'],
                edgecolor=p['success'], alpha=0.9), zorder=10)

    # 主循环箭头
    for i in range(3):
        x1 = nodes[i][3] + 1.3
        x2 = nodes[i+1][3] - 1.3
        ax.annotate('', xy=(x2, 3), xytext=(x1, 3),
                    arrowprops=dict(arrowstyle='->', color=p['success'], lw=3), zorder=5)

    # 循环回箭头（o_{t+1} → o_t，从底部绕回）
    ax.annotate('', xy=(1.5, 1.8), xytext=(15, 1.8),
                arrowprops=dict(arrowstyle='->', color=p['success'], lw=2.5,
                               connectionstyle='arc3,rad=-0.15'), zorder=4)
    ax.text(8.25, 0.8, 'L4 编排：循环反馈，进入下一轮', fontsize=9, ha='center', va='center',
            color=p['success'], style='italic')

    # S（真实状态）：虚线幽灵框，在 s_t 上方
    ghost_x, ghost_y = 6, 6.8
    ghost = FancyBboxPatch((ghost_x-1.4, ghost_y-0.7), 2.8, 1.4,
                            boxstyle="round,pad=0.1,rounding_size=0.2",
                            facecolor='none', edgecolor=p['subtext'], linewidth=2.5,
                            linestyle='--', zorder=7)
    ax.add_patch(ghost)
    ax.text(ghost_x, ghost_y+0.2, '$\\mathcal{S}$ 真实世界状态空间', fontsize=10, fontweight='bold', ha='center',
            va='center', color=p['subtext'], zorder=9)
    ax.text(ghost_x, ghost_y-0.25, 'Agent 看不到全貌', fontsize=8, ha='center', va='center',
            color=p['subtext'], zorder=9)

    # Z（观测模型）：S → o_t 的虚线箭头
    ax.annotate('', xy=(1.5, 4.0), xytext=(5.0, 6.3),
                arrowprops=dict(arrowstyle='->', color=p['subtext'], lw=1.8, linestyle='--'), zorder=6)
    ax.text(2.5, 5.6, '$Z$ 观测模型', fontsize=9, ha='center', va='center', color=p['subtext'],
            bbox=dict(boxstyle='round,pad=0.15', facecolor=p['white'], edgecolor=p['subtext'], alpha=0.8))

    # T（状态转移）：S → S' 的标注，在 ghost 右侧
    ax.text(9.0, 7.0, '$T$ 状态转移', fontsize=9, ha='center', va='center', color=p['subtext'],
            bbox=dict(boxstyle='round,pad=0.15', facecolor=p['white'], edgecolor=p['subtext'], alpha=0.8))
    ax.annotate('', xy=(9.5, 6.8), xytext=(7.4, 6.8),
                arrowprops=dict(arrowstyle='->', color=p['subtext'], lw=1.5, linestyle=':'), zorder=6)

    # b_t(s) 信念状态：s_t 下方标注
    ax.text(6, 1.3, '$b_t(s)$ 信念状态\n= $P(s_t=s \\mid o_1,...,o_t)$',
            fontsize=8, ha='center', va='center', color=p['primary'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=p['light'], edgecolor=p['primary'], alpha=0.9))
    ax.annotate('', xy=(6, 1.9), xytext=(6, 2.05),
                arrowprops=dict(arrowstyle='->', color=p['primary'], lw=1.5), zorder=6)

    # R（奖励）和 γ（折扣因子）：右下角
    ax.text(15, 6.5, '$R$ 奖励/目标\n看整条轨迹',
            fontsize=9, ha='center', va='center', color=p['warm'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=p['warm_fill'], edgecolor=p['warm'], alpha=0.9))
    ax.annotate('', xy=(11.5, 4.0), xytext=(14, 5.8),
                arrowprops=dict(arrowstyle='->', color=p['warm'], lw=1.5, linestyle=':'), zorder=6)

    ax.text(15, 8.0, '$\\gamma$ 折扣因子\n远期收益打折',
            fontsize=9, ha='center', va='center', color=p['warning'],
            bbox=dict(boxstyle='round,pad=0.2', facecolor=p['warning_fill'], edgecolor=p['warning'], alpha=0.9))

    # MDP 退化注释
    ax.text(1.5, 6.5, '若 $O = S$\n退化为 MDP', fontsize=8, ha='center', va='center',
            color=p['tertiary'], style='italic',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=p['white'], edgecolor=p['tertiary'], alpha=0.8))

    ax.text(8.25, 8.5, 'POMDP 循环：Agent 在信息不全的世界里观察、决策、行动',
            fontsize=15, fontweight='bold', ha='center', va='center', color=p['text'])
    save(fig, 'fig_ch2_pomdp_cycle.png')


# ============================================================
# 图4：六层工程栈
# ============================================================
def fig_ch3_six_layer_stack():
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 13)
    ax.axis('off')
    p = PALETTE

    layers = [
        ('L6', '护栏与安全', '过滤输入·授权工具·验证输出', '约束：把不安全动作从 $\\mathcal{A}$ 中删除', p['danger'], p['danger_fill']),
        ('L5', '评估与可观测', '追踪轨迹·评分输出·捕捉退化', '观测 $o_t$ 的解析与奖励 $R$ 的估计', p['warning'], p['warning_fill']),
        ('L4', '编排', '组合模型调用·工具使用·控制流', '状态转移 $T$ 的工程化控制', p['primary'], p['light']),
        ('L3', '记忆与知识', '存取窗口状态·历史·偏好·领域知识', '信念状态 $b_t$ 的维护与历史压缩', p['primary'], p['light']),
        ('L2', '协议与工具', '经 MCP·A2A 调用外部 API·浏览器', '动作 $a_t$ 的执行通道', p['secondary'], p['lighter']),
        ('L1', '推理', '调用模型完成理解和决策', '策略 $\\pi: b_t \\to a_t$ 的近似', p['tertiary'], p['lighter']),
    ]

    for i, (code, name, resp, pomdp, border, fill) in enumerate(layers):
        y = 11 - i * 2
        box = FancyBboxPatch((1.5, y-0.8), 8, 1.6,
                              boxstyle="round,pad=0.1,rounding_size=0.15",
                              facecolor=fill, edgecolor=border, linewidth=3.5, zorder=8)
        ax.add_patch(box)
        ax.text(2.3, y+0.35, code, fontsize=13, fontweight='bold', ha='center', va='center',
                color=border, zorder=9)
        ax.text(3.5, y+0.35, name, fontsize=13, fontweight='bold', ha='left', va='center',
                color=p['text'], zorder=9)
        ax.text(3.5, y-0.15, resp, fontsize=9, ha='left', va='center', color=p['subtext'], zorder=9)
        ax.text(3.5, y-0.5, pomdp, fontsize=8, ha='left', va='center', color=border,
                style='italic', zorder=9)

    # 右侧成熟度箭头
    ax.annotate('', xy=(10, 11), xytext=(10, 1),
                arrowprops=dict(arrowstyle='->', color=p['text'], lw=2.5))
    ax.text(10.5, 6, '越\n往\n上\n越\n不\n成\n熟', fontsize=10, fontweight='bold', ha='center',
            va='center', color=p['text'], linespacing=1.6)

    # 左侧标签
    ax.text(0.5, 10, '缺\n口\n集\n中', fontsize=10, fontweight='bold', ha='center',
            va='center', color=p['danger'], linespacing=1.6)
    ax.text(0.5, 3, '成\n熟\n稳\n定', fontsize=10, fontweight='bold', ha='center',
            va='center', color=p['success'], linespacing=1.6)

    ax.text(5.5, 12.5, 'Harness 六层：可靠产出的必要条件',
            fontsize=15, fontweight='bold', ha='center', va='center', color=p['text'])
    save(fig, 'fig_ch3_six_layer_stack.png')


# ============================================================
# 图12：栈成熟度梯度
# ============================================================
def fig_ch6_maturity_gradient():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(-1, 14)
    ax.set_ylim(-2.35, 10.4)
    ax.axis('off')
    p = PALETTE

    # (代码, 名称, 状态, 详情, 边框色, 填充色, 成熟条宽或None, 是否虚线)
    layers = [
        ('G',  '治理（单列）', '制度问题', '权限边界·风险分级·留痕追责', p['success'], p['success_fill'], None, True),
        ('L6', '护栏·安全', '最不成熟最关键', '无主导框架·硬约束裁剪动作空间', p['danger'], p['danger_fill'], 1.5, False),
        ('L5', '评估·观测', '最大缺口', '89% 有可观测性\n仅 52% 有评估', p['warning'], p['warning_fill'], 2.5, False),
        ('L4', '编排', '重心转移中', '图管不可逆路径·规划接管探索流', p['primary'], p['light'], 4.0, False),
        ('L3', '记忆与知识', '复杂度最高', '治理＋知识备料\n运行时接口＝上下文工程', p['primary'], p['light'], 3.7, False),
        ('L2', '协议与工具', '协议已定', 'MCP 连工具·A2A 连智能体\n技能包供应链要审', p['secondary'], p['lighter'], 5.0, False),
        ('L1', '推理', '快速演进', '每代打开新能力空间\n层在商品化', p['tertiary'], p['lighter'], 5.5, False),
    ]

    for i, (code, name, status, detail, border, fill, bar_w, dashed) in enumerate(layers):
        y = 8.6 - i * 1.30
        box = FancyBboxPatch((0.5, y-0.5), 4, 1.0,
                              boxstyle="round,pad=0.08,rounding_size=0.12",
                              facecolor=fill, edgecolor=border, linewidth=3,
                              linestyle='--' if dashed else '-', zorder=8)
        ax.add_patch(box)
        ax.text(1.05, y+0.15, code, fontsize=12, fontweight='bold', ha='center', va='center',
                color=border, zorder=9)
        ax.text(1.75, y+0.15, name, fontsize=11 if dashed else 12, fontweight='bold', ha='left',
                va='center', color=p['text'], zorder=9)
        ax.text(4.2, y+0.15, status, fontsize=9, fontweight='bold', ha='right', va='center',
                color=border, zorder=9)
        ax.text(2.5, y-0.27, detail, fontsize=8, ha='left', va='center', color=p['subtext'], zorder=9)

        if bar_w is None:
            ax.text(8.5, y, '制度维度——独立于技术栈，不参与成熟度排序', fontsize=8.5,
                    ha='center', va='center', color=border, style='italic')
            continue
        ax.add_patch(FancyBboxPatch((5.5, y-0.18), 6.0, 0.36,
                     boxstyle="round,pad=0.02,rounding_size=0.05",
                     facecolor='#E8E8E8', edgecolor='none', zorder=6))
        ax.add_patch(FancyBboxPatch((5.5, y-0.18), bar_w, 0.36,
                     boxstyle="round,pad=0.02,rounding_size=0.05",
                     facecolor=border, edgecolor='none', alpha=0.75, zorder=7))

    for x, lab in [(5.5, '低'), (8.5, '中'), (11.5, '高')]:
        ax.text(x, -0.25, lab, fontsize=8, ha='center', color=p['subtext'])
    ax.text(8.5, -0.62, '← 成熟度 →（仅对 L1-L6）', fontsize=9, ha='center',
            color=p['subtext'], fontweight='bold')

    ax.annotate('37pp 差距', xy=(8.2, 6.0), xytext=(10.3, 6.7),
               arrowprops=dict(arrowstyle='->', color=p['danger'], lw=1.5),
               fontsize=9, ha='center', color=p['danger'], fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.2', facecolor=p['danger_fill'],
               edgecolor=p['danger'], alpha=0.9))

    ax.text(6.5, 9.95, 'Harness 成熟度梯度：六层 ＋ 治理（G）', fontsize=15, fontweight='bold',
            ha='center', va='center', color=p['text'])
    ax.text(6.5, 9.42, 'Harness 的薄弱层在哪里，工程重心就在哪里', fontsize=11,
            ha='center', va='center', color=p['subtext'], style='italic')

    ax.text(6.5, -1.18, '跨层课题：循环自身的失效与终止工程——Loopmaxxing · 理解债 · 多重退出条件（§7.6）',
            fontsize=8, ha='center', color=p['subtext'], style='italic')
    ax.text(6.5, -1.58, '学术对照：ETCLOVG 七层（E 执行·T 工具·C 上下文·L 编排·O 可观测·V 验证·G 治理）与 Harness 六层大致对应，O/V/G 更强调形式化与审计',
            fontsize=7.5, ha='center', color=p['subtext'], style='italic')
    ax.text(6.5, -1.98, '2026 前瞻：Provider SDK 正把记忆、工具调用与基础评估吸进单一 API——通用件被商品化，独特件（领域备料、专有评估集）除外',
            fontsize=8, ha='center', color=p['subtext'], style='italic')

    save(fig, 'fig_ch6_maturity_gradient.png')


# ============================================================
# 图11：四种死法 → 栈缺口映射（卡片式，无填充，大字距）
# ============================================================
def fig_ch6_death_modes():
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(-0.5, 16)
    ax.set_ylim(-2.5, 12)
    ax.axis('off')
    p = PALETTE

    deaths = [
        ('失效一', '跳步执行',
         '没 pick 就 hint\n没 test 就 submit',
         'L4 编排 + L6 护栏',
         '流程控制，防跳步',
         p['danger']),
        ('失效二', '参数不匹配',
         '语言与文件扩展名不一致\n路径不符合项目结构',
         'L2 工具',
         'schema 校验，类型检查',
         p['warning']),
        ('失效三', '不分类型微调',
         'WA 只改常数\nTLE 只改逻辑',
         'L5 评估',
         '分类路由，策略匹配',
         p['warm']),
        ('失效四', '错误传播',
         '连续 3 次 WA\n仍在微调细节',
         'L3 记忆 + L4 编排',
         '失败模式追踪，阈值中断',
         p['primary']),
    ]

    col_x = [0.5, 5.8, 10.8]
    col_w = [4.8, 4.4, 4.5]
    row_h = 2.3
    row_gap = 0.5

    # 列标题
    titles = ['没有护栏时的失效', '缺口层', '护栏机制']
    title_colors = [p['danger'], p['text'], p['success']]
    for i, (title, color) in enumerate(zip(titles, title_colors)):
        ax.text(col_x[i] + col_w[i]/2, 11.2, title, fontsize=14, fontweight='bold',
                ha='center', va='center', color=color)

    for idx, (death, title, symptom, layer, guard, color) in enumerate(deaths):
        y_top = 10.0 - idx * (row_h + row_gap)
        y_center = y_top - row_h / 2

        # 列1：死法（无填充，只有边框）
        box1 = FancyBboxPatch((col_x[0], y_top - row_h), col_w[0], row_h,
                               boxstyle="round,pad=0.15,rounding_size=0.2",
                               facecolor='none', edgecolor=color, linewidth=3, zorder=8)
        ax.add_patch(box1)
        ax.text(col_x[0] + 0.4, y_top - 0.45, death, fontsize=12, fontweight='bold', ha='left',
                va='center', color=color, zorder=9)
        ax.text(col_x[0] + 0.4, y_top - 0.95, title, fontsize=15, fontweight='bold', ha='left',
                va='center', color=p['text'], zorder=9)
        ax.text(col_x[0] + 0.4, y_top - 1.65, symptom, fontsize=10.5, ha='left', va='center',
                color=p['subtext'], zorder=9, linespacing=1.5)

        # 列2：缺口层
        box2 = FancyBboxPatch((col_x[1], y_top - row_h + 0.35), col_w[1], row_h - 0.7,
                               boxstyle="round,pad=0.15,rounding_size=0.2",
                               facecolor='none', edgecolor=color, linewidth=3, zorder=8)
        ax.add_patch(box2)
        ax.text(col_x[1] + col_w[1]/2, y_center, layer, fontsize=14, fontweight='bold', ha='center',
                va='center', color=color, zorder=9, linespacing=1.4)

        # 列3：护栏
        box3 = FancyBboxPatch((col_x[2], y_top - row_h + 0.35), col_w[2], row_h - 0.7,
                               boxstyle="round,pad=0.15,rounding_size=0.2",
                               facecolor='none', edgecolor=p['success'], linewidth=3, zorder=8)
        ax.add_patch(box3)
        ax.text(col_x[2] + col_w[2]/2, y_center, guard, fontsize=13, fontweight='bold', ha='center',
                va='center', color=p['success'], zorder=9, linespacing=1.4)

        # 箭头：列1 → 列2
        ax.annotate('', xy=(col_x[1] - 0.1, y_center), xytext=(col_x[0] + col_w[0] + 0.1, y_center),
                    arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.25',
                                   color=color, lw=2.5), zorder=5)
        # 箭头：列2 → 列3
        ax.annotate('', xy=(col_x[2] - 0.1, y_center), xytext=(col_x[1] + col_w[1] + 0.1, y_center),
                    arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.25',
                                   color=p['success'], lw=2.5), zorder=5)

    ax.text(8, -1.8, '四类失效 → Harness 六层缺口 → 护栏：没有架构护栏的 Agent 在这四个环节反复翻车',
            fontsize=14, fontweight='bold', ha='center', va='center', color=p['text'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor='none', edgecolor=p['primary'], alpha=0.9))
    save(fig, 'fig_ch6_death_modes.png')



# ============================================================
# 图6：控制范式四阶段——自主度递进，约束同步变硬
# ============================================================
def fig_ch4_control_paradigms():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(-0.5, 16.5)
    ax.set_ylim(-1.5, 9)
    ax.axis('off')
    p = PALETTE

    ax.text(8, 8.2, '控制范式：自主度递进，约束同步变硬',
            fontsize=17, fontweight='bold', ha='center', va='center', color=p['text'])

    stages = [
        ('命令控制', '人下每一步指令', '人盯', 0.9, 2.2, p['tertiary'], '#EEEEEE'),
        ('目标控制', '人给目标，Agent 自己规划', '规则查', 4.6, 3.6, p['secondary'], p['light']),
        ('意图控制', '人给模糊意图，Agent 追问补全', '追问补全', 8.3, 5.0, p['warm'], p['warm_fill']),
        ('受约束自主', '安全边界内持续自主运行', '权限系统裁剪动作空间', 12.0, 6.4, p['primary'], p['light']),
    ]
    box_w, box_h = 3.6, 1.9
    for name, desc, constraint, x, y, color, fill in stages:
        box = FancyBboxPatch((x, y), box_w, box_h,
                              boxstyle="round,pad=0.1,rounding_size=0.2",
                              facecolor=fill, edgecolor=color, linewidth=2.5, zorder=8)
        ax.add_patch(box)
        ax.text(x + box_w/2, y + box_h - 0.45, name, fontsize=14, fontweight='bold',
                ha='center', va='center', color=color, zorder=9)
        ax.text(x + box_w/2, y + box_h - 1.15, desc, fontsize=9.5,
                ha='center', va='center', color=p['text'], zorder=9, linespacing=1.5)
        ax.text(x + box_w/2, y - 0.55, f'约束：{constraint}', fontsize=9.5, fontweight='bold',
                ha='center', va='center', color=p['subtext'], zorder=9)

    # 递进箭头
    for i in range(3):
        x1 = 0.9 + box_w + 0.28 + i * (box_w + 0.28)
        y1 = 2.2 + 1.4 * i
        x2 = 4.6 + i * (box_w + 0.28)
        y2 = 2.2 + 1.4 * (i + 1)
        ax.annotate('', xy=(x2 - 0.1, y2 + box_h/2), xytext=(x1 + 0.05, y1 + box_h/2),
                    arrowprops=dict(arrowstyle='-|>', color=p['primary'], lw=2.5))

    ax.text(8, 0.5, '从左到右：人逐步放手，约束从软到硬——内建约束（执行前裁剪动作空间）比外挂规则（运行时检查）更硬',
            fontsize=11, ha='center', va='center', color=p['subtext'])

    save(fig, 'fig_ch4_control_paradigms.png')


# ============================================================
# 图9：状态图示意——Agent 的状态、转移与回退
# ============================================================
def fig_ch5_state_diagram():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(-1, 14)
    ax.set_ylim(-1, 9)
    ax.axis('off')
    p = PALETTE

    states = [
        ('初始化', 2, 4, p['tertiary']),
        ('思考中', 6, 6.5, p['secondary']),
        ('工具调用中', 10, 4, p['primary']),
        ('等待确认', 8, 1, p['warm']),
        ('失败恢复', 3, 1, p['danger']),
        ('完成', 12, 7.5, p['success']),
    ]

    for name, x, y, color in states:
        circ = Circle((x, y), 0.9, facecolor=p['light'], edgecolor=color, linewidth=3.5, zorder=10)
        ax.add_patch(circ)
        ax.text(x, y, name, fontsize=10.5, fontweight='bold', ha='center', va='center',
                color=color, zorder=11)

    transitions = [
        (0, 1, '目标就绪', 'up'),
        (1, 2, '需要工具', 'up'),
        (2, 3, '不可逆动作', 'down'),
        (3, 1, '人类确认', 'left'),
        (2, 4, '工具失败', 'down'),
        (4, 1, '换方案重试', 'left'),
        (1, 5, '验证通过', 'up'),
        (0, 5, '无需工具', 'right'),
    ]

    for from_i, to_i, label, side in transitions:
        x1, y1 = states[from_i][1], states[from_i][2]
        x2, y2 = states[to_i][1], states[to_i][2]
        dx, dy = x2-x1, y2-y1
        dist = np.sqrt(dx**2 + dy**2)
        offset = 0.95
        sx = x1 + dx/dist * offset
        sy = y1 + dy/dist * offset
        ex = x2 - dx/dist * offset
        ey = y2 - dy/dist * offset
        rad = 0.15
        ax.annotate('', xy=(ex, ey), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle='->', color=p['subtext'], lw=2,
                                   connectionstyle=f'arc3,rad={rad}'), zorder=5)
        mx, my = (sx+ex)/2, (sy+ey)/2
        ax.text(mx, my+0.25, label, fontsize=8, ha='center', va='center', color=p['text'],
                bbox=dict(boxstyle='round,pad=0.15', facecolor=p['white'],
                edgecolor=p['border'], alpha=0.85), zorder=12)

    ax.text(6.5, 8.6, '状态图：每个状态是节点，每条边是转移条件——回退边（失败恢复→思考中）让 Agent 能回头',
            fontsize=14, fontweight='bold', ha='center', va='center', color=p['text'])
    save(fig, 'fig_ch5_state_diagram.png')


# ============================================================
# 图15：数字 Agent vs 具身智能（雷达图）
# ============================================================
def fig_ch6_radar():
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    p = PALETTE

    categories = ['安全', '记忆', '工具', '实时性', '学习']
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    digital_scores = [8, 9, 9, 6, 9]
    physical_scores = [3, 4, 2, 9, 3]
    digital_scores += digital_scores[:1]
    physical_scores += physical_scores[:1]

    ax.plot(angles, digital_scores, 'o-', linewidth=2.5, color=p['secondary'], label='数字 Agent', markersize=8)
    ax.fill(angles, digital_scores, alpha=0.15, color=p['secondary'])

    ax.plot(angles, physical_scores, 's-', linewidth=2.5, color=p['warm'], label='具身智能', markersize=8)
    ax.fill(angles, physical_scores, alpha=0.15, color=p['warm'])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=13, fontweight='bold', color=p['text'])
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=9, color=p['subtext'])
    ax.grid(True, linestyle='--', alpha=0.4, color=p['border'])
    ax.spines['polar'].set_color(p['border'])

    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), fontsize=12, frameon=True,
              fancybox=True, shadow=False, facecolor=p['white'], edgecolor=p['border'])

    ax.set_title('数字 Agent vs 具身智能：约束对比（定性示意，非实测）',
                 fontsize=13, fontweight='bold', color=p['text'], pad=20)
    save(fig, 'fig_ch6_radar.png')


# ============================================================
# 图8：ReAct 循环
# ============================================================
def fig_ch5_react_loop():
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(-6, 6)
    ax.set_ylim(-5, 7)
    ax.set_aspect('equal')
    ax.axis('off')
    p = PALETTE

    node_borders = [p['primary'], p['secondary'], p['tertiary'], '#3A7CA5', p['primary']]
    node_data = [
        ('观察\nPerceive', '看到了什么？\n环境输入 / 工具返回', 0, 4.5),
        ('思考\nReason', '这意味着什么？\n下一步该做什么？', 4.2, 1.2),
        ('行动\nDecide', '调用哪个工具？\n传什么参数？', 2.5, -3.2),
        ('执行\nExecute', '通过运行时\n实际运行', -2.5, -3.2),
        ('记忆\nUpdate', '记录结果\n更新状态', -4.2, 1.2),
    ]

    for i, (title, desc, x, y) in enumerate(node_data):
        circ = Circle((x, y), 1.1, facecolor=p['light'], edgecolor=node_borders[i],
                      linewidth=3.5, zorder=10)
        ax.add_patch(circ)
        ax.text(x, y+0.25, title, fontsize=11, fontweight='bold', ha='center', va='center',
                color=node_borders[i], zorder=11)
        ax.text(x, y-0.35, desc, fontsize=8, ha='center', va='center', color=p['subtext'], zorder=11)

    connections = [(0,1), (1,2), (2,3), (3,4), (4,0)]
    for i, j in connections:
        x1, y1 = node_data[i][2], node_data[i][3]
        x2, y2 = node_data[j][2], node_data[j][3]
        dx, dy = x2-x1, y2-y1
        dist = np.sqrt(dx**2 + dy**2)
        offset = 1.25
        x_start = x1 + dx/dist * offset
        y_start = y1 + dy/dist * offset
        x_end = x2 - dx/dist * offset
        y_end = y2 - dy/dist * offset
        ax.annotate('', xy=(x_end, y_end), xytext=(x_start, y_start),
                    arrowprops=dict(arrowstyle='->', color=p['success'], lw=2.5,
                                   connectionstyle="arc3,rad=0.1"), zorder=5)

    ax.text(0, 0, 'while not\ntask_done:', fontsize=12, ha='center', va='center',
            color=p['text'], fontweight='bold', family='monospace',
            bbox=dict(boxstyle='round,pad=0.4', facecolor=p['light'], edgecolor=p['primary'], linewidth=2.5))

    features = [
        ('$o_t$', 0, 6.2, p['primary']),
        ('$b_t$', 5.5, 3.5, p['secondary']),
        ('$a_t$', 4, -4.5, p['tertiary']),
        ('$o_{t+1}$', -4, -4.5, '#3A7CA5'),
        ('信念状态 $b_t$', -5.5, 3.5, p['primary']),
    ]
    for text, x, y, color in features:
        ax.text(x, y, text, fontsize=10, ha='center', va='center', color=color, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.25', facecolor=p['white'], edgecolor=color, alpha=0.85))

    ax.text(0, 6.7, 'ReAct 循环：$o_t \\to b_t \\to a_t \\to o_{t+1}$ 的最朴素实现',
            fontsize=14, fontweight='bold', ha='center', va='center', color=p['text'])
    save(fig, 'fig_ch5_react_loop.png')


# ============================================================
# 图7：规划的四诊断维度（APB 视角）
# 长程规划 / 工具鲁棒 / 校准拒绝 / 推理时精化
# ============================================================
def fig_ch5_planning_dimensions():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(-0.5, 16)
    ax.set_ylim(-1.5, 11)
    ax.axis('off')
    p = PALETTE

    # 顶部标题
    ax.text(7.75, 10.3, '规划的四个诊断维度', fontsize=17, fontweight='bold',
            ha='center', va='center', color=p['text'])
    ax.text(7.75, 9.6, 'Agent Planning Benchmark (APB, 2026) 把"规划质量"从端到端成功率中剥离',
            fontsize=11.5, ha='center', va='center', color=p['subtext'])

    # 四个诊断维度：2×2 布局
    dims = [
        # (label, title, question, symptom_when_fail, engineering_response, color, x, y)
        ('D1', '长程规划',
         '任务展开数十步后\nAgent 还知道自己在走哪条路吗？',
         '前 5 步正确，第 20 步偏离目标',
         '规划前置 + 里程碑锚点',
         p['primary'], 1.0, 5.0),
        ('D2', '工具鲁棒',
         '工具集里混入无关或损坏工具，\n规划质量是否骤降？',
         '被无关工具吸引\n或对损坏工具反复重试',
         '工具过滤 + 失败快速降级',
         p['secondary'], 8.5, 5.0),
        ('D3', '校准拒绝',
         '任务不可解时，\nAgent 会承认还是硬编？',
         '幻觉出一个"看起来对"的方案',
         '不可行判据 + 显式拒绝',
         p['warm'], 1.0, 0.5),
        ('D4', '推理时精化',
         '基于反馈修正后续步骤，\n还是把错误累加下去？',
         '每步都在为上一步的错误打补丁',
         '重规划触发条件 + 检查点',
         p['success'], 8.5, 0.5),
    ]

    box_w, box_h = 6.5, 3.7
    for label, title, question, symptom, response, color, x, y in dims:
        # 主框
        box = FancyBboxPatch((x, y), box_w, box_h,
                              boxstyle="round,pad=0.15,rounding_size=0.25",
                              facecolor='none', edgecolor=color, linewidth=3, zorder=8)
        ax.add_patch(box)

        # 编号 + 标题
        ax.text(x + 0.4, y + box_h - 0.5, label, fontsize=13, fontweight='bold',
                ha='left', va='center', color=color, zorder=9)
        ax.text(x + 1.4, y + box_h - 0.5, title, fontsize=15, fontweight='bold',
                ha='left', va='center', color=p['text'], zorder=9)

        # 分隔线
        ax.plot([x + 0.4, x + box_w - 0.4], [y + box_h - 0.95, y + box_h - 0.95],
                color=color, linewidth=1.2, alpha=0.4, zorder=8)

        # 诊断问题
        ax.text(x + 0.4, y + box_h - 1.55, question, fontsize=10.5,
                ha='left', va='center', color=p['text'], zorder=9,
                fontstyle='italic', linespacing=1.4)

        # 失败症状（红色小标签）
        ax.text(x + 0.4, y + 1.15, '· 未处理时：', fontsize=9.5, fontweight='bold',
                ha='left', va='center', color=p['danger'], zorder=9)
        ax.text(x + 0.4, y + 0.65, symptom, fontsize=10,
                ha='left', va='center', color=p['subtext'], zorder=9, linespacing=1.4)

        # 工程手段（绿色小标签）
        ax.text(x + box_w - 0.4, y + 1.15, '工程手段：', fontsize=9.5, fontweight='bold',
                ha='right', va='center', color=p['success'], zorder=9)
        ax.text(x + box_w - 0.4, y + 0.5, response, fontsize=10.5, fontweight='bold',
                ha='right', va='center', color=p['success'], zorder=9)

    # 底部小结
    ax.text(7.75, -1.0,
            'APB (arXiv:2606.04874) 4209 例 · 22 领域 · 12 前沿模型：四维度全部存在系统性短板',
            fontsize=11.5, ha='center', va='center', color=p['text'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=p['lighter'],
                     edgecolor=p['primary'], linewidth=1.5, alpha=0.9))
    save(fig, 'fig_ch5_planning_dimensions.png')


# ============================================================
# 图17：AgentFail 三层十六类失败根因分类
# 节点级 F1 / 结构级 F2 / 平台级 F3
# ============================================================
def fig_ch7_agentfail_taxonomy():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(-0.5, 16)
    ax.set_ylim(-2, 12)
    ax.axis('off')
    p = PALETTE

    # 标题
    ax.text(7.75, 11.3, 'AgentFail 三层十六类失败根因（2025 实证）',
            fontsize=17, fontweight='bold', ha='center', va='center', color=p['text'])
    ax.text(7.75, 10.6,
            '307 例真实多 Agent 平台失败 · 按"抽象层级"归因',
            fontsize=11.5, ha='center', va='center', color=p['subtext'])

    # 三个层级：横向三列（F1×7 + F2×7 + F3×2 = 16 类，对齐论文 Figure 4）
    layers = [
        # (code, title, subtitle, items, color, x_start, w)
        ('F1', '节点级', 'LLM & Agent 单节点',
         [('F1.1', '工具 / 动作规划错误'),
          ('F1.2', '响应格式错误'),
          ('F1.3', '响应内容偏差'),
          ('F1.4', '知识 / 推理局限'),
          ('F1.5', 'Prompt 设计缺陷'),
          ('F1.6', '语言 / 编码缺陷'),
          ('F1.7', '工具调用 / 知识库检索错误')],
         p['primary'], 0.3, 5.0),
        ('F2', '结构级', '工作流拓扑',
         [('F2.1', '输入校验缺失'),
          ('F2.2', '节点依赖不合理'),
          ('F2.3', '循环 / 死锁'),
          ('F2.4', '条件判断错误'),
          ('F2.5', '任务分解不当'),
          ('F2.6', '上下文冲突'),
          ('F2.7', '跨 Agent 工具 / 接口不匹配')],
         p['warm'], 5.6, 5.0),
        ('F3', '平台级', '底层运行时',
         [('F3.1', '网络 / 资源波动'),
          ('F3.2', '服务不可用')],
         p['secondary'], 10.9, 5.0),
    ]

    for code, title, subtitle, items, color, x0, w in layers:
        # 层级标题栏
        header = FancyBboxPatch((x0, 8.7), w, 1.4,
                                 boxstyle="round,pad=0.1,rounding_size=0.2",
                                 facecolor=color, edgecolor=color, linewidth=2, alpha=0.15, zorder=6)
        ax.add_patch(header)
        ax.text(x0 + w/2, 9.6, f'{code}  {title}',
                fontsize=15, fontweight='bold', ha='center', va='center', color=color, zorder=9)
        ax.text(x0 + w/2, 9.0, subtitle,
                fontsize=10.5, ha='center', va='center', color=p['subtext'], zorder=9)

        # 子类（7 行列高 0.72，底部留余给实证区）
        y_top = 8.3
        row_h = 0.72
        for i, (subcode, name) in enumerate(items):
            y = y_top - i * row_h
            row = FancyBboxPatch((x0 + 0.2, y - row_h + 0.1), w - 0.4, row_h - 0.12,
                                 boxstyle="round,pad=0.05,rounding_size=0.15",
                                 facecolor='none', edgecolor=color, linewidth=1.5, alpha=0.7, zorder=7)
            ax.add_patch(row)
            ax.text(x0 + 0.5, y - row_h/2 + 0.05, subcode,
                    fontsize=10, fontweight='bold', ha='left', va='center', color=color, zorder=9)
            ax.text(x0 + 1.5, y - row_h/2 + 0.05, name,
                    fontsize=10, ha='left', va='center', color=p['text'], zorder=9)

        # 底部注解（F3 只有 2 项，用一段注解填补视觉空白 + 补充信息）
        if code == 'F3':
            annot_y_top = y_top - len(items) * row_h - 0.3
            annot_h = 3.1
            annot = FancyBboxPatch((x0 + 0.2, annot_y_top - annot_h), w - 0.4, annot_h,
                                    boxstyle="round,pad=0.1,rounding_size=0.2",
                                    facecolor=color, edgecolor=color, linewidth=1, alpha=0.08, zorder=6)
            ax.add_patch(annot)
            ax.text(x0 + w/2, annot_y_top - 0.5, '为何平台级最少？',
                    fontsize=11, fontweight='bold', ha='center', va='center', color=color, zorder=9)
            ax.text(x0 + w/2, annot_y_top - 1.7,
                    '低代码 Agent 平台\n(Dify · Coze) 把\n底层运行时封装严密\n但更高层的节点与\n结构故障因此更凸显',
                    fontsize=9.8, ha='center', va='center',
                    color=p['subtext'], zorder=9, linespacing=1.55)

    # 底部：传播距离实证数字
    ax.text(0.3, 1.5, '实证发现（arXiv:2509.23735）',
            fontsize=13, fontweight='bold', ha='left', va='center', color=p['danger'])

    facts = [
        '· 10%+ 的失败案例中，根因位置距离暴露位置超过工作流长度的 40%',
        '· LLM & Agent 节点中，40% 的失败根因位置 ≠ 暴露位置',
        '· Logic & Control 节点中，这一比例升至 45%',
        '· 长距离传播意味着"看到错误"和"改正错误"要跨节点回溯',
    ]
    for i, fact in enumerate(facts):
        ax.text(0.5, 0.7 - i*0.55, fact, fontsize=10.5,
                ha='left', va='center', color=p['text'])

    # 右下：四条修复策略
    ax.text(9.5, 1.5, '收敛的四条修复策略',
            fontsize=13, fontweight='bold', ha='left', va='center', color=p['success'])
    fixes = [
        '· 格式验证模块（对齐 F1.2）',
        '· 二次校验代理 / 备用工具路径（对齐 F2.4）',
        '· 渐进式工作流：先串行再复合（对齐 F2.2 / F2.3）',
        '· 输入校验前置（对齐 F2.1，修复成功率最高）',
    ]
    for i, fix in enumerate(fixes):
        ax.text(9.7, 0.7 - i*0.55, fix, fontsize=10.5,
                ha='left', va='center', color=p['text'])

    save(fig, 'fig_ch7_agentfail_taxonomy.png')

# ============================================================
# 图18：自演化三路线 + 三硬边界
# skill 演化 / workflow 演化 / topology 演化  vs  Library Drift / 统计极限 / 泛化间隙
# ============================================================
def fig_ch8_self_evolution():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(-0.5, 16)
    ax.set_ylim(-2, 11)
    ax.axis('off')
    p = PALETTE

    # 标题
    ax.text(7.75, 10.3, '自演化：Agent 迭代自身的三条路线，以及三条硬边界',
            fontsize=17, fontweight='bold', ha='center', va='center', color=p['text'])

    # 上半部：三条路线（绿色系）
    ax.text(3.5, 9.3, '生成 / 迭代能力', fontsize=13, fontweight='bold',
            ha='left', va='center', color=p['success'])
    ax.plot([3.0, 15.5], [9.0, 9.0], color=p['success'], linewidth=1.5, alpha=0.4)

    paths = [
        ('Skill 演化',
         'Voyager · OpenSkill · EvolveR · Anthropic Skills',
         '从失败轨迹蒸馏出可复用策略\n写回技能库供下次检索',
         p['success'], 0.5, 6.2),
        ('Workflow 演化',
         'AFlow · AutoFlow · ADAS',
         '把 Agent 工作流建模为代码图\nMCTS / meta-agent 搜索最优拓扑',
         p['tertiary'], 5.8, 6.2),
        ('协作拓扑演化',
         'GPTSwarm · MetaSkill-Evolve',
         '把多 Agent 图交给优化器\n节点优化 prompt，边优化通信',
         p['secondary'], 11.1, 6.2),
    ]
    box_w, box_h = 4.5, 2.4
    for title, refs, desc, color, x, y in paths:
        box = FancyBboxPatch((x, y), box_w, box_h,
                              boxstyle="round,pad=0.12,rounding_size=0.25",
                              facecolor='none', edgecolor=color, linewidth=3, zorder=8)
        ax.add_patch(box)
        ax.text(x + box_w/2, y + box_h - 0.4, title, fontsize=14, fontweight='bold',
                ha='center', va='center', color=color, zorder=9)
        ax.text(x + box_w/2, y + box_h - 0.95, refs, fontsize=9,
                ha='center', va='center', color=p['subtext'], zorder=9, fontstyle='italic')
        ax.text(x + box_w/2, y + 0.65, desc, fontsize=10.5,
                ha='center', va='center', color=p['text'], zorder=9, linespacing=1.5)

    # 中间：一根"张力线"横穿
    ax.plot([0.3, 15.7], [4.7, 4.7], color=p['danger'], linewidth=2, linestyle='--', alpha=0.6)
    ax.text(7.75, 4.7, '  三条硬边界  ',
            fontsize=13, fontweight='bold', ha='center', va='center', color=p['danger'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=p['bg'], edgecolor=p['danger'], linewidth=1.5))

    # 下半部：三条边界（红色系）
    bounds = [
        ('Library Drift',
         'arXiv:2605.19576',
         'LLM 自生成 skill: +0.0pp\n人工策展 skill: +16.2pp\n（SkillsBench 实测）',
         '需要生命周期治理\n（淘汰 · 容量 · 元技能授权）',
         0.5, 1.4),
        ('统计极限',
         'arXiv:2510.04399',
         '容量无界的自我修改\n可能把原本可学的任务\n变成不可学',
         '效用与学习之间存在\n数学证明的张力',
         5.8, 1.4),
        ('泛化间隙',
         'arXiv:2606.01075',
         '闭环自演化投入算力后\n会平台化，始终留有\n到 oracle 监督的差距',
         '收益递减是内生的\n人工监督仍不可替代',
         11.1, 1.4),
    ]
    for title, ref, finding, implication, x, y in bounds:
        box = FancyBboxPatch((x, y), box_w, 2.9,
                              boxstyle="round,pad=0.12,rounding_size=0.25",
                              facecolor='none', edgecolor=p['danger'], linewidth=3, zorder=8)
        ax.add_patch(box)
        ax.text(x + box_w/2, y + 2.5, title, fontsize=14, fontweight='bold',
                ha='center', va='center', color=p['danger'], zorder=9)
        ax.text(x + box_w/2, y + 2.05, ref, fontsize=8.5,
                ha='center', va='center', color=p['subtext'], zorder=9, fontstyle='italic')
        ax.text(x + box_w/2, y + 1.3, finding, fontsize=10.2,
                ha='center', va='center', color=p['text'], zorder=9, linespacing=1.5)
        # 分隔小线
        ax.plot([x + 0.5, x + box_w - 0.5], [y + 0.75, y + 0.75],
                color=p['danger'], linewidth=1, alpha=0.4, zorder=8)
        ax.text(x + box_w/2, y + 0.4, implication, fontsize=9.5, fontweight='bold',
                ha='center', va='center', color=p['danger'], zorder=9, linespacing=1.4)

    # 底部落款
    ax.text(7.75, -1.3,
            '基座是能力上限 · Agent 栈是稳定性下限 · 自演化是迭代速率上限——三把钥匙缺一不可',
            fontsize=12, fontweight='bold', ha='center', va='center', color=p['text'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=p['lighter'],
                     edgecolor=p['primary'], linewidth=1.5, alpha=0.9))

    save(fig, 'fig_ch8_self_evolution.png')



# ============================================================
# 图5：Agent Loop 运行时剖面
# ============================================================
def fig_ch3_agent_loop_runtime():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    p = PALETTE

    # 外框：L4 编排
    outer = FancyBboxPatch((0.5, 0.5), 15, 8,
                            boxstyle="round,pad=0.2,rounding_size=0.3",
                            facecolor=p['lighter'], edgecolor=p['success'], linewidth=3, zorder=1)
    ax.add_patch(outer)
    ax.text(8, 8.2, 'L4 编排（元层）', fontsize=13, fontweight='bold', ha='center',
            color=p['success'], zorder=10)
    ax.text(8, 7.7, 'max_turns=20 | stopReason: end_turn / max_turns / error_budget | 失败回退规则',
            fontsize=9, ha='center', color=p['subtext'], zorder=10)

    # 四个内部组件
    boxes = [
        ('L3 记忆', 'b_t = assemble(\nhistory, o_t)', p['tertiary'], 2.0),
        ('L1 推理', 'a_t = policy(b_t)\n模型选择动作', p['primary'], 5.5),
        ('L6 护栏', 'a_t in A_safe(c)?\n规则计算', p['danger'], 9.0),
        ('L2 工具', 'o_{t+1} = exec(a_t)\n执行并返回', p['secondary'], 12.5),
    ]
    for name, desc, color, x in boxes:
        box = FancyBboxPatch((x, 3.5), 2.8, 2.8,
                              boxstyle="round,pad=0.12,rounding_size=0.2",
                              facecolor=p['white'], edgecolor=color, linewidth=2.5, zorder=5)
        ax.add_patch(box)
        ax.text(x+1.4, 5.7, name, fontsize=11, fontweight='bold', ha='center',
                color=color, zorder=6)
        ax.text(x+1.4, 4.5, desc, fontsize=8.5, ha='center', va='center',
                color=p['text'], zorder=6)

    # 箭头连接
    for i in range(3):
        x1 = boxes[i][3] + 2.8
        x2 = boxes[i+1][3]
        ax.annotate('', xy=(x2, 4.9), xytext=(x1, 4.9),
                    arrowprops=dict(arrowstyle='->', color=p['text'], lw=2.5), zorder=4)

    # 回路箭头（L2 → L3）
    ax.annotate('', xy=(2.0+1.4, 3.5), xytext=(12.5+1.4, 3.5),
                arrowprops=dict(arrowstyle='->', color=p['success'], lw=2.5,
                               connectionstyle='arc3,rad=0.3'), zorder=4)
    ax.text(8, 1.8, 'history.append(action, result) → 进入下一轮', fontsize=9,
            ha='center', color=p['success'], style='italic', zorder=6)

    # 环境反馈（底部）
    ax.text(14.5, 2.5, '环境', fontsize=10, fontweight='bold', ha='center', color=p['warm'], zorder=6)
    ax.annotate('', xy=(13.9, 3.5), xytext=(14.5, 2.8),
                arrowprops=dict(arrowstyle='->', color=p['warm'], lw=2), zorder=4)
    ax.text(14.5, 2.0, 'o_{t+1}', fontsize=9, ha='center', color=p['warm'], zorder=6)

    # Pi 对照注释
    ax.text(8, 0.9, 'Pi 对照：receive(o_t) → model(π) → tool(exec) → inject(history)',
            fontsize=8.5, ha='center', color=p['subtext'], style='italic', zorder=6,
            bbox=dict(boxstyle='round,pad=0.2', facecolor=p['white'], edgecolor=p['subtext'], alpha=0.7))

    save(fig, 'fig_ch3_agent_loop_runtime.png')


# ============================================================
# 图10：工具调用五步管道
# ============================================================
def fig_ch6_tool_pipeline():
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 7)
    ax.axis('off')
    p = PALETTE

    steps = [
        ('1. 声明', 'JSON Schema\n(MCP 格式)', '失效二前提', p['secondary']),
        ('2. 校验', '类型·范围\n文件存在性', '失效二', p['tertiary']),
        ('3. 执行', '超时/沙箱\n约束下运行', '失效一', p['primary']),
        ('4. 格式化', '截断·分类\n返回码', '失效三', p['warm']),
        ('5. 注入', '回写上下文\n触发下轮', '失效四', p['success']),
    ]

    box_w, box_h, gap = 2.5, 3.0, 0.5
    start_x = 0.7
    y_center = 3.5

    for i, (title, desc, failure, color) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        box = FancyBboxPatch((x, y_center - box_h/2), box_w, box_h,
                              boxstyle="round,pad=0.1,rounding_size=0.2",
                              facecolor=p['white'], edgecolor=color, linewidth=2.5, zorder=5)
        ax.add_patch(box)
        ax.text(x + box_w/2, y_center + 0.9, title, fontsize=11, fontweight='bold',
                ha='center', color=color, zorder=6)
        ax.text(x + box_w/2, y_center, desc, fontsize=9, ha='center', va='center',
                color=p['text'], zorder=6)
        # 失效标签（下方）
        ax.text(x + box_w/2, y_center - box_h/2 - 0.4, f'对应{failure}', fontsize=8,
                ha='center', color=p['danger'], zorder=6,
                bbox=dict(boxstyle='round,pad=0.15', facecolor=p['danger_fill'],
                         edgecolor=p['danger'], alpha=0.8))
        # 箭头（从左到右）
        if i < 4:
            ax.annotate('', xy=(x + box_w + gap*0.85, y_center),
                       xytext=(x + box_w + gap*0.15, y_center),
                       arrowprops=dict(arrowstyle='->', color=p['text'], lw=2.5), zorder=4)

    # 顶部标题
    ax.text(8, 6.3, '工具调用五步管道: 每一步都有约束', fontsize=13, fontweight='bold',
            ha='center', color=p['text'], zorder=6)

    # 底部注释：错误即消息
    ax.text(8, 0.8, '第3步失败不终止管道 → 错误格式化后走第4、5步正常注入 → "错误即消息"',
            fontsize=9, ha='center', color=p['success'], style='italic', zorder=6)

    save(fig, 'fig_ch6_tool_pipeline.png')


# ============================================================
# 图13：上下文窗口的一生
# ============================================================
def fig_ch6_context_lifecycle():
    fig, ax = plt.subplots(figsize=(14, 7))
    p = PALETTE

    turns = np.arange(0, 51)
    # 模拟上下文占用
    raw_usage = np.minimum(turns * 2, 100)  # 线性增长到窗口上限
    # 压缩后
    compressed = np.where(turns < 15, turns * 2,
                 np.where(turns < 30, 30 + (turns-15)*1.2,
                 48 + (turns-30)*0.8))

    ax.fill_between(turns, 0, raw_usage, alpha=0.15, color=p['danger'], label='无压缩（会撞墙）')
    ax.plot(turns, raw_usage, '--', color=p['danger'], lw=1.5, alpha=0.5)
    ax.fill_between(turns, 0, compressed, alpha=0.3, color=p['success'], label='有上下文工程')
    ax.plot(turns, compressed, '-', color=p['success'], lw=2.5)

    # 窗口上限
    ax.axhline(y=100, color=p['danger'], lw=2, linestyle=':', alpha=0.7)
    ax.text(50.5, 100, '窗口上限', fontsize=9, color=p['danger'], va='center')

    # 三个区域标注
    ax.axvspan(0, 15, alpha=0.05, color=p['secondary'])
    ax.axvspan(15, 30, alpha=0.05, color=p['warm'])
    ax.axvspan(30, 50, alpha=0.05, color=p['success'])

    ax.text(7.5, 85, '增长期\n(层3为主)', fontsize=9, ha='center', color=p['secondary'], fontweight='bold')
    ax.text(22.5, 85, '压缩触发\n(层3→层2迁移)', fontsize=9, ha='center', color=p['warm'], fontweight='bold')
    ax.text(40, 85, '外化期\n(层4分担)', fontsize=9, ha='center', color=p['success'], fontweight='bold')

    # 技术标注
    ax.annotate('Compaction', xy=(15, 30), xytext=(15, 55),
               arrowprops=dict(arrowstyle='->', color=p['warm'], lw=1.5),
               fontsize=8, ha='center', color=p['warm'])
    ax.annotate('NOTES.md', xy=(30, 48), xytext=(33, 65),
               arrowprops=dict(arrowstyle='->', color=p['success'], lw=1.5),
               fontsize=8, ha='center', color=p['success'])
    ax.annotate('Sub-agent\n卸载', xy=(22, 38), xytext=(25, 70),
               arrowprops=dict(arrowstyle='->', color=p['primary'], lw=1.5),
               fontsize=8, ha='center', color=p['primary'])

    ax.set_xlabel('对话轮次', fontsize=10)
    ax.set_ylabel('上下文窗口占用 (%)', fontsize=10)
    ax.set_title('上下文窗口的一生：四层互补 + 三种压缩技术', fontsize=13, fontweight='bold', color=p['text'])
    ax.set_xlim(0, 52)
    ax.set_ylim(0, 110)
    ax.legend(loc='upper left', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    save(fig, 'fig_ch6_context_lifecycle.png')


# ============================================================
# 图16：多Agent五种拓扑
# ============================================================
def fig_ch7_multi_agent_topologies():
    fig, axes = plt.subplots(1, 5, figsize=(18, 5))
    p = PALETTE
    titles = ['Supervisor', 'Pipeline', 'Fan-out', 'Debate', 'Swarm']

    for idx, (ax, title) in enumerate(zip(axes, titles)):
        ax.set_xlim(-2, 2)
        ax.set_ylim(-2, 2.5)
        ax.axis('off')
        ax.set_title(title, fontsize=11, fontweight='bold', color=p['text'], pad=10)

        def node(x, y, color=p['secondary'], r=0.25):
            circle = plt.Circle((x, y), r, facecolor=color, edgecolor=p['border'], lw=1.5, zorder=5)
            ax.add_patch(circle)

        def edge(x1, y1, x2, y2):
            ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                       arrowprops=dict(arrowstyle='->', color=p['subtext'], lw=1.5), zorder=3)

        if idx == 0:  # Supervisor
            node(0, 1.5, p['primary'], 0.3)
            for x in [-1.2, 0, 1.2]:
                node(x, -0.5, p['secondary'])
                edge(0, 1.2, x, -0.2)
        elif idx == 1:  # Pipeline
            for i, x in enumerate([-1.5, -0.5, 0.5, 1.5]):
                node(x, 0.5, p['secondary'] if i > 0 else p['primary'])
                if i > 0:
                    edge(x-1+0.25, 0.5, x-0.25, 0.5)
        elif idx == 2:  # Fan-out
            node(0, 1.5, p['primary'], 0.3)
            for x in [-1.2, 0, 1.2]:
                node(x, -0.3, p['secondary'])
                edge(0, 1.2, x, 0)
            node(0, -1.5, p['warm'], 0.3)
            for x in [-1.2, 0, 1.2]:
                edge(x, -0.55, 0, -1.2)
        elif idx == 3:  # Debate
            for x in [-1, 0, 1]:
                node(x, 1, p['secondary'])
            node(0, -1, p['warm'], 0.3)
            for x in [-1, 0, 1]:
                edge(x, 0.75, 0, -0.7)
        elif idx == 4:  # Swarm
            positions = [(-1, 1), (0, 1.5), (1, 1), (-1.2, 0), (1.2, 0), (-0.5, -1), (0.5, -1)]
            for x, y in positions:
                node(x, y, p['secondary'], 0.2)
            edges = [(0,1),(1,2),(0,3),(2,4),(3,5),(4,6),(5,6),(3,4)]
            for i, j in edges:
                x1, y1 = positions[i]
                x2, y2 = positions[j]
                ax.plot([x1, x2], [y1, y2], '-', color=p['subtext'], lw=1, alpha=0.5, zorder=2)

    fig.suptitle('五种多Agent编排拓扑', fontsize=13, fontweight='bold', color=p['text'], y=1.02)
    plt.tight_layout()
    save(fig, 'fig_ch7_multi_agent_topologies.png')


# ============================================================
# 图14：约束硬度梯度
# ============================================================
def fig_ch6_trust_gradient():
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 5)
    ax.axis('off')
    p = PALETTE

    # 渐变背景条
    gradient = np.linspace(0, 1, 256).reshape(1, -1)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('trust', [p['success'], p['warm'], p['danger']])
    ax.imshow(gradient, aspect='auto', cmap=cmap, extent=[1, 15, 1.8, 2.8], alpha=0.3, zorder=1)

    # 五个锚点
    anchors = [
        ('提示词建议', '"请谨慎操作"\n模型可忽略', 2.0, p['success']),
        ('输出过滤', 'L5 事后检查\n已太晚', 5.0, p['tertiary']),
        ('确认弹窗', 'HITL\n人可拒绝', 8.0, p['secondary']),
        ('权限系统', 'A_safe(c)\n规则计算', 11.0, p['warm']),
        ('硬件回路', '物理Agent\n不可绕过', 14.0, p['danger']),
    ]

    for name, desc, x, color in anchors:
        # 竖线
        ax.plot([x, x], [1.5, 3.1], '-', color=color, lw=3, zorder=5)
        # 名称
        ax.text(x, 3.5, name, fontsize=10, fontweight='bold', ha='center', color=color, zorder=6)
        # 描述
        ax.text(x, 1.0, desc, fontsize=8, ha='center', va='center', color=p['subtext'], zorder=6)

    # 两端标注
    ax.text(1.0, 2.3, '软', fontsize=12, fontweight='bold', ha='center', color=p['success'], zorder=6)
    ax.text(15.0, 2.3, '硬', fontsize=12, fontweight='bold', ha='center', color=p['danger'], zorder=6)

    # 标题
    ax.text(8, 4.5, '约束硬度梯度：从"模型自觉"到"物理不可能"', fontsize=13,
            fontweight='bold', ha='center', color=p['text'], zorder=6)

    # 底部判据
    ax.text(8, 0.3, '判据：动作是否还在候选集里？在 → 软约束（可被忽略）；不在 → 硬约束（物理路障）',
            fontsize=9, ha='center', color=p['subtext'], style='italic', zorder=6)

    save(fig, 'fig_ch6_trust_gradient.png')


# ============================================================
# 图1：后训练阶段图谱——从毛坯到工具
# ============================================================
def fig_ch1_post_training_stages():
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(-0.5, 16.5)
    ax.set_ylim(-1.5, 9)
    ax.axis('off')
    p = PALETTE

    ax.text(8, 8.2, '后训练：从毛坯到工具——四种反馈，四个阶段',
            fontsize=17, fontweight='bold', ha='center', va='center', color=p['text'])

    stages = [
        ('毛坯', '基础模型', '只会续写\n对指令没有义务', p['subtext'], '#EEEEEE'),
        ('例题', 'SFT', '场景特化\n会按要求作答', p['warm'], p['warm_fill']),
        ('打分', 'RLHF / DPO', '好坏之分\n风格与安全', p['warm'], p['warm_fill']),
        ('对错', 'RLVR', '可验证硬实力\n推理与自查', p['warm'], p['warm_fill']),
        ('干活', 'Agentic 后训练', '工具使用\n环境轨迹反馈', p['warm'], p['warm_fill']),
        ('工具', '可用的模型', '能按要求做事\n有潜能，且成形', p['success'], p['success_fill']),
    ]
    x0, box_w, box_h = 0.4, 2.35, 3.6
    for i, (tag, name, desc, color, fill) in enumerate(stages):
        x = x0 + i * (box_w + 0.28)
        y = 2.2
        box = FancyBboxPatch((x, y), box_w, box_h,
                              boxstyle="round,pad=0.1,rounding_size=0.2",
                              facecolor=fill, edgecolor=color, linewidth=2.5, zorder=8)
        ax.add_patch(box)
        ax.text(x + box_w/2, y + box_h - 0.55, tag, fontsize=15, fontweight='bold',
                ha='center', va='center', color=color, zorder=9)
        ax.text(x + box_w/2, y + box_h - 1.25, name, fontsize=12, fontweight='bold',
                ha='center', va='center', color=p['text'], zorder=9)
        ax.text(x + box_w/2, y + 1.0, desc, fontsize=10.5,
                ha='center', va='center', color=p['text'], zorder=9, linespacing=1.6)
        if i < len(stages) - 1:
            ax.annotate('', xy=(x + box_w + 0.24, y + box_h/2), xytext=(x + box_w + 0.02, y + box_h/2),
                        arrowprops=dict(arrowstyle='-|>', color=p['primary'], lw=2.5))

    ax.text(8, 0.8, '四种反馈 = 后训练给模型的四类信号：示范、偏好、验证、轨迹',
            fontsize=12, ha='center', va='center', color=p['subtext'])

    save(fig, 'fig_ch1_post_training_stages.png')


# ============================================================
# 图2：训练时 vs 推理时——同一个循环，两处落点
# ============================================================
def fig_ch1_training_vs_inference():
    fig, ax = plt.subplots(figsize=(16, 9.5))
    ax.set_xlim(-0.5, 16.5)
    ax.set_ylim(-1.5, 9.5)
    ax.axis('off')
    p = PALETTE

    ax.text(8, 8.7, '同一个循环，两处落点：训练时烧权重，推理时写上下文',
            fontsize=17, fontweight='bold', ha='center', va='center', color=p['text'])

    col_x = [0.4, 8.4]
    col_w = 7.2
    titles = ['训练时（后训练）', '推理时（Harness 循环）']
    title_colors = [p['warm'], p['primary']]
    for x, title, color in zip(col_x, titles, title_colors):
        box = FancyBboxPatch((x, 7.2), col_w, 0.9,
                              boxstyle="round,pad=0.1,rounding_size=0.18",
                              facecolor='none', edgecolor=color, linewidth=3, zorder=8)
        ax.add_patch(box)
        ax.text(x + col_w/2, 7.65, title, fontsize=15, fontweight='bold',
                ha='center', va='center', color=color, zorder=9)

    def box(x, y, w, h, text, color, fill, fontsize=11, bold=False):
        b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.15",
                            facecolor=fill, edgecolor=color, linewidth=2.2, zorder=8)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, text, fontsize=fontsize,
                ha='center', va='center', color=p['text'], zorder=9,
                fontweight='bold' if bold else 'normal', linespacing=1.6)

    def arrow(x1, y1, x2, y2, color):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='-|>', color=color, lw=2.4))

    # 左栏：训练时
    box(col_x[0], 5.4, 3.3, 1.3, '环境 / 任务\n（沙箱、题目、轨迹）', p['subtext'], '#EEEEEE')
    box(col_x[0] + 3.9, 5.4, 3.3, 1.3, 'Agent 采样\n跑出完整轨迹', p['warm'], p['warm_fill'])
    arrow(col_x[0] + 3.3, 6.05, col_x[0] + 3.9, 6.05, p['primary'])
    box(col_x[0], 3.6, 3.3, 1.3, '验证器评测\n轨迹级 → 步级 → 教师信号', p['warm'], p['warm_fill'])
    arrow(col_x[0] + 5.55, 6.05, col_x[0] + 5.55, 4.9, p['primary'])
    box(col_x[0] + 3.9, 3.6, 3.3, 1.3, '优化器回灌\n（GRPO 等）', p['warm'], p['warm_fill'])
    arrow(col_x[0] + 3.9, 4.9, col_x[0] + 3.9, 4.25, p['primary'])
    box(col_x[0] + 1.2, 1.4, 4.8, 1.4, '权重\n学一次，万人用', p['success'], p['success_fill'], fontsize=13, bold=True)
    arrow(col_x[0] + 5.55, 3.6, col_x[0] + 5.55, 2.8, p['success'])

    # 右栏：推理时
    box(col_x[1], 5.4, 3.3, 1.3, '任务 / 用户目标', p['subtext'], '#EEEEEE')
    box(col_x[1] + 3.9, 5.4, 3.3, 1.3, '模型动作\n（调用工具、生成）', p['primary'], p['light'])
    arrow(col_x[1] + 3.3, 6.05, col_x[1] + 3.9, 6.05, p['primary'])
    box(col_x[1], 3.6, 3.3, 1.3, '工具 / 环境反馈\n（返回、测试、报错）', p['primary'], p['light'])
    arrow(col_x[1] + 5.55, 6.05, col_x[1] + 5.55, 4.9, p['primary'])
    box(col_x[1] + 3.9, 3.6, 3.3, 1.3, '反馈写回\n错误即消息', p['primary'], p['light'])
    arrow(col_x[1] + 3.9, 4.9, col_x[1] + 3.9, 4.25, p['primary'])
    box(col_x[1] + 1.2, 1.4, 4.8, 1.4, '上下文\n学一次，用一次', p['success'], p['success_fill'], fontsize=13, bold=True)
    arrow(col_x[1] + 5.55, 3.6, col_x[1] + 5.55, 2.8, p['success'])

    ax.text(8, 0.2, '高频、稳定、可验证 → 烧权重；低频、临时、一次性 → 写上下文',
            fontsize=12, ha='center', va='center', color=p['subtext'])

    save(fig, 'fig_ch1_training_vs_inference.png')


# ============================================================
# 主程序
# ============================================================
if __name__ == '__main__':
    print("开始生成图表...")
    main_funcs = [
        (fig_ch2_pomdp_cycle, "fig1 POMDP循环与七要素"),
        (fig_ch3_six_layer_stack, "fig2 Harness六层"),
        (fig_ch3_agent_loop_runtime, "fig3 Agent Loop运行时剖面"),
        (fig_ch5_planning_dimensions, "fig4 规划的四个诊断维度"),
        (fig_ch5_react_loop, "fig5 ReAct循环"),
        (fig_ch6_tool_pipeline, "fig6 工具调用五步管道"),
        (fig_ch6_death_modes, "fig7 四类失效→Harness六层缺口映射"),
        (fig_ch6_maturity_gradient, "fig8 Harness六层成熟度梯度"),
        (fig_ch6_context_lifecycle, "fig9 上下文窗口的一生"),
        (fig_ch6_trust_gradient, "fig10 约束硬度梯度"),
        (fig_ch6_radar, "fig11 数字Agent vs 具身智能"),
        (fig_ch7_multi_agent_topologies, "fig12 五种多Agent编排拓扑"),
        (fig_ch7_agentfail_taxonomy, "fig13 AgentFail 三层十六类失败根因"),
        (fig_ch8_self_evolution, "fig14 自演化：三条路线+三条硬边界"),
        (fig_ch1_post_training_stages, "fig16 后训练：从毛坯到工具"),
        (fig_ch1_training_vs_inference, "fig17 训练时vs推理时：两处落点"),
        (fig_ch4_control_paradigms, "fig18 控制范式四阶段"),
        (fig_ch5_state_diagram, "fig19 状态图示意"),
    ]
    for fn, label in main_funcs:
        fn()
        print(f"✓ {label} 完成")
    print(f"\n全部 18 张图表已保存到 {OUTPUT_DIR}/")
