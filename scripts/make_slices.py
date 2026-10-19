"""Режет расшифровки на пачки (~65k слов) по курсам для параллельного разбора агентами.
Результат: .work/slices/<course>_<nn>.txt  (не коммитится) и .work/slices/MANIFEST.json
"""
import json, sqlite3, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".work" / "slices"
CAPS = {  # лимит слов на курс (первый проход)
    "return_ex": 500_000, "balance_respect": 250_000, "attachment": 200_000,
    "marriage_divorce": 200_000, "toxic_boundaries": 200_000, "infidelity_jealousy": 200_000,
    "distance_pause": 130_000, "dating": 100_000,
}
SLICE_WORDS = 65_000

c = sqlite3.connect(ROOT / "data" / "heal.db")
best = {}
for vid, w, sec, course, s, h in c.execute(
    "select v.id,v.words,v.section,t.course,t.score,t.title_hit from videos v join tags t on t.video_id=v.id where v.words>=80"
):
    if sec == "streams" and w > 20000:
        continue
    if vid not in best or s > best[vid][1]:
        best[vid] = (course, s, h, w)

OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*"):
    f.unlink()
manifest = {}
for course, cap in CAPS.items():
    ids = sorted((v for v, b in best.items() if b[0] == course), key=lambda v: (-best[v][2], -best[v][1]))
    chosen, tot = [], 0
    for v in ids:
        if tot + best[v][3] > cap:
            continue
        chosen.append(v); tot += best[v][3]
    slices, cur, cw = [], [], 0
    for v in chosen:
        if cw + best[v][3] > SLICE_WORDS and cur:
            slices.append(cur); cur, cw = [], 0
        cur.append(v); cw += best[v][3]
    if cur:
        slices.append(cur)
    for i, sl in enumerate(slices, 1):
        name = f"{course}_{i:02d}"
        lines = []
        for v in sl:
            ch, sec, date, title, text, w = c.execute(
                "select channel,section,date,title,text,words from videos where id=?", (v,)).fetchone()
            lines.append(f"=== {v} | {ch} | {sec} | {date} | {w} слов | {title}")
            lines.extend(textwrap.wrap(text, 140))
            lines.append("")
        (OUT / f"{name}.txt").write_text("\n".join(lines), encoding="utf-8")
        manifest[name] = {"course": course, "videos": len(sl), "words": sum(best[v][3] for v in sl), "ids": sl}
    print(f"{course}: {len(chosen)} видео, {tot:,} слов, пачек {len(slices)}")
(OUT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print("всего пачек", len(manifest), "слов", sum(m["words"] for m in manifest.values()))
