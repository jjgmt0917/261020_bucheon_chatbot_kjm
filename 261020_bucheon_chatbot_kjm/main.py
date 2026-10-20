import os
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
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
    "recommend checking official sources such as the Bucheon City Hall website."
)

MAX_HISTORY = 20  # 서버로 보내는 최근 대화 수 제한

app = Flask(__name__)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def ask_groq(messages):
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.5,
        max_completion_tokens=1000,
        reasoning_effort="low",
    )
    return res.choices[0].message.content


def ask_gemini(messages):
    """Groq 한도 소진/오류 시 대체 호출 (REST)."""
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
        json={"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
              "contents": contents},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


@app.route("/")
def index():
    return render_template("index.html")


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

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # 1순위 Groq -> 실패(한도 소진 등) 시 Gemini
    if groq_client:
        try:
            return jsonify(answer=ask_groq(messages), provider="groq")
        except Exception as e:
            app.logger.warning("Groq 실패, Gemini로 전환: %s", e)
    if GEMINI_API_KEY:
        try:
            return jsonify(answer=ask_gemini(messages), provider="gemini")
        except Exception as e:
            app.logger.error("Gemini 실패: %s", e)
            return jsonify(error="AI 응답 중 오류가 발생했습니다."), 502
    return jsonify(error="API 키가 설정되지 않았거나 모두 실패했습니다. .env 를 확인하세요."), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
