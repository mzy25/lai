# -*- coding: utf-8 -*-
"""series 配图共享基础设施（单一来源配图管线的公共件）。

- CJK 字体自动探测（Noto Sans CJK 优先；缺失时警告并回退）
- 语义色板：五族三阶 + 语义角色别名（与根仓五篇同一视觉语言）
- setup_rc / save_fig：统一 dpi=200、白底、负号；输出 series/figures/
- 缺字形警告升异常：中文渲染成方块时当场报错（FIG_ALLOW_MISSING_GLYPHS=1 可关）
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无显示环境也能跑（必须在 import pyplot 之前）

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SERIES = Path(__file__).resolve().parent.parent
FIGDIR = SERIES / "figures"

# 常用 CJK 字体候选（优先 Noto Sans CJK；Windows/Colab 回退链）
_CJK_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]

CJK_FONT_NAME: str | None = None
for _p in _CJK_CANDIDATES:
    if Path(_p).exists():
        CJK_FONT_NAME = fm.FontProperties(fname=_p).get_name()
        break
if CJK_FONT_NAME is None:  # 系统字体目录回退扫描
    _names = {f.name for f in fm.fontManager.ttflist}
    for _n in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei",
               "AR PL UMing CN"):
        if _n in _names:
            CJK_FONT_NAME = _n
            break
if CJK_FONT_NAME is None:
    warnings.warn("未找到 CJK 字体，中文将渲染为方块；请安装 Noto Sans CJK")

# ═══════════════════════ 语义色板（与根仓五篇同一张表） ═══════════════════════
# 语义角色：primary=主 danger=危险/错误 success=正确/有效 warning=警告/强调
#           purple=第三种并列类别
# 六族三阶色（l=浅填充 / m=主体 / d=强调深色）
BLUE = {"l": "#E3F2FD", "xl": "#BBDEFB", "m": "#2196F3", "d": "#1565C0",
        "alt": "#2166AC", "soft": "#4A90D9"}
RED = {"l": "#FFEBEE", "m": "#F44336", "d": "#C62828"}
GREEN = {"l": "#E8F5E9", "m": "#4CAF50", "d": "#2E7D32", "alt": "#1B7837"}
ORANGE = {"l": "#FFF3E0", "m": "#FF9800", "d": "#E65100",
          "amber": "#F57F17", "alt": "#E66101"}
PURPLE = {"l": "#F3E5F5", "m": "#9C27B0", "d": "#7B1FA2", "alt": "#7B2D8B"}
YELLOW = {"l": "#FFFDE7", "m": "#FFF8E1"}
GRAY = {"l": "#F5F5F5", "m": "#757575", "d": "#555555",
        "xlight": "#FAFAFA", "line": "#DDDDDD"}
INK = "#1A1A2E"
WHITE = "#FFFFFF"

ROLE_PRIMARY = BLUE["d"]
ROLE_DANGER = RED["d"]
ROLE_SUCCESS = GREEN["d"]
ROLE_WARNING = ORANGE["amber"]
ROLE_PURPLE = PURPLE["d"]


def setup_rc(*, dpi: int = 200, facecolor: str = "white") -> None:
    """统一 rcParams：dpi、字号层级、负号、面板底色、CJK 字体。"""
    family = CJK_FONT_NAME or "sans-serif"
    plt.rcParams.update({
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
        "figure.facecolor": facecolor,
        "axes.facecolor": facecolor,
        "axes.unicode_minus": False,
        "font.family": "sans-serif",
        "font.sans-serif": [family] + list(plt.rcParamsDefault["font.sans-serif"]),
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 12,
    })
    if os.environ.get("FIG_ALLOW_MISSING_GLYPHS") != "1":
        warnings.filterwarnings("error", message=r".*missing from font.*")


def save_fig(fig, name: str, dpi: int = 200, facecolor: str = "white") -> Path:
    """保存图片到 series/figures/ 并关闭 figure。"""
    FIGDIR.mkdir(parents=True, exist_ok=True)
    path = FIGDIR / name
    fig.savefig(path, dpi=dpi, bbox_inches="tight",
                facecolor=facecolor, edgecolor="none")
    plt.close(fig)
    return path
