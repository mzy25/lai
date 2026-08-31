"""共享的 matplotlib 配图基础设施（四个章节脚本共用）。

统一五篇脚本的字体配置、保存函数与输出目录行为：
- CJK 字体自动探测（NotoSansCJK 常规/粗体），缺失时回退 sans-serif 并警告
- save_fig() 统一 dpi/bbox/facecolor，目标目录自动创建
- setup_rc() 统一 rcParams（dpi、字号、负号、面板底色）
- 批处理辅助：run_all(functions, doc_name) 统一打印进度并统计生成数
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # 无显示环境也能运行（必须在 import pyplot 之前）

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from pathlib import Path

# 常用 CJK 字体候选路径（按优先级）。NotoSansCJK 是五篇脚本当前使用的字体。
# 五篇脚本统一 dpi=200（save_fig 默认），共享同一保存与字体规范。
_CJK_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]

# 探测到的 CJK 字体名（None 表示未找到，回退 sans-serif）
CJK_FONT_NAME: str | None = None
CJK_BOLD_NAME: str | None = None

for _path in _CJK_CANDIDATES:
    if Path(_path).exists():
        _fp = fm.FontProperties(fname=_path)
        CJK_FONT_NAME = _fp.get_name()
        fm.fontManager.addfont(_path)
        break

# 粗体 CJK：NotoSansCJK-Bold.ttc 是候选列表第二项；单独探测并注册，
# 让 fontweight='bold' 的标签用真粗体而非合成加粗。
_BOLD_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
]
for _path in _BOLD_CANDIDATES:
    if Path(_path).exists():
        _fp = fm.FontProperties(fname=_path)
        CJK_BOLD_NAME = _fp.get_name()
        fm.fontManager.addfont(_path)
        break

if CJK_FONT_NAME is None:
    import warnings
    warnings.warn(
        "未找到 CJK 字体（NotoSansCJK 等），中文可能渲染为方块。"
        "可安装 fonts-noto-cjk 或将字体路径加入 fig_common 的 _CJK_CANDIDATES。",
        stacklevel=2,
    )


# ═══════════════════════ 共享语义色板（五篇约定） ═══════════════════════
# 语义角色（跨篇一致）：danger=错误/危险 success=正确/有效 warning=强调 primary=主
# 四族三阶色（l=浅填充 / m=主体 / d=强调深色）；灰三阶 + 墨色/白。
# 全部配图一律从本表取色（含改图/新图），禁止引入表外独点色。
ROLE_DANGER   = "#C62828"   # 红 危险/错误
ROLE_SUCCESS  = "#2E7D32"   # 绿 正确/成功
ROLE_WARNING  = "#F57F17"   # 橙 警告/强调
ROLE_PRIMARY  = "#1565C0"   # 蓝 主色（Material 系，全库兼容）
BLUE    = {"l": "#9DC3E6", "m": "#4A90D9", "d": "#1F4E79"}
RED     = {"l": "#FF8C8C", "m": "#C62828", "d": "#8B0000"}
GREEN   = {"l": "#A8D8B9", "m": "#55A868", "d": "#2D6A3A"}
ORANGE  = {"l": "#FFD9A0", "m": "#E8A33D", "d": "#C87D1A"}
GRAY    = {"l": "#F0F0F0", "m": "#9E9E9E", "d": "#555555"}
INK     = "#1A1A2E"
WHITE   = "#FFFFFF"


def setup_rc(*, dpi: int = 200, facecolor: str = "white") -> None:
    """统一 rcParams。在调用前导入本模块即可（模块导入时已切 Agg）。"""
    plt.rcParams.update({
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
        "figure.facecolor": facecolor,
        "axes.facecolor": facecolor,
        "axes.unicode_minus": False,
        "font.family": CJK_FONT_NAME or "sans-serif",
    })


def save_fig(fig, name: str, output_dir: str | Path, dpi: int = 200,
             facecolor: str = "white") -> Path:
    """保存图片并关闭 figure。返回保存路径。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    fig.savefig(path, dpi=dpi, bbox_inches="tight",
                facecolor=facecolor, edgecolor="none")
    plt.close(fig)
    return path


def run_all(functions: list, doc_name: str, expected: int) -> None:
    """顺序运行配图函数并打印进度；结束时校验生成数量。

    functions: 可调用对象列表（每项返回保存路径或 None）
    expected : 期望生成张数，用于校验脚本注释与文档引用是否一致
    """
    print(f"生成《{doc_name}》配图，共 {expected} 张")
    for i, fn in enumerate(functions, 1):
        name = getattr(fn, "__name__", str(fn))
        print(f"  [{i:02d}/{expected}] {name}", end="", flush=True)
        path = fn()
        if path:
            print(f"  ->  {Path(path).name}")
        else:
            print()
    print(f"✅ 《{doc_name}》{expected} 张配图生成完毕")