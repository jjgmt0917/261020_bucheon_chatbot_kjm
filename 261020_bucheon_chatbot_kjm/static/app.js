const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = form.querySelector("button");
let history = [];

function add(role, text, extra = "") {
  const el = document.createElement("div");
  el.className = "msg " + role + (extra ? " " + extra : "");
  el.textContent = text; // textContent: XSS 방지
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function greet() {
  add("bot", "안녕하세요! 부천시 안내 챗봇 부천이예요 😊 무엇이 궁금하세요?");
}

async function send(text) {
  if (sendBtn.disabled) return;
  add("user", text);
  history.push({ role: "user", content: text });
  sendBtn.disabled = true;
  const loading = add("bot", "생각 중...");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "오류가 발생했습니다.");
    loading.textContent = data.answer;
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = "via " + data.provider;
    loading.appendChild(tag);
    history.push({ role: "assistant", content: data.answer });
  } catch (e) {
    loading.textContent = e.message;
    loading.classList.add("err");
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
