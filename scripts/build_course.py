"""Собирает из уроков оглавление (README.md), lessons.json для сайта/бота и единый файл COURSE_FULL.md для вычитки.
Запуск: python3 scripts/build_course.py
"""
import glob, json, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "course" / "return_ex"
lessons = []
for f in sorted(glob.glob(str(C / "lessons" / "[0-9][0-9]-*.md"))):
    t = Path(f).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", t, re.S)
    meta = yaml.safe_load(m.group(1)); body = m.group(2).strip()
    meta["file"] = Path(f).name
    meta["words"] = len(re.findall(r"\w+", body))
    meta["body"] = body
    lessons.append(meta)

(C / "lessons.json").write_text(json.dumps(lessons, ensure_ascii=False, indent=1), encoding="utf-8")

total = sum(l["words"] for l in lessons)
mins = sum(l["minutes"] for l in lessons)
out = ["# Курс «Вернуть бывшую / бывшего»\n",
       f"Текстовый курс: {len(lessons)} уроков, около {total:,} слов, ~{mins // 60} ч {mins % 60} мин чтения.\n".replace(f"{total:,}", f"{total:,}".replace(",", " ")),
       "Бесплатные уроки: 1–10. Платная часть: 11–60.\n",
       "Служебные файлы: [BIBLE.md](BIBLE.md) (правила курса), [OUTLINE.md](OUTLINE.md) (план), "
       "[COURSE_FULL.md](COURSE_FULL.md) (весь курс одним файлом для вычитки), `lessons.json` (для сайта и бота).\n"]
mod = None
for l in lessons:
    if l["module"] != mod:
        mod = l["module"]; out.append(f"\n## {mod}\n")
    tag = "бесплатно" if l["access"] == "free" else "платно"
    out.append(f"{l['id']}. [{l['title']}](lessons/{l['file']}) — {l['minutes']} мин, {tag}")
(C / "README.md").write_text("\n".join(out) + "\n", encoding="utf-8")

full = ["# Курс «Вернуть бывшую / бывшего». Полный текст для вычитки\n"]
for l in lessons:
    full.append(f"\n\n---\n\n{l['body']}\n")
(C / "COURSE_FULL.md").write_text("\n".join(full), encoding="utf-8")
print(f"{len(lessons)} уроков, {total:,} слов, {mins} мин")
