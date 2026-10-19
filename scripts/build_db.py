"""Собирает data/heal.db (SQLite + FTS5) из zip-архивов расшифровок в корне репозитория.

Запуск из корня репозитория:  python3 scripts/build_db.py
Таблицы:
  videos(id, channel, section, title, date, duration, words, url, status, text)
  videos_fts(title, text)         -- полнотекстовый поиск (rowid = videos.rowid)
  tags(video_id, course, score, title_hit)  -- мультиметки по 8 темам курсов
"""
import json
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "heal.db"

CHANNELS = {
    "alex_staseev": "Alex Staseev",
    "divertitomax": "Максим Дівертіто",
    "hotpsychologies": "Hotpsychologies (Юшкевич)",
    "maxim_verdict": "Максим Вердикт",
    "vapsychology": "Винсент Александр",
    "yurishelest": "Юрий Шелест",
}

# Темы курсов: регулярки по стемам (рус. + укр.), всё в нижнем регистре.
COURSES = {
    "return_ex": r"верн\w*|бывш\w+|расстав\w+|разрыв\w*|колишн\w+|розстав\w+|ломк\w+",
    "balance_respect": r"уважен\w+|значимост\w+|ценност\w+|ценит\w*|самооценк\w+|вкладыва\w+|баланс\w*|цінн\w+|поваг\w+",
    "distance_pause": r"дистанц\w+|пауз\w+|игнор\w*|молчан\w+|отстран\w+|холодн\w+|отдал\w+|не писа\w+|не звон\w+|дистанці\w+",
    "attachment": r"привязанн\w+|тревожн\w+|избегающ\w+|аттач\w*|созависим\w+|травм\w+",
    "infidelity_jealousy": r"измен\w*|ревн\w+|предат\w+|предал\w*|неверн\w+|зрад\w+|ревнощ\w+|любовник\w*|любовниц\w*",
    "toxic_boundaries": r"токсич\w+|манипул\w+|нарцисс\w+|границ\w+|абьюз\w*|газлайт\w*|унижен\w+|контрол\w+|шантаж\w*|давлен\w+",
    "marriage_divorce": r"брак\w*|развод\w*|жен[аыуе]\b|мужа\b|супруг\w*|свекр\w+|тёщ\w+|тещ\w+|ребён\w+|семь\w+",
    "dating": r"знакомств\w+|знакомит\w+|встретить|одиноч\w+|свидани\w+|привлеч\w+|познайом\w+|самотн\w+",
}
COURSE_RE = {k: re.compile(v) for k, v in COURSES.items()}
TS_RE = re.compile(r"^\[\d\d:\d\d:\d\d\]\s*", re.M)
ID_RE = re.compile(r"\[([\w-]{11})\]\.txt$")


def clean(raw: str) -> str:
    raw = raw.lstrip("\ufeff")
    body = raw.split("--- РАСШИФРОВКА ---", 1)[-1]
    body = TS_RE.sub("", body)
    return re.sub(r"\s+", " ", body).strip()


def tag(title: str, text: str, words: int):
    t = title.lower()
    low = text.lower()
    rows = []
    for course, rx in COURSE_RE.items():
        title_hit = len(rx.findall(t))
        density = len(rx.findall(low)) * 1000 / max(words, 1)
        score = round(title_hit * 5 + density, 2)
        if title_hit or density >= 4:
            rows.append((course, score, int(title_hit > 0)))
    return rows


def main():
    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(
        """
        CREATE TABLE videos(id TEXT PRIMARY KEY, channel TEXT, section TEXT, title TEXT,
            date TEXT, duration INTEGER, words INTEGER, url TEXT, status TEXT, text TEXT);
        CREATE VIRTUAL TABLE videos_fts USING fts5(title, text, content='videos', content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 2');
        CREATE TABLE tags(video_id TEXT, course TEXT, score REAL, title_hit INTEGER);
        """
    )
    total = 0
    for zpath in sorted(ROOT.glob("*.zip")):
        key = next((k for k in CHANNELS if zpath.name.startswith(k)), None)
        if key is None:
            continue
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            mpath = next(n for n in names if n.endswith("manifest.json"))
            manifest = json.loads(z.read(mpath).decode("utf-8-sig"))
            by_id = {}
            for n in names:
                m = ID_RE.search(n)
                if m and n.endswith(".txt") and "ALL_TRANSCRIPTS" not in n and "MISSING" not in n:
                    by_id[m.group(1)] = n
            for v in manifest:
                text = ""
                if v["id"] in by_id and v.get("status") == "готово":
                    text = clean(z.read(by_id[v["id"]]).decode("utf-8-sig"))
                words = v.get("word_count") or len(text.split())
                d = v["upload_date"]
                con.execute(
                    "INSERT INTO videos VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (v["id"], CHANNELS[key], v["section"], v["title"], f"{d[:4]}-{d[4:6]}-{d[6:]}",
                     v.get("duration_seconds"), words, v["url"], v.get("status"), text),
                )
                if text:
                    con.executemany(
                        "INSERT INTO tags VALUES(?,?,?,?)",
                        [(v["id"], c, s, h) for c, s, h in tag(v["title"], text, words)],
                    )
                total += 1
        print(f"{CHANNELS[key]}: ok", file=sys.stderr)
    con.execute("INSERT INTO videos_fts(rowid,title,text) SELECT rowid,title,text FROM videos")
    con.commit()
    con.execute("VACUUM")
    con.close()
    print(f"{total} видео -> {DB} ({DB.stat().st_size/1e6:.1f} МБ)")


if __name__ == "__main__":
    main()
