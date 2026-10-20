# 부천이 챗봇 (261020_bucheon_chatbot_kjm)

Groq API 기반 부천시 안내 챗봇 (Flask + 간단 웹 프론트).
Groq 한도 소진/오류 시 Gemini API로 자동 전환됩니다.

## 구조
```
README.md
.gitignore
261020_bucheon_chatbot_kjm/
  main.py            Flask 서버 + Groq/Gemini 호출
  templates/         채팅 화면 (index.html)
  static/            style.css, app.js
  requirements.txt   필요 라이브러리
  .env.example       환경변수 예시
```

## 사용법
1. 가상환경 및 설치
   ```bash
   cd 261020_bucheon_chatbot_kjm
   python -m venv venv
   venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```
2. `.env.example` 을 복사해 `.env` 생성 후 키 입력
   ```
   GROQ_API_KEY=...      # https://console.groq.com/keys
   GEMINI_API_KEY=...    # (선택) https://aistudio.google.com/apikey
   ```
3. 실행
   ```bash
   python main.py
   ```
4. 브라우저에서 http://127.0.0.1:5000 접속

## 동작
- 프론트가 대화 기록을 `/api/chat` 으로 전송 → 서버가 부천 안내 시스템 프롬프트를 붙여 Groq(`openai/gpt-oss-20b`) 호출
- Groq 실패(한도 소진 등) 시 Gemini(`gemini-2.5-flash`)로 재시도, 답변 하단에 사용된 제공자 표시

## 주의
- `.env` 는 `.gitignore` 로 제외되어 있습니다. API 키를 절대 커밋하지 마세요.
