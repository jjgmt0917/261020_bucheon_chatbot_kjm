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

## 기능
- **스트리밍 답변:** 생성되는 대로 실시간으로 표시
- **마크다운 렌더링:** 굵게/목록/표를 보기 좋게 표시 (marked + DOMPurify로 XSS 방지)
- **지도 연동:** 답변 속 장소명을 카카오맵 검색 링크(📍)로 변환 (API 키 불필요)
- **날씨 연동:** Open-Meteo로 부천 현재 날씨를 가져와 헤더에 표시하고 프롬프트에 반영 (API 키 불필요)
- **Gemini 폴백:** Groq가 시작 전에 실패(한도 소진 등)하면 Gemini로 재시도 (답변 하단에 제공자 표시)

## 동작
- 프론트가 대화 기록을 `/api/chat` 으로 전송 → 서버가 부천 안내 프롬프트 + 현재 날씨를 붙여 Groq(`openai/gpt-oss-20b`)를 스트리밍 호출
- `/api/weather` 는 헤더의 날씨 표시용 (10분 캐시)

## 주의
- `.env` 는 `.gitignore` 로 제외되어 있습니다. API 키를 절대 커밋하지 마세요.
