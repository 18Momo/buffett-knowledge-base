import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import cors from "cors";
import Anthropic from "@anthropic-ai/sdk";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.join(__dirname, "public");
const dataDir = path.join(publicDir, "data");
const wikiIndexPath = path.join(dataDir, "wiki-index.json");
const graphPath = path.join(dataDir, "graph.json");
const pagesDir = path.join(dataDir, "pages");

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use("/data", express.static(dataDir));

const accessPassword = process.env.ACCESS_PASSWORD || "";
const aiProvider = process.env.AI_PROVIDER || (process.env.DEEPSEEK_API_KEY ? "deepseek" : "anthropic");
const deepseekKey = process.env.DEEPSEEK_API_KEY;
const deepseekBaseUrl = process.env.DEEPSEEK_BASE_URL || "https://api.deepseek.com";
const deepseekModel = process.env.DEEPSEEK_MODEL || "deepseek-chat";
const anthropicKey = process.env.ANTHROPIC_API_KEY;
const anthropicBaseUrl = process.env.ANTHROPIC_BASE_URL;
const anthropicModel = process.env.ANTHROPIC_MODEL || "claude-sonnet-4-6";

const state = {
  wikiIndex: [],
  graph: { nodes: [], edges: [] },
  neighbors: new Map(),
  indexByTitle: new Map(),
};

function normalizeText(value = "") {
  return String(value).toLowerCase().replace(/\s+/g, " ").trim();
}

function toNgrams(text) {
  const compact = text.replace(/\s+/g, "");
  const set = new Set();
  for (let size = 2; size <= 4; size += 1) {
    for (let i = 0; i <= compact.length - size; i += 1) {
      set.add(compact.slice(i, i + size));
    }
  }
  for (const part of text.split(/\s+/).filter(Boolean)) {
    set.add(part.toLowerCase());
  }
  return [...set];
}

function buildGraphIndexes() {
  state.neighbors = new Map();
  state.indexByTitle = new Map();

  for (const page of state.wikiIndex) {
    state.indexByTitle.set(page.title, page);
    if (!state.neighbors.has(page.title)) {
      state.neighbors.set(page.title, new Set());
    }
  }

  for (const edge of state.graph.edges) {
    if (!state.neighbors.has(edge.source)) {
      state.neighbors.set(edge.source, new Set());
    }
    if (!state.neighbors.has(edge.target)) {
      state.neighbors.set(edge.target, new Set());
    }
    state.neighbors.get(edge.source).add(edge.target);
    state.neighbors.get(edge.target).add(edge.source);
  }
}

async function loadData() {
  try {
    state.wikiIndex = JSON.parse(await fs.readFile(wikiIndexPath, "utf8"));
    state.graph = JSON.parse(await fs.readFile(graphPath, "utf8"));
    buildGraphIndexes();
    console.log(`Loaded ${state.wikiIndex.length} pages and ${state.graph.edges.length} edges`);
  } catch (error) {
    console.warn("Data preload skipped:", error.message);
  }
}

function scorePage(page, question, ngrams) {
  const title = normalizeText(page.title);
  const summary = normalizeText(page.summary);
  const links = (page.links || []).map((item) => normalizeText(item));
  let score = 0;

  if (!title) {
    return 0;
  }
  if (question.includes(title)) {
    score += 50;
  }
  if (title.includes(question) && question) {
    score += 40;
  }
  for (const gram of ngrams) {
    if (title.includes(gram)) {
      score += 8;
    }
    if (summary.includes(gram)) {
      score += 3;
    }
  }
  for (const link of links) {
    if (link && question.includes(link)) {
      score += 6;
    }
  }
  return score;
}

