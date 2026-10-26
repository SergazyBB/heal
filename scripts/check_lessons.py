"""Проверка уроков курса: YAML, длина, запрещённые формулировки, ссылки, родовые окончания.
Запуск: python3 scripts/check_lessons.py [каталог_уроков]
"""
import re, sys, glob
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None
D = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "course/return_ex/lessons")
BAD = [r"100\s?%", r"(?<!не )(?<!без )гарантир", r"\b\d{2,3}\s?%\s*(женщин|мужчин|бывш)", r"\w\((а|ла|ёл|ся|ась)\)", r"\bтряп", r"\bлох\b", r"\bбаба\b", r"\b(хуй|хуё|хуе|блят|бляд|пизд|ебан|ёбан|ебат|нахуй|заеб|мудак|сука)"]
REQ = ["## Главная мысль", "## Как это работает", "## Пример", "## Частые ошибки", "## Что делать вместо", "## Упражнение", "## Конспект", "## Дальше"]
problems = 0; ids = []
for f in sorted(glob.glob(str(D / "[0-9][0-9]-*.md"))):
    t = Path(f).read_text(encoding="utf-8"); name = Path(f).name
    m = re.match(r"---\n(.*?)\n---\n(.*)", t, re.S)
    if not m: print(name, "нет заголовка YAML"); problems += 1; continue
    fm, body = m.groups(); msgs = []
    meta = None
    if yaml:
        try: meta = yaml.safe_load(fm)
        except Exception as e: msgs.append(f"YAML не разбирается: {str(e).splitlines()[0]}")
    if meta:
        for k in ("id", "title", "module", "access", "minutes", "exercise", "tool"):
            if k not in meta: msgs.append(f"нет поля {k}")
        n = int(name[:2])
        if meta.get("id") != n: msgs.append(f"id {meta.get('id')} != {n}")
        exp = "free" if n <= 10 else "paid"
        if meta.get("access") != exp: msgs.append(f"access {meta.get('access')} (ожидалось {exp})")
        ids.append(n)
    words = len(re.findall(r"\w+", re.sub(r"^#.*$", "", body, flags=re.M)))
    if not 880 <= words <= 1450: msgs.append(f"слов {words}")
    for r in REQ:
        if r not in body: msgs.append(f"нет раздела {r}")
    for p in BAD:
        if re.search(p, body, re.I): msgs.append(f"запрещённое: {p}")
    for ref in re.findall(r"урок\w*\s+(\d+)", body, re.I):
        if not 1 <= int(ref) <= 60: msgs.append(f"ссылка на урок {ref}")
    if msgs: problems += 1; print(name, "|", "; ".join(msgs))
print(f"проверено {len(list(glob.glob(str(D/'[0-9][0-9]-*.md'))))} файлов, с замечаниями: {problems}")
miss = sorted(set(range(1, 61)) - set(ids)); print("нет уроков:", miss)
