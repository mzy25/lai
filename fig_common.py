"""共享的 matplotlib 配图基础设施（四个章节脚本共用）。

统一四篇脚本的字体配置、保存函数与输出目录行为：
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

# 常用 CJK 字体候选路径（按优先级）。NotoSansCJK 是四篇脚本当前使用的字体。
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

for _path in _CJK_CANDIDATES:
    if Path(_path).exists():
        _fp = fm.FontProperties(fname=_path)
        CJK_FONT_NAME = _fp.get_name()
        fm.fontManager.addfont(_path)
        break

if CJK_FONT_NAME is None:
    import warnings
    warnings.warn(
        "未找到 CJK 字体（NotoSansCJK 等），中文可能渲染为方块。"
        "可安装 fonts-noto-cjk 或将字体路径加入 fig_common 的 _CJK_CANDIDATES。",
        stacklevel=2,
    )


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