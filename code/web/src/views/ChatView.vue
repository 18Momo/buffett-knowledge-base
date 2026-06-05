<script setup>
import MarkdownIt from "markdown-it";
import { computed, nextTick, ref } from "vue";

const md = new MarkdownIt({ html: true, linkify: true, breaks: true });
const password = ref("");
const verified = ref(false);
const error = ref("");
const input = ref("");
const loading = ref(false);
const sources = ref([]);
const messages = ref([]);
const messagesEl = ref(null);

function scrollToBottom() {
  nextTick(() => {
    messagesEl.value?.scrollTo({
      top: messagesEl.value.scrollHeight,
      behavior: "smooth",
    });
  });
}

const renderedMessages = computed(() =>
  messages.value.map((item) => ({
    ...item,
    html: md.render(item.content || ""),
  })),
);

async function verify() {
  error.value = "";
  try {
    const response = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: password.value }),
    });
    if (!response.ok) {
      error.value = "密码错误，请重试。";
      return;
    }
    verified.value = true;
  } catch (fetchError) {
    error.value = "无法连接后端服务。";
  }
}

async function send() {
  if (!input.value.trim() || loading.value) {
    return;
  }
  const userText = input.value.trim();
  messages.value.push({ role: "user", content: userText });
  messages.value.push({ role: "assistant", content: "思考中..." });
  const assistantIndex = messages.value.length - 1;
  input.value = "";
  loading.value = true;
  sources.value = [];
  scrollToBottom();

  let response;
  try {
    response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        password: password.value,
        messages: messages.value
          .slice(0, -1)
          .map(({ role, content }) => ({ role, content })),
      }),
    });
  } catch (fetchError) {
    loading.value = false;
    messages.value[assistantIndex] = { role: "assistant", content: "无法连接后端服务，请先启动 Express API。" };
    return;
  }

  if (!response.ok || !response.body) {
    loading.value = false;
    let detail = "请求失败，请检查后端配置。";
    try {
      const payload = await response.json();
      detail = payload.error || detail;
    } catch (parseError) {
      detail = `${detail} HTTP ${response.status}`;
    }
    messages.value[assistantIndex] = { role: "assistant", content: detail };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let content = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part
        .split("\n")
        .find((entry) => entry.startsWith("data: "));
      if (!line) {
        continue;
      }
      const payload = JSON.parse(line.slice(6));
      if (payload.text) {
        content += payload.text;
        messages.value[assistantIndex] = { role: "assistant", content };
        scrollToBottom();
      }
      if (payload.sources) {
        sources.value = payload.sources;
      }
      if (payload.error) {
        messages.value[assistantIndex] = { role: "assistant", content: payload.error };
      }
    }
  }

  if (!content) {
    messages.value[assistantIndex] = { role: "assistant", content: "没有收到有效回复。" };
  }
  loading.value = false;
  scrollToBottom();
}

function onInputKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    send();
  }
}
</script>

<template>
  <div class="page chat-page">
    <div v-if="!verified" class="auth-wrap">
      <div class="auth-panel">
        <div style="font-size: 32px;">🔐</div>
        <h1 class="section-title" style="margin-top: 8px;">访问密码</h1>
        <p class="muted">输入访问密码后进入 AI 巴菲特对话。</p>
        <input v-model="password" class="auth-input" type="password" @keyup.enter="verify" />
        <p v-if="error" class="error">{{ error }}</p>
        <button class="btn btn-primary" style="margin-top: 12px;" @click="verify">确认进入</button>
      </div>
    </div>

    <div v-else class="chat-panel">
      <div class="chat-hero">
        <h1>AI 巴菲特</h1>
        <p>基于预编译 Wiki 页面回答问题，强调长期主义、估值、能力圈与资本配置。</p>
      </div>

      <div v-if="!messages.length" class="empty-state">
        <div style="font-size: 42px;">🎩</div>
        <p>可以问：巴菲特为什么强调安全边际？喜诗糖果如何改变了他的投资框架？</p>
      </div>

      <div ref="messagesEl" class="messages">
        <div v-for="(item, index) in renderedMessages" :key="index" class="message-row" :class="item.role">
          <div v-if="item.role === 'assistant'" class="message-avatar">🎩</div>
          <div class="bubble" v-html="item.html"></div>
          <div v-if="item.role === 'user'" class="message-avatar">👤</div>
        </div>
      </div>

      <div v-if="sources.length" class="source-list">参考页面：{{ sources.join("、") }}</div>

      <div class="chat-input">
        <textarea
          v-model="input"
          placeholder="输入你的问题，Enter 发送，Shift + Enter 换行"
          @keydown="onInputKeydown"
        ></textarea>
        <button class="btn btn-primary" :disabled="loading" @click="send">{{ loading ? "生成中" : "发送" }}</button>
      </div>
    </div>
  </div>
</template>
