"""Находит темы во всём корпусе расшифровок снизу вверх (TF-IDF + NMF), без заранее заданных рубрик.

Нужно: pip install scikit-learn pymorphy3
Запуск из корня репозитория:  python3 scripts/discover_topics.py [число_тем]
Результат: analysis/topics/topics_N.md (темы, ключевые слова, размеры, примеры заголовков)
          analysis/topics/doc_topics_N.csv (видео -> основная тема)
"""
import csv
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pymorphy3
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
K = int(sys.argv[1]) if len(sys.argv) > 1 else 40
OUT = ROOT / "analysis" / "topics"
OUT.mkdir(parents=True, exist_ok=True)

morph = pymorphy3.MorphAnalyzer()
cache = {}
KEEP_POS = {"NOUN", "ADJF", "VERB", "INFN", "ADVB"}
TOKEN = re.compile(r"[а-яёіїєґ]{4,}")
STOP = set("""это этот этом этого этим как так там тут когда потому почему который которая которые просто очень
вообще значит например конечно хорошо сказать говорить делать сделать быть стать мочь хотеть знать понимать
думать смотреть видео канал подписаться ссылка описание подписывайтесь лайк комментарий друзья друг ребята
тоже сейчас теперь сразу всегда никогда иногда чтобы чтоб если есть нужно надо можно нельзя должен
человек люди мужчина женщина девушка парень отношение история ситуация вопрос ответ""".split())


def lemma(w):
    r = cache.get(w)
    if r is None:
        p = morph.parse(w)[0]
        r = p.normal_form if (p.tag.POS in KEEP_POS) else ""
        cache[w] = r
    return r


def tokens(text):
    out = []
    for w in TOKEN.findall(text.lower()):
        l = lemma(w)
        if l and l not in STOP:
            out.append(l)
    return " ".join(out)


con = sqlite3.connect(ROOT / "data" / "heal.db")
rows = con.execute(
    "select id,channel,section,title,words,text from videos where status='готово' and words>=150"
).fetchall()
print(len(rows), "видео в анализе", file=sys.stderr)
docs = [tokens((t + " ") * 3 + body) for _, _, _, t, _, body in rows]

vec = TfidfVectorizer(max_df=0.35, min_df=6, max_features=25000, sublinear_tf=True)
X = vec.fit_transform(docs)
terms = np.array(vec.get_feature_names_out())
print("матрица", X.shape, file=sys.stderr)

nmf = NMF(n_components=K, init="nndsvda", random_state=0, max_iter=400)
W = nmf.fit_transform(X)
H = nmf.components_
main = W.argmax(axis=1)

lines = [f"# Темы корпуса (NMF, {K} тем, {len(rows)} видео с текстом)\n"]
order = np.argsort([-(main == k).sum() for k in range(K)])
for k in order:
    idx = np.where(main == k)[0]
    top = terms[H[k].argsort()[::-1][:14]]
    ch = Counter(rows[i][1] for i in idx).most_common(4)
    words = sum(rows[i][4] for i in idx)
    ranked = idx[np.argsort(-W[idx, k])][:8]
    lines.append(f"## Тема {k}: {', '.join(top[:8])}")
    lines.append(f"Видео: {len(idx)}, слов: {words:,}. Каналы: " + "; ".join(f"{c} {n}" for c, n in ch))
    lines.append("Ещё слова: " + ", ".join(top[8:]))
    lines.append("Примеры заголовков:")
    for i in ranked:
        lines.append(f"- {rows[i][3][:110]} [{rows[i][1].split()[0]}]")
    lines.append("")
(OUT / f"topics_{K}.md").write_text("\n".join(lines), encoding="utf-8")
with open(OUT / f"doc_topics_{K}.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["video_id", "channel", "section", "words", "topic", "weight", "title"])
    for i, r in enumerate(rows):
        w.writerow([r[0], r[1], r[2], r[4], int(main[i]), round(float(W[i, main[i]]), 4), r[3]])
print("готово:", OUT / f"topics_{K}.md")
