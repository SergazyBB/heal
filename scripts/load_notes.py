"""Загружает analysis/notes/*.jsonl (разборы агентов) в таблицу video_notes в data/heal.db.
Запуск: python3 scripts/load_notes.py
"""
import json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
c = sqlite3.connect(ROOT / "data" / "heal.db")
c.executescript(
    """
    DROP TABLE IF EXISTS video_notes;
    CREATE TABLE video_notes(video_id TEXT PRIMARY KEY, slice TEXT, summary TEXT, key_points TEXT, steps TEXT,
        situations TEXT, mistakes TEXT, concepts TEXT, hook_pattern TEXT, tone TEXT);
    """
)
ok = bad = 0
for f in sorted((ROOT / "analysis" / "notes").glob("*.jsonl")):
    slice_name = f.name.split(".")[0]
    for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            dump = lambda k: json.dumps(d.get(k, []), ensure_ascii=False)
            c.execute("INSERT OR REPLACE INTO video_notes VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (d["id"], slice_name, d.get("summary", ""), dump("key_points"), dump("steps"),
                       dump("situations"), dump("mistakes"), dump("concepts"), d.get("hook_pattern", ""), d.get("tone", "")))
            ok += 1
        except Exception as e:
            bad += 1
            print(f"{f.name}:{n}: {e}", file=sys.stderr)
c.commit()
print(f"загружено {ok}, ошибок {bad}")
