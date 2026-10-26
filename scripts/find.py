"""Поиск по корпусу расшифровок.
  python3 scripts/find.py "пинг игнор" [N]     -> топ-N видео по полнотекстовому поиску (заголовок, канал, выдержка)
  python3 scripts/find.py --notes "пинг" [N]   -> то же по разборам агентов (summary/ключевые мысли)
  python3 scripts/find.py --show VIDEO_ID [MAXCHARS]  -> чистый текст видео (по умолчанию 6000 символов)
Слова ищутся по точной форме (без морфологии): используй несколько форм или префикс со звёздочкой: игнор*
Читай как источник идей и фактов; в курс переносить своими словами, не дословно.
"""
import json, sqlite3, sys
from pathlib import Path
c = sqlite3.connect(Path(__file__).resolve().parent.parent / "data" / "heal.db")
a = sys.argv[1:]
if not a: print(__doc__); sys.exit()
if a[0] == "--show":
    r = c.execute("select channel,title,date,text from videos where id=?", (a[1],)).fetchone()
    n = int(a[2]) if len(a) > 2 else 6000
    print(f"[{r[0]}] {r[1]} ({r[2]})\n{r[3][:n]}")
elif a[0] == "--notes":
    q = a[1]; n = int(a[2]) if len(a) > 2 else 8
    rows = c.execute("""select v.id,v.channel,v.title,n.summary,n.key_points from video_notes n join videos v on v.id=n.video_id
        where v.id in (select v2.id from videos_fts f join videos v2 on v2.rowid=f.rowid where videos_fts match ?)
        limit ?""", (q, n)).fetchall()
    for i, ch, t, s, kp in rows:
        print(f"- {i} [{ch.split()[0]}] {t[:90]}\n  {s}\n  мысли: {'; '.join(json.loads(kp)[:4])}")
else:
    q = a[0]; n = int(a[1]) if len(a) > 1 else 8
    rows = c.execute("""select v.id,v.channel,v.title,snippet(videos_fts,1,'[',']','…',24)
        from videos_fts join videos v on v.rowid=videos_fts.rowid where videos_fts match ? order by rank limit ?""", (q, n)).fetchall()
    for i, ch, t, sn in rows:
        print(f"- {i} [{ch.split()[0]}] {t[:90]}\n  {sn}")
