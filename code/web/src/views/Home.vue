<script setup>
import * as d3 from "d3";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { loadJson, categoryColor } from "../lib/wiki";

const router = useRouter();
const wikiIndex = ref([]);
const graph = ref({ nodes: [], edges: [] });
const query = ref("");
const graphEl = ref(null);

const filtered = computed(() => {
  const text = query.value.trim().toLowerCase();
  if (!text) {
    return [];
  }
  return wikiIndex.value
    .filter((item) => `${item.title} ${item.summary}`.toLowerCase().includes(text))
    .slice(0, 8);
});

const stats = computed(() => [
  { label: "股东信", icon: "✉️", count: wikiIndex.value.filter((item) => item.category === "letters").length, color: "#c2604a", to: "/category/letters" },
  { label: "核心概念", icon: "💡", count: wikiIndex.value.filter((item) => item.category === "concepts").length, color: "#3b7dd8", to: "/category/concepts" },
  { label: "投资公司", icon: "🏢", count: wikiIndex.value.filter((item) => item.category === "companies").length, color: "#47956a", to: "/category/companies" },
  { label: "访谈演讲", icon: "🎤", count: wikiIndex.value.filter((item) => item.category === "interviews").length, color: "#7e5fad", to: "/category/interviews" },
]);

function countTop(category) {
  const counts = new Map();
  const byId = new Map(graph.value.nodes.map((node) => [node.id, node]));
  for (const edge of graph.value.edges) {
    const target = byId.get(edge.target);
    const source = byId.get(edge.source);
    for (const node of [source, target]) {
      if (node?.category === category) {
        const current = counts.get(node.title) || { title: node.title, count: 0, path: node.path };
        current.count += 1;
        counts.set(node.title, current);
      }
    }
  }
  return [...counts.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, 15)
}

const topConcepts = computed(() => countTop("concepts"));
const topCompanies = computed(() => countTop("companies"));
const topPeople = computed(() =>
  countTop("people").map((item, index) => ({
    ...item,
    color: ["#3B7DD8", "#7E5FAD", "#C5961B", "#47956A"][index % 4],
  })),
);

const timelineItems = computed(() => {
  const points = wikiIndex.value
    .filter((item) => ["letters", "interviews"].includes(item.category))
    .map((item) => {
      const yearMatch = `${item.title} ${item.date}`.match(/(19|20)\d{2}/);
      const year = yearMatch ? Number(yearMatch[0]) : null;
      return year ? { ...item, year } : null;
    })
    .filter(Boolean);
  const min = 1956;
  const max = 2025;
  return points.map((item) => ({
    ...item,
    left: `${((item.year - min) / (max - min)) * 100}%`,
    color:
      item.category === "interviews"
        ? "var(--color-interview)"
        : item.title.includes("合伙")
          ? "var(--color-concept)"
          : item.title.includes("特别") || item.title.includes("感恩节")
            ? "#d98324"
            : "var(--color-company)",
  }));
});

function renderMiniGraph() {
  if (!graphEl.value || !graph.value.nodes.length) {
    return;
  }
  const width = 240;
  const height = 150;
  const svg = d3.select(graphEl.value);
  svg.selectAll("*").remove();

  const nodes = graph.value.nodes.slice(0, 24).map((item) => ({ ...item }));
  const allowed = new Set(nodes.map((item) => item.id));
  const links = graph.value.edges
    .filter((edge) => allowed.has(edge.source) && allowed.has(edge.target))
    .slice(0, 28)
    .map((item) => ({ ...item }));

  const simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance(34))
    .force("charge", d3.forceManyBody().strength(-55))
    .force("center", d3.forceCenter(width / 2, height / 2));

  const link = svg
    .append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", "rgba(255,255,255,0.36)")
    .attr("stroke-width", 1);

  const node = svg
    .append("g")
    .selectAll("circle")
    .data(nodes)
    .join("circle")
    .attr("r", 4.5)
    .attr("fill", (d) => categoryColor(d.category))
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 1.1);

  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);
    node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
  });

  setTimeout(() => simulation.stop(), 4000);
}

onMounted(async () => {
  [wikiIndex.value, graph.value] = await Promise.all([
    loadJson("/data/wiki-index.json"),
    loadJson("/data/graph.json"),
  ]);
  renderMiniGraph();
});
</script>

