"""共享的 matplotlib 配图基础设施（各篇配图脚本共用）。

统一配图脚本的字体配置、语义色板、保存函数与批处理：
- CJK 字体自动探测（NotoSansCJK 常规/粗体），缺失时回退 sans-serif 并警告
- 语义色板：五族三阶色 + 四个语义角色，全部配图应从本表取色
- save_fig() 统一 dpi/bbox/facecolor，目标目录自动创建，返回保存路径
- setup_rc() 统一 rcParams（dpi、字号层级、负号、面板底色）
- 批处理 run_all(groups, doc_name, expected)：逐张校验，失败会真实报错
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # 无显示环境也能运行（必须在 import pyplot 之前）

import sys

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from pathlib import Path

# Windows 中文控制台默认是 GBK 代码页，打印 ✅/❌ 之类字符会抛 UnicodeEncodeError，
# 让"图其实都生成完了"的脚本以非零码退出（CI 会误判为失败）。这里统一切成 UTF-8；
# 任何环境下失败都静默跳过，不影响出图。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 —— 环境不支持时不强求
        pass

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

# 粗体 CJK：单独探测并 addfont 注册。
# 这步真正的价值是 addfont 本身——把 Bold 字重登记进 fontManager。
# 系统已装该字体时看似多余（fontManager 扫描系统目录就能发现全字重），
# 但在字体未装到系统目录的便携场景下，没有这步 fontweight='bold' 会退成合成加粗。
# 注：CJK_BOLD_NAME 供需要**显式**指定粗体的场合使用（如 FontProperties(family=...)）；
#     常规写法 fontweight='bold' 由 matplotlib 按字族自动查字重，用不到这个变量。
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


# ═══════════════════════ 共享语义色板（各篇约定） ═══════════════════════
# 语义角色（跨篇一致）：primary=主 danger=错误/危险 success=正确/有效
#                       warning=警告/强调 purple=第三种并列类别
# 六族三阶色（l=浅填充 / m=主体 / d=强调深色）；灰族多阶 + 墨色/白。
# 全部配图一律从本表取色（含改图/新图），禁止引入表外独点色。
#
# ⚠️ 本表数值取自配图脚本的实际用法（Material 系为主），不是凭空设计：
#    紫族曾长期缺失，而 #7B1FA2 是第三高频色（32 次）——色板若与实际脱节，
#    "一律从本表取色"就只是一句空话。新增颜色请在此登记后再用。
# 与 HTML 主题 tokens（build/template_common.py）保持同一意象；改 CSS 配色时对照本表
BLUE    = {"l": "#E3F2FD", "xl": "#BBDEFB", "m": "#2196F3", "d": "#1565C0",
           "alt": "#2166AC", "soft": "#4A90D9"}  # xl=Material blue-100，能力栈三档渐变用
RED     = {"l": "#FFEBEE", "m": "#F44336", "d": "#C62828"}
GREEN   = {"l": "#E8F5E9", "m": "#4CAF50", "d": "#2E7D32",
           "alt": "#1B7837"}
ORANGE  = {"l": "#FFF3E0", "m": "#FF9800", "d": "#E65100",
           "amber": "#F57F17", "alt": "#E66101"}
PURPLE  = {"l": "#F3E5F5", "m": "#9C27B0", "d": "#7B1FA2",
           "alt": "#7B2D8B"}
YELLOW  = {"l": "#FFFDE7", "m": "#FFF8E1"}
GRAY    = {"l": "#F5F5F5", "m": "#757575", "d": "#555555",
           "xlight": "#FAFAFA", "line": "#DDDDDD"}
INK     = "#1A1A2E"
WHITE   = "#FFFFFF"

# 角色别名：指向上表，不另设新值（改族色时角色自动跟随）
ROLE_PRIMARY = BLUE["d"]     # 蓝 主色
ROLE_DANGER  = RED["d"]      # 红 危险/错误
ROLE_SUCCESS = GREEN["d"]    # 绿 正确/成功
ROLE_WARNING = ORANGE["amber"]  # 橙 警告/强调
ROLE_PURPLE  = PURPLE["d"]   # 紫 第三种并列类别（如"思考"）

# 屏蔽色（命中需禁用/拦截的场合），与族色区分开
ROLE_BLOCKED = GRAY["m"]


def setup_rc(*, dpi: int = 200, facecolor: str = "white") -> None:
    """统一 rcParams：dpi、字号层级、负号、面板底色、CJK 字体（含真粗体）。

    字号层级说明：这里显式写出 matplotlib 的默认字号（base 10、标题 12、
    刻度/图例 10），不是为了改变观感，而是让"统一字号"这件事**有处可改**——
    各脚本仍有 297 处显式 fontsize= 覆盖，改这里只影响未显式指定的元素。

    粗体：实测确认——把 font.family 直接设成单一字体名，matplotlib 也会
    把它当字族名按 weight 查找，bold 文本同样能解析到真正的 Bold 字重
    （此处改用 sans-serif 列表只是为了保留回退链，不是修 bug）。
    真正的关键在模块顶部的 addfont：它把 Bold 字重注册进 fontManager，
    若 Bold 字体不在系统字体目录里（便携场景），没有这步 bold 才会失效。

    斜体与 CJK（2026-10-02）：generic 别名 "sans-serif" 下，斜体请求整体解析到
    DejaVu Sans Oblique（无中文），CJK 不逐字回退，渲染成方块。含中文的斜体
    注记必须显式传 fontproperties=CJK_FONT_NAME（见 2_foundation 既有写法）；
    为防复发，setup_rc 同时把 "missing from font" 警告升为异常
    （FIG_ALLOW_MISSING_GLYPHS=1 可回退为容忍，供无 CJK 字体的便携环境使用），
    让方块问题在生成时即失败。
    """
    import os
    import warnings

    family = CJK_FONT_NAME or "sans-serif"
    plt.rcParams.update({
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
        "figure.facecolor": facecolor,
        "axes.facecolor": facecolor,
        "axes.unicode_minus": False,
        # 字族：经 sans-serif 列表，并保留 matplotlib 默认回退链，
        # 使 Noto Sans CJK 未覆盖的字形（部分数学符号等）仍能解析。
        "font.family": "sans-serif",
        "font.sans-serif": [family] + list(plt.rcParamsDefault["font.sans-serif"]),
        # 字号层级（数值 = matplotlib 默认值，显式声明以便统一调整）
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


def _normalize_groups(items: list) -> list[tuple[str, list]]:
    """把入参统一成 [(分组标题, [可调用对象, ...]), ...]。

    同时接受两种写法，便于旧脚本平滑过渡：
      - 分组：[(标题, [fn, ...]), ...]   —— 现推荐，输出带分组标题
      - 扁平：[fn, fn, ...]              —— 旧版写法，整批归入一个无标题分组
    """
    if not items:
        return []
    first = items[0]
    if (isinstance(first, (tuple, list)) and len(first) == 2
            and isinstance(first[1], (list, tuple))):
        return [(str(label), list(fns)) for label, fns in items]
    return [("", list(items))]


def run_all(groups: list, doc_name: str, expected: int) -> int:
    """按分组顺序运行配图函数，逐张校验，返回失败张数（0 表示全部成功）。

    groups  : [(分组标题, [可调用对象, ...]), ...]；**也接受**旧版的扁平
              列表 [fn, fn, ...]（见 _normalize_groups）
    doc_name: 用于打印的文档名
    expected: 期望生成张数

    与旧版（只打印、不校验）的差别：
      1. 每张函数必须**返回**保存路径，否则计为失败；
      2. 单张抛异常不会中断整批，会被记录并继续；
      3. 结束时用**实际成功数**比对 expected，不一致则报错并返回非零。

    ⚠️ 调用方必须以返回的失败数作为进程退出码，否则"全部成功"仍是空话。
    """
    groups = _normalize_groups(groups)
    total = sum(len(fns) for _, fns in groups)
    if total != expected:
        raise ValueError(
            f"分组内共 {total} 个函数，但 expected={expected}；"
            f"两者不一致说明脚本与文档引用已脱节，请核对。"
        )

    print(f"生成《{doc_name}》配图，共 {expected} 张")
    done = 0
    saved: list[Path] = []
    failed: list[tuple[str, str]] = []

    for label, fns in groups:
        if label:
            print(f"\n=== {label} ===")
        for fn in fns:
            name = getattr(fn, "__name__", str(fn))
            done += 1
            print(f"  [{done:02d}/{expected}] {name}", end="", flush=True)
            try:
                path = fn()
            except Exception as exc:  # noqa: BLE001 —— 单张失败不应中断整批
                print(f"  ❌ 异常：{type(exc).__name__}: {exc}")
                failed.append((name, f"异常 {type(exc).__name__}: {exc}"))
                continue
            if path is None:
                print("  ❌ 未返回保存路径（save() 忘了 return？）")
                failed.append((name, "未返回保存路径"))
                continue
            if not Path(path).exists():
                print("  ❌ 返回路径不存在（save 未真正写盘？）")
                failed.append((name, f"返回路径不存在：{path}"))
                continue
            saved.append(Path(path))
            print(f"  ->  {Path(path).name}")

    print()
    if failed:
        print(f"❌ {len(failed)}/{expected} 张失败：")
        for name, why in failed:
            print(f"    · {name}: {why}")
        return len(failed)

    if len(saved) != expected:
        print(f"❌ 实际生成 {len(saved)} 张，期望 {expected} 张")
        return expected - len(saved)

    print(f"✅ 《{doc_name}》{expected} 张配图全部生成完毕")
    return 0