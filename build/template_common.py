#!/usr/bin/env python3
"""两个 HTML 模板的共享片段单一源（T1，2026-10）：主题引导、设计 tokens、可访问性基线。

build_html.py / build_cards.py 各自把 `COMMON_HEAD` 注入模板的 `{{COMMON_HEAD}}`
占位符；模板内不再各存一份。改配色/引导逻辑只改这里。
约束：本片段会被注入 HTML `<head>`，不得含字面 `{{`（cards 渲染有占位符残留检查）。
"""

BOOT_JS = """<script>
/* 主题/字号引导：在首屏绘制前设定，避免深色闪白（单一源：build/template_common.py） */
(function () {
  try {
    var t = localStorage.getItem('ai-primer-theme');
    if (t !== 'light' && t !== 'dark') {
      t = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    }
    document.documentElement.dataset.theme = t;
    var f = localStorage.getItem('ai-primer-fs');
    if (f) document.documentElement.style.setProperty('--fs', f);
  } catch (e) {}
})();
</script>"""

BASE_CSS = """<style>
/* 共享基线（单一源：build/template_common.py）：reset / 核心 tokens / 可访问性 */
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  color-scheme: light;
  --bg:#fafaf8; --card:#ffffff; --ink:#1f2937; --ink-soft:#4b5563;
  --line:#e5e7eb; --accent:#2563eb; --accent-soft:#eff6ff;
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg:#111827; --card:#1f2937; --ink:#e5e7eb; --ink-soft:#9ca3af;
  --line:#374151; --accent:#60a5fa; --accent-soft:#1e3a5f;
}
html { font-size: var(--fs, 16px); }
body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC",system-ui,sans-serif;
       background:var(--bg); color:var(--ink); }
a { color:var(--accent); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; border-radius:2px; }
.skip-link { position:absolute; left:-9999px; top:0; background:var(--card); color:var(--accent);
  padding:8px 12px; border:1px solid var(--accent); border-radius:0 0 8px 0; z-index:999; }
.skip-link:focus { left:0; }
.visually-hidden { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden;
  clip:rect(0 0 0 0); white-space:nowrap; border:0; }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior:auto; }
  *, *::before, *::after { transition-duration:0.01ms !important; animation-duration:0.01ms !important; }
}
</style>"""

COMMON_HEAD = BOOT_JS + "\n" + BASE_CSS + "\n"