<template>
  <div class="page">
    <section class="hero">
      <div>
        <h1>苏墨-巴菲特知识库</h1>
        <p>把巴菲特信件、访谈、概念、公司与人物预编译成可浏览、可搜索、可推理的知识网络。</p>
        <div class="hero-actions">
          <button class="btn btn-primary" @click="router.push('/chat')">🧑‍💼 问 AI 巴菲特</button>
          <button class="btn btn-secondary" @click="router.push('/graph')">🕸️ 探索知识图谱</button>
        </div>
      </div>
      <svg ref="graphEl" class="mini-graph" viewBox="0 0 240 150" />
    </section>

    <section class="section stats-grid">
      <div
        v-for="item in stats"
        :key="item.label"
        class="stat-card"
        :style="{ '--stripe': item.color }"
        @click="router.push(item.to)"
      >
        <div class="stat-row"><span>{{ item.icon }}</span><span>{{ item.count }}</span></div>
        <div class="stat-label">{{ item.label }}</div>
      </div>
    </section>

    <section class="section">
      <div class="search-box">
        <span>🔍</span>
        <input v-model="query" placeholder="搜索标题、摘要、概念、公司或人物" />
      </div>
      <div v-if="filtered.length" class="list-stack" style="margin-top: 14px;">
        <RouterLink v-for="item in filtered" :key="item.path" :to="item.path" class="list-item">
          <div class="list-item-header">
            <strong>{{ item.title }}</strong>
            <span class="muted">{{ item.category }}</span>
          </div>
          <div class="muted">{{ item.summary }}</div>
        </RouterLink>
      </div>
    </section>

    <section class="section feature-block concepts">
      <div class="feature-head">
        <div class="feature-title">核心投资概念</div>
        <div class="feature-top">TOP 15</div>
      </div>
      <div class="top-grid">
        <RouterLink v-for="item in topConcepts" :key="item.title" class="chip" :to="item.path || '#'">
          <span>{{ item.title }}</span>
          <span class="chip-badge" style="background:#b8922a">{{ item.count }}</span>
        </RouterLink>
      </div>
    </section>

    <section class="section feature-block companies">
      <div class="feature-head">
        <div class="feature-title">重要公司</div>
        <div class="feature-top">TOP 15</div>
      </div>
      <div class="top-grid">
        <RouterLink v-for="item in topCompanies" :key="item.title" class="chip" :to="item.path || '#'">
          <span>{{ item.title }}</span>
          <span class="chip-badge" style="background:#47956a">{{ item.count }}</span>
        </RouterLink>
      </div>
    </section>

    <section class="section card">
      <h2>关键人物</h2>
      <div class="people-grid" style="margin-top: 18px;">
        <RouterLink v-for="item in topPeople" :key="item.title" :to="item.path || '#'" class="person-card">
          <div class="avatar" :style="{ background: item.color }">{{ item.title.slice(0, 1) }}</div>
          <div><strong>{{ item.title }}</strong></div>
          <div class="muted">{{ item.count }} 次引用</div>
        </RouterLink>
      </div>
    </section>

    <section class="section card timeline-card">
      <h2>时间线</h2>
      <div class="timeline-track">
        <div class="timeline-line"></div>
        <RouterLink
          v-for="item in timelineItems"
          :key="item.path"
          class="timeline-point"
          :style="{ left: item.left, background: item.color }"
          :to="item.path"
          :title="`${item.year} · ${item.title}`"
        />
      </div>
      <div class="timeline-legend">
        <span><i class="dot" style="background:var(--color-concept)"></i>合伙人信</span>
        <span><i class="dot" style="background:var(--color-company)"></i>伯克希尔股东信</span>
        <span><i class="dot" style="background:var(--color-interview)"></i>访谈</span>
        <span><i class="dot" style="background:#d98324"></i>特别信件</span>
      </div>
    </section>

    <section class="section card">
      <h2>快速导航</h2>
      <div class="quick-grid" style="margin-top: 18px;">
        <RouterLink class="quick-link" to="/category/concepts">核心概念</RouterLink>
        <RouterLink class="quick-link" to="/category/companies">投资公司</RouterLink>
        <RouterLink class="quick-link" to="/category/people">关键人物</RouterLink>
        <RouterLink class="quick-link" to="/category/interviews">访谈演讲</RouterLink>
        <RouterLink class="quick-link" to="/category/letters">股东信</RouterLink>
        <RouterLink class="quick-link" to="/graph">知识图谱</RouterLink>
      </div>
    </section>
  </div>
</template>
