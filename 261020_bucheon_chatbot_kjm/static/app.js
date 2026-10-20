const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = form.querySelector("button");
let history = [];

// 링크는 새 탭에서 열기 (DOMPurify 정제 후)
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A") {
    node.setAttribute("target", "_blank");
    node.setAttribute("rel", "noopener noreferrer");
  }
});

// [[장소명]] -> 카카오맵 검색 링크 (API 키 불필요)
// [[ ]] 없이 쓴 장소명도 지식 데이터의 이름과 같으면 링크로 바꾼다 (/api/places)
let placeNames = [];
let linkRe = /\[\[([^\[\]\n]+?)\]\]/g;

async function loadPlaces() {
  try {
    const res = await fetch("/api/places");
    if (!res.ok) return;
    placeNames = (await res.json()).names.sort((a, b) => b.length - a.length);
    const esc = placeNames.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    linkRe = new RegExp("\\[\\[([^\\[\\]\\n]+?)\\]\\]" + (esc.length ? "|(" + esc.join("|") + ")" : ""), "g");
  } catch (_) { /* 이름 목록이 없어도 [[ ]] 변환은 동작 */ }
}

function withMapLinks(text) {
  return text.replace(linkRe, (_, bracketed, plain) => {
    const name = (bracketed || plain).trim();
    const q = encodeURIComponent("부천 " + name);
    return `[📍 ${name}](https://map.kakao.com/link/search/${q})`;
  });
}

// 마크다운 -> 안전한 HTML
function render(el, text) {
  el.innerHTML = DOMPurify.sanitize(marked.parse(withMapLinks(text), { breaks: true }));
}

function scrollToBottom() {
  window.scrollTo(0, document.documentElement.scrollHeight);
}

function add(role, text, extra = "") {
  const el = document.createElement("div");
  el.className = "msg " + role + (extra ? " " + extra : "");
  el.textContent = text; // 사용자 입력/상태 문구는 textContent (XSS 방지)
  log.appendChild(el);
  scrollToBottom();
  return el;
}

function greet() {
  add("bot", "안녕하세요! 부천시 안내 챗봇 부천이예요 😊 무엇이 궁금하세요?");
}

async function loadWeather() {
  const box = document.getElementById("weather");
  try {
    const res = await fetch("/api/weather");
    if (!res.ok) return;
    const w = await res.json();
    box.textContent = `${w.desc} ${w.temp}°C`;
  } catch (_) { /* 날씨 표시는 선택 기능 */ }
}

async function send(text) {
  if (sendBtn.disabled) return;
  add("user", text);
  history.push({ role: "user", content: text });
  sendBtn.disabled = true;
  const bot = add("bot", "생각 중...");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "오류가 발생했습니다.");
    }
    // 스트리밍: 도착하는 대로 이어 붙여 렌더링
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let answer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      answer += decoder.decode(value, { stream: true });
      render(bot, answer);
      scrollToBottom();
    }
    if (!answer.trim()) throw new Error("빈 응답이 돌아왔습니다.");
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = "via " + res.headers.get("X-Provider");
    bot.appendChild(tag);
    history.push({ role: "assistant", content: answer });
  } catch (e) {
    bot.textContent = e.message;
    bot.classList.add("err");
    history.pop(); // 실패한 질문은 기록에서 제거
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  send(text);
});

document.querySelectorAll(".chips button").forEach((b) =>
  b.addEventListener("click", () => send(b.textContent)));

document.getElementById("reset").addEventListener("click", () => {
  history = [];
  log.innerHTML = "";
  greet();
});

greet();
loadWeather();
loadPlaces();
