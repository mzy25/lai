#!/usr/bin/env python3
"""产物新鲜度门禁：工作区产物是否与 HEAD 提交的一致（CI/本地同源）。

用途：源稿（*.md）改了却忘记重建产物时，本门禁报红。比较对象是**已跟踪的产物**
（html/ cards/ docs/），不是源稿——源稿改动由 lint/仪器负责。

两种比较口径（2026-10-03 实测得出，不是猜的）：
- 文本类（.html/.tsv/.css/.js）：**逐字节**比。实测重建后无差异，可作硬门禁。
- DOCX：**逐条目**比 zip 内文件，但跳过 `docProps/core.xml`、`docProps/app.xml`。
  pandoc 每次写入当前时间戳，重建未改动的源稿也会让这两个条目变；实测 38 个条目里
  仅 `docProps/core.xml` 变，其余 37 个（含 word/document.xml、media、styles）逐字节
  相同——故排除这两个即可既抓内容陈旧、又不被时间戳噪声误伤。

退出码：0 全部新鲜；1 有陈旧/缺失/内容漂移；2 用法或环境错误。

    python3 build/check_artifact_fresh.py                 # 默认查 html cards docs
    python3 build/check_artifact_fresh.py --paths html    # 限范围
    python3 build/check_artifact_fresh.py --selftest       # 合成夹具自测
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = ("html", "cards", "docs")
# DOCX 里与内容无关的元数据（时间戳/生成工具版本）
DOCX_META_SKIP = ("docProps/core.xml", "docProps/app.xml")
ZIP_MAGIC = b"PK\x03\x04"


def _git(*args: str) -> bytes:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败：{r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout


def tracked(prefixes: tuple[str, ...]) -> list[str]:
    """已跟踪文件清单。

    必须用 `-z`：默认输出对非 ASCII 路径做 C 风格转义（"docs/\\346\\225\\260..."），
    直接拼 ROOT 会得到不存在的路径——五篇 docx 会全被误报"工作区缺失"（2026-10-03 实测）。
    """
    out: set[str] = set()
    for p in prefixes:
        raw = _git("ls-files", "-z", "--", p)
        for chunk in raw.split(b"\0"):
            if chunk.strip():
                out.add(chunk.decode("utf-8"))
    return sorted(out)


def head_bytes(path: str) -> bytes | None:
    """HEAD 版本内容；文件在 HEAD 中不存在（如新产物未提交）→ None。"""
    r = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True)
    return None if r.returncode != 0 else r.stdout


def _zip_entries(data: bytes) -> dict[str, bytes] | None:
    if not data.startswith(ZIP_MAGIC):
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return {n: z.read(n) for n in z.namelist()}
    except zipfile.BadZipFile:
        return None


def compare(path: str, work: bytes, head: bytes | None) -> tuple[str, str]:
    """→ (状态, 说明)；状态 ∈ same / stale / meta_only / missing_head / missing_work。"""
    if head is None:
        return "missing_head", "工作区有、HEAD 无（新产物未提交）"
    if work == head:
        return "same", ""
    wz, hz = _zip_entries(work), _zip_entries(head)
    if wz is not None and hz is not None:
        only_meta = [n for n in set(wz) | set(hz)
                     if n not in DOCX_META_SKIP and wz.get(n) != hz.get(n)]
        if not only_meta:
            return "meta_only", "仅 docProps 元数据变（pandoc 时间戳，可忽略）"
        sample = sorted(only_meta)[:3]
        return "stale", f"zip 内容漂移：{sample}"
    return "stale", "逐字节不同"


def scan(prefixes: tuple[str, ...]) -> tuple[int, list[str]]:
    lines: list[str] = []
    bad = 0
    for rel in tracked(prefixes):
        p = ROOT / rel
        if not p.exists():
            bad += 1
            lines.append(f"STALE  {rel}：工作区缺失（产物被删或未构建）")
            continue
        status, note = compare(rel, p.read_bytes(), head_bytes(rel))
        if status == "same":
            continue
        if status == "meta_only":
            lines.append(f"meta   {rel}：{note}")
            continue
        bad += 1
        lines.append(f"STALE  {rel}：{note}")
    return bad, lines


def _selftest() -> int:
    ok = True

    def case(name: str, cond: bool) -> None:
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    def zip_bytes(entries: dict[str, bytes]) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for n, b in entries.items():
                z.writestr(n, b)
        return buf.getvalue()

    doc = {"word/document.xml": b"<w>hi</w>", "word/styles.xml": b"s", "docProps/core.xml": b"t1"}
    doc2 = {"word/document.xml": b"<w>hi</w>", "word/styles.xml": b"s", "docProps/core.xml": b"t2"}
    changed = dict(doc, **{"word/document.xml": b"<w>CHANGED</w>"})
    case("docx 仅时间戳变 → meta_only",
         compare("a.docx", zip_bytes(doc2), zip_bytes(doc))[0] == "meta_only")
    case("docx 内容变 → stale",
         compare("a.docx", zip_bytes(changed), zip_bytes(doc))[0] == "stale")
    case("docx 完全相同 → same",
         compare("a.docx", zip_bytes(doc), zip_bytes(doc))[0] == "same")
    case("docx 少条目 → stale",
         compare("a.docx", zip_bytes({"word/document.xml": b"<w>hi</w>"}), zip_bytes(doc))[0] == "stale")
    case("文本逐字节同 → same", compare("a.html", b"<html>", b"<html>")[0] == "same")
    case("文本逐字节异 → stale", compare("a.html", b"<html>2", b"<html>")[0] == "stale")
    case("HEAD 无 → missing_head", compare("a.html", b"x", None)[0] == "missing_head")
    # 兜底：真实仓库里 html/ 必须全部新鲜（本脚本不能自己空转）
    bad, _ = scan(("html",))
    case(f"真实 html/ 新鲜（bad={bad}）", bad == 0)
    print("check_artifact_fresh selftest:", "all pass" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="产物新鲜度门禁（与 HEAD 比对）")
    ap.add_argument("--paths", nargs="*", default=list(DEFAULT_PATHS), help="要检查的产物目录（默认 html cards docs）")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not _git("rev-parse", "--git-dir").strip():
        print("不在 git 仓库内，无法取 HEAD 版本", file=sys.stderr)
        return 2
    bad, lines = scan(tuple(args.paths))
    for line in lines:
        print(line)
    n_tracked = len(tracked(tuple(args.paths)))
    print(f"检查 {n_tracked} 个已跟踪产物（{' '.join(args.paths)}）："
          f"陈旧 {bad}" + ("　——源稿改了需重建（build_html/build_docx/build_cards）" if bad else "　全部新鲜"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())