function retrieveRelevantPages(questionText) {
  const question = normalizeText(questionText);
  const ngrams = toNgrams(question);
  const scored = state.wikiIndex
    .map((page) => ({ page, score: scorePage(page, question, ngrams) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score);

  const direct = scored.slice(0, 4).map((item) => item.page);
  const seen = new Set(direct.map((page) => page.title));
  const expanded = [...direct];

  for (const page of direct) {
    const neighbors = [...(state.neighbors.get(page.title) || [])];
    for (const neighborTitle of neighbors) {
      if (seen.has(neighborTitle)) {
        continue;
      }
      const neighbor = state.indexByTitle.get(neighborTitle);
      if (!neighbor) {
        continue;
      }
      const score = scorePage(neighbor, question, ngrams);
      if (score <= 0) {
        continue;
      }
      expanded.push(neighbor);
      seen.add(neighborTitle);
      if (expanded.length >= 6) {
        return expanded;
      }
    }
  }

  return expanded;
}

async function loadPageContext(page) {
  const filePath = path.join(pagesDir, page.category, `${page.slug}.md`);
  const text = await fs.readFile(filePath, "utf8");
  return text.slice(0, 3000);
}

function fallbackResponse(question) {
  if (!question) {
    return "请先告诉我你想了解的概念、公司、人物或某封股东信。";
  }
  return `知识库里暂时没有足够直接匹配“${question}”的页面。你可以换一种问法，或者直接指出相关对象，例如“安全边际”“喜诗糖果”“1973年股东信”。`;
}

function writeSseHeaders(res) {
  res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();
}

function missingKeyMessage() {
  if (aiProvider === "deepseek") {
    return "缺少 DEEPSEEK_API_KEY";
  }
  return "缺少 ANTHROPIC_API_KEY";
}

function hasRealKey(value) {
  return Boolean(value && !value.startsWith("your-"));
}

async function streamAnthropic({ prompt, messages, res }) {
  const client = new Anthropic({
    apiKey: anthropicKey,
    baseURL: anthropicBaseUrl,
  });

  const stream = await client.messages.stream({
    model: anthropicModel,
    max_tokens: 2048,
    temperature: 0.4,
    system: prompt,
    messages: messages.map((item) => ({
      role: item.role,
      content: item.content,
    })),
  });

  for await (const chunk of stream) {
    if (chunk.type === "content_block_delta" && chunk.delta?.type === "text_delta") {
      res.write(`data: ${JSON.stringify({ text: chunk.delta.text })}\n\n`);
    }
  }
}

async function streamDeepSeek({ prompt, messages, res }) {
  const response = await fetch(`${deepseekBaseUrl.replace(/\/$/, "")}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${deepseekKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: deepseekModel,
      stream: true,
      temperature: 0.4,
      max_tokens: 2048,
      messages: [
        { role: "system", content: prompt },
        ...messages.map((item) => ({
          role: item.role === "assistant" ? "assistant" : "user",
          content: item.content,
        })),
      ],
    }),
  });

  if (!response.ok || !response.body) {
    const errorText = await response.text();
    throw new Error(`DeepSeek API 请求失败：${response.status} ${errorText}`);
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  for await (const chunk of response.body) {
    buffer += decoder.decode(chunk, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n").filter((line) => line.startsWith("data: "));
      for (const line of lines) {
        const payload = line.slice(6).trim();
        if (!payload || payload === "[DONE]") {
          continue;
        }
        const json = JSON.parse(payload);
        const text = json.choices?.[0]?.delta?.content;
        if (text) {
          res.write(`data: ${JSON.stringify({ text })}\n\n`);
        }
      }
    }
  }
}

app.post("/api/auth", (req, res) => {
  const { password } = req.body || {};
  if (!accessPassword) {
    return res.json({ ok: true, disabled: true });
  }
  if (password === accessPassword) {
    return res.json({ ok: true });
  }
  return res.status(401).json({ ok: false, error: "密码错误" });
});

app.post("/api/chat", async (req, res) => {
  const { messages = [], password } = req.body || {};
  if (accessPassword && password !== accessPassword) {
    return res.status(401).json({ error: "未授权访问" });
  }
  if (aiProvider === "deepseek" && !hasRealKey(deepseekKey)) {
    return res.status(500).json({ error: missingKeyMessage() });
  }
  if (aiProvider !== "deepseek" && !hasRealKey(anthropicKey)) {
    return res.status(500).json({ error: missingKeyMessage() });
  }

  const latestUserMessage = [...messages].reverse().find((item) => item.role === "user");
  const relevantPages = retrieveRelevantPages(latestUserMessage?.content || "");
  if (!relevantPages.length) {
    writeSseHeaders(res);
    res.write(`data: ${JSON.stringify({ text: fallbackResponse(latestUserMessage?.content || "") })}\n\n`);
    res.write(`data: ${JSON.stringify({ done: true, sources: [] })}\n\n`);
    return res.end();
  }

  const contextBlocks = await Promise.all(
    relevantPages.map(async (page) => `# ${page.title}\n\n${await loadPageContext(page)}`),
  );

  const prompt = [
    "你是“AI 巴菲特”，请基于以下预编译知识库页面回答。",
    "要求：",
    "1. 优先引用知识库内容，不要编造页面中没有的事实。",
    "2. 语气清晰、克制、巴菲特式，但不要装扮成真人。",
    "3. 回答尽量给出长期主义、概率、估值和能力圈视角。",
    "4. 若上下文不足，明确说明知识库尚未覆盖。",
    "",
    "知识库上下文：",
    contextBlocks.join("\n\n---\n\n"),
  ].join("\n");

  writeSseHeaders(res);

  try {
    if (aiProvider === "deepseek") {
      await streamDeepSeek({ prompt, messages, res });
    } else {
      await streamAnthropic({ prompt, messages, res });
    }

    res.write(`data: ${JSON.stringify({ done: true, sources: relevantPages.map((item) => item.title) })}\n\n`);
    res.end();
  } catch (error) {
    res.write(`data: ${JSON.stringify({ error: error.message || "生成失败" })}\n\n`);
    res.end();
  }
});

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    provider: aiProvider,
    model: aiProvider === "deepseek" ? deepseekModel : anthropicModel,
    configured: aiProvider === "deepseek" ? hasRealKey(deepseekKey) : hasRealKey(anthropicKey),
    pages: state.wikiIndex.length,
    nodes: state.graph.nodes.length,
    edges: state.graph.edges.length,
  });
});

loadData();

const port = Number(process.env.PORT || 3001);
const host = process.env.HOST || "127.0.0.1";
app.listen(port, host, () => {
  console.log(`API server listening on http://${host}:${port}`);
});
