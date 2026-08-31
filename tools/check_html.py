from pathlib import Path
import re
from collections import Counter

html = Path('html/index.html').read_text(encoding='utf-8')
issues = []

# 1. duplicate ids
ids = re.findall(r'id="([^"]+)"', html)
dupes = {k: v for k, v in Counter(ids).items() if v > 1}
if dupes: issues.append('dup ids: ' + str(dupes))
else: print('1. ids unique: OK (', len(ids), ')')

# 2. internal hrefs all resolve
hrefs = re.findall(r'href="#([^"]+)"', html)
broken = [h for h in set(hrefs) if h not in set(ids)]
if broken: issues.append('broken hrefs (%d): %s' % (len(broken), broken[:10]))
else: print('2. internal hrefs: OK (', len(set(hrefs)), ')')

# 3. images exist
imgs = re.findall(r'<img src="figures/([^"]+)"', html)
missing = [s for s in set(imgs) if not (Path('html/figures') / s).exists()]
if missing: issues.append('missing imgs: ' + str(missing[:5]))
else: print('3. images: OK (', len(set(imgs)), ')')

# 4. five docs present
for d in ['doc-1', 'doc-2', 'doc-3', 'doc-4', 'doc-5']:
    if ('id="%s"' % d) not in html: issues.append('missing doc ' + d)
print('4. docs: OK' if not any('missing doc' in i for i in issues) else '4. docs ISSUE')

# 5. appendix anchors per doc
for name in ['附录逻辑链', '附录参考文献', '附录数学预备']:
    per = [(d, ('%s-%s' % (d, name)) in ids) for d in ['doc-1','doc-2','doc-3','doc-4','doc-5']]
    print('5.', name, '->', per)

print()
print('ISSUES:', issues if issues else 'none')