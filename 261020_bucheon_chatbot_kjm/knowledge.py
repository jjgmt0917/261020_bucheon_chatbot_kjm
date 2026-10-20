"""부천 관광지 지식 데이터 로드 + 프롬프트용 컨텍스트 생성.

장소가 20곳(약 6천 자)이라 전부 프롬프트에 넣고, 말투 예시만 질문과 유사한 것을 골라 붙인다.
"""
import json
import math
import os
from collections import Counter

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _bigrams(text):
    """공백/기호를 제거한 문자 2-gram 집합 (조사 때문에 단어 매칭이 어려운 한국어용)."""
    chars = "".join(c for c in text if c.isalnum())
    return {chars[i:i + 2] for i in range(len(chars) - 1)}


def _flat(value):
    if isinstance(value, (list, tuple)):
        return " ".join(_flat(v) for v in value)
    return str(value)


def _load():
    with open(os.path.join(DATA_DIR, "bucheon_places.json"), encoding="utf-8") as f:
        places = json.load(f)["records"]
    with open(os.path.join(DATA_DIR, "bucheon_qa_dataset.jsonl"), encoding="utf-8") as f:
        qa = [json.loads(line) for line in f if line.strip()]
    return places, qa


PLACES, QA = _load()

_qa_grams = [_bigrams(q["user"] + " " + _flat(q["keywords"])) for q in QA]


def _idf(grams_list):
    df = Counter(g for grams in grams_list for g in grams)
    n = len(grams_list)
    return {g: math.log((n + 1) / (c + 0.5)) for g, c in df.items()}


_qa_idf = _idf(_qa_grams)


def search_examples(query, k=2, min_score=4.0):
    """질문과 2-gram이 많이 겹치는(흔한 조각은 낮은 가중치) 예시 Q&A를 고른다."""
    q = _bigrams(query)
    scored = []
    for i, grams in enumerate(_qa_grams):
        score = sum(_qa_idf.get(g, 0) for g in q & grams)
        if score >= min_score:
            scored.append((score, i))
    scored.sort(reverse=True)
    return [QA[i] for _, i in scored[:k]]


def _place_line(p):
    return json.dumps({k: p[k] for k in
                       ("name", "category", "description", "activities",
                        "recommended_for", "cautions")}, ensure_ascii=False)


def build_context(query):
    """전체 장소 데이터 + 질문과 유사한 예시 답변을 프롬프트용 문자열로 만든다."""
    parts = [
        "## Knowledge base (the ONLY places you may recommend; one JSON per line)",
        *[_place_line(p) for p in PLACES],
    ]
    examples = search_examples(query)
    if examples:
        parts.append("\nExample answers (match this style and level of detail):")
        parts += [f"Q: {e['user']}\nA: {e['assistant']}" for e in examples]
    return "\n".join(parts)
