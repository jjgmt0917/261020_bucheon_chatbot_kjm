import itertools
import os
import time

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from groq import Groq

# 1. 환경 변수 불러오기 (.env)
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GROQ_MODEL = "openai/gpt-oss-20b"
GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are 'Bucheon-i', a friendly guide chatbot for Bucheon City, Gyeonggi-do, South Korea. "
    "Help users with attractions (Bucheon Central Park, Woongjin Playdoci, Korea Manhwa Museum, etc.), "
    "restaurants, transportation (Subway Lines 1 and 7, Seohae Line), festivals "
    "(Bucheon International Fantastic Film Festival, etc.), and local living information. "
    "Keep answers concise and warm. "
    "Always reply in Korean, unless the user writes in another language. "
    "If you are not sure about something, do not guess; "
    "recommend checking official sources such as the Bucheon City Hall website. "
    "You may use Markdown (bold, lists) for readability. "
    "Whenever you mention a specific place, wrap its name like [[Place Name]] "
    "(e.g. [[한국만화박물관]]) so the UI can turn it into a map link. "
    "Use the current weather below when it is relevant "
    "(e.g. suggest indoor places when it rains)."
)

MAX_HISTORY = 20  # 서버로 보내는 최근 대화 수 제한

# 부천시청 좌표 (Open-Meteo, API 키 불필요)
LAT, LON = 37.5034, 126.7660
WEATHER_TTL = 600  # 초 단위 캐시
WEATHER_CODES = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "안개", 51: "이슬비", 53: "이슬비", 55: "이슬비",
    61: "비", 63: "비", 65: "강한 비", 71: "눈", 73: "눈", 75: "강한 눈",
    80: "소나기", 81: "소나기", 82: "강한 소나기", 95: "뇌우", 96: "뇌우", 99: "뇌우",
}
_weather_cache = {"at": 0, "data": None}

app = Flask(__name__)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def get_weather():
    """부천 현재 날씨. 실패하면 None."""
    now = time.time()
    if _weather_cache["data"] and now - _weather_cache["at"] < WEATHER_TTL:
        return _weather_cache["data"]
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": LAT, "longitude": LON, "timezone": "Asia/Seoul",
                    "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m"},
            timeout=5,
        )
        r.raise_for_status()
        cur = r.json()["current"]
        data = {
            "temp": round(cur["temperature_2m"]),
            "feels": round(cur["apparent_temperature"]),
            "wind": cur["wind_speed_10m"],
            "desc": WEATHER_CODES.get(cur["weather_code"], "알 수 없음"),
        }
        _weather_cache.update(at=now, data=data)
        return data
    except Exception as e:
        app.logger.warning("날씨 조회 실패: %s", e)
        return _weather_cache["data"]


def build_system_prompt():
    w = get_weather()
    if not w:
        return SYSTEM_PROMPT
    return (f"{SYSTEM_PROMPT}\nCurrent weather in Bucheon: {w['desc']}, {w['temp']}°C "
            f"(feels like {w['feels']}°C), wind {w['wind']} km/h.")


def stream_groq(messages):
    stream = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.5,
        max_completion_tokens=1000,
        reasoning_effort="low",
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def ask_gemini(messages, system_prompt):
    """Groq 한도 소진/오류 시 대체 호출 (REST, 비스트리밍)."""
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user",
         "parts": [{"text": m["content"]}]}
        for m in messages if m["role"] != "system"
    ]
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    r = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={"systemInstruction": {"parts": [{"text": system_prompt}]},
              "contents": contents},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/weather")
def weather():
    w = get_weather()
    if not w:
        return jsonify(error="날씨 정보를 가져오지 못했습니다."), 502
    return jsonify(w)


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    history = [
        {"role": m["role"], "content": str(m["content"])}
        for m in data.get("messages", [])
        if m.get("role") in ("user", "assistant") and m.get("content")
    ][-MAX_HISTORY:]
    if not history:
        return jsonify(error="메시지가 비어 있습니다."), 400

    system_prompt = build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + history

    def text_response(chunks, provider):
        return Response(stream_with_context(chunks), mimetype="text/plain; charset=utf-8",
                        headers={"X-Provider": provider, "Cache-Control": "no-cache",
                                 "X-Accel-Buffering": "no"})

    # 1순위 Groq(스트리밍) -> 첫 토큰 전에 실패(한도 소진 등)하면 Gemini
    if groq_client:
        try:
            gen = stream_groq(messages)
            first = next(gen)  # 여기서 429 등 오류가 나면 폴백
            return text_response(itertools.chain([first], gen), "groq")
        except StopIteration:
            return jsonify(error="빈 응답이 돌아왔습니다."), 502
        except Exception as e:
            app.logger.warning("Groq 실패, Gemini로 전환: %s", e)
    if GEMINI_API_KEY:
        try:
            return text_response([ask_gemini(messages, system_prompt)], "gemini")
        except Exception as e:
            app.logger.error("Gemini 실패: %s", e)
            return jsonify(error="AI 응답 중 오류가 발생했습니다."), 502
    return jsonify(error="API 키가 설정되지 않았거나 모두 실패했습니다. .env 를 확인하세요."), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
