<script setup>
import * as d3 from "d3";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { categoryColor, loadJson, typeLabel } from "../lib/wiki";

const router = useRouter();
const graph = ref({ nodes: [], edges: [] });
const svgEl = ref(null);
const stageEl = ref(null);
const activeNode = ref(null);

let simulation = null;
let resizeObserver = null;

const legend = [
  { category: "concepts", label: "概念" },
  { category: "companies", label: "公司" },
  { category: "people", label: "人物" },
  { category: "interviews", label: "访谈" },
  { category: "letters", label: "股东信" },
];

const stats = computed(() => ({
  nodes: graph.value.nodes.length,
  edges: graph.value.edges.length,
}));

function nodeRadius(node) {
  return node.category === "unknown" ? 3 : 6;
}

function renderGraph() {
  if (!svgEl.value || !stageEl.value || !graph.value.nodes.length) {
    return;
  }

  simulation?.stop();

  const stageRect = stageEl.value.getBoundingClientRect();
  const width = Math.max(stageRect.width, 720);
  const height = Math.max(stageRect.height, 520);
  const nodes = graph.value.nodes.map((node) => ({ ...node }));
  const links = graph.value.edges.map((edge) => ({ ...edge }));
  const svg = d3.select(svgEl.value);

  svg.selectAll("*").remove();
  svg.attr("viewBox", `0 0 ${width} ${height}`);

  const zoomLayer = svg.append("g").attr("class", "graph-zoom-layer");
  const linkLayer = zoomLayer.append("g").attr("class", "graph-link-layer");
  const nodeLayer = zoomLayer.append("g").attr("class", "graph-node-layer");

  const zoom = d3
    .zoom()
    .scaleExtent([0.2, 5])
    .on("zoom", (event) => {
      zoomLayer.attr("transform", event.transform);
    });

  svg.call(zoom);

  const link = linkLayer
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("class", "graph-link");

  const node = nodeLayer
    .selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", "graph-node")
    .style("cursor", (item) => (item.path ? "pointer" : "default"))
    .on("mouseenter", (_, item) => {
      activeNode.value = item;
    })
    .on("mouseleave", () => {
      activeNode.value = null;
    })
    .on("click", (_, item) => {
      if (item.path) {
        router.push(item.path);
      }
    })
    .call(
      d3
        .drag()
        .on("start", (event, item) => {
          if (!event.active) {
            simulation.alphaTarget(0.25).restart();
          }
          item.fx = item.x;
          item.fy = item.y;
        })
        .on("drag", (event, item) => {
          item.fx = event.x;
          item.fy = event.y;
        })
        .on("end", (event, item) => {
          if (!event.active) {
            simulation.alphaTarget(0);
          }
          item.fx = null;
          item.fy = null;
        }),
    );

  node
    .append("circle")
    .attr("r", nodeRadius)
    .attr("fill", (item) => categoryColor(item.category))
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5);

  node.append("title").text((item) => `${item.title} · ${typeLabel(item.category)}`);

  node
    .filter((item) => item.category !== "unknown")
    .append("text")
    .attr("class", "graph-label")
    .attr("x", 9)
    .attr("dy", "0.32em")
    .text((item) => item.title);

  simulation = d3
    .forceSimulation(nodes)
    .force(
      "link",
      d3
        .forceLink(links)
        .id((item) => item.id)
        .distance((item) => (item.source.category === "letters" || item.target.category === "letters" ? 92 : 74))
        .strength(0.18),
    )
    .force("charge", d3.forceManyBody().strength(-86))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide((item) => nodeRadius(item) + 8))
    .on("tick", () => {
      link
        .attr("x1", (item) => item.source.x)
        .attr("y1", (item) => item.source.y)
        .attr("x2", (item) => item.target.x)
        .attr("y2", (item) => item.target.y);

      node.attr("transform", (item) => `translate(${item.x},${item.y})`);
    });
}

onMounted(async () => {
  graph.value = await loadJson("/data/graph.json");
  await nextTick();
  renderGraph();

  resizeObserver = new ResizeObserver(() => {
    renderGraph();
  });
  resizeObserver.observe(stageEl.value);
});

onBeforeUnmount(() => {
  simulation?.stop();
  resizeObserver?.disconnect();
});
</script>

<template>
  <div class="page graph-page">
    <section class="graph-hero">
      <div>
        <h1>知识图谱</h1>
        <p>{{ stats.nodes }} 个节点 · {{ stats.edges }} 条连接 · 支持缩放、拖拽节点、点击跳转详情页</p>
      </div>
      <div class="graph-legend">
        <span v-for="item in legend" :key="item.category">
          <i :style="{ background: categoryColor(item.category) }"></i>
          {{ item.label }}
        </span>
      </div>
    </section>

    <section class="card graph-card">
      <div class="graph-card-head">
        <div>
          <h2>巴菲特投资思想网络</h2>
          <p v-if="activeNode">{{ activeNode.title }} · {{ typeLabel(activeNode.category) }}</p>
          <p v-else>滚轮缩放画布，拖拽节点观察连接关系。</p>
        </div>
      </div>
      <div ref="stageEl" class="graph-stage">
        <svg ref="svgEl" class="graph-svg" role="img" aria-label="巴菲特知识库关系图谱"></svg>
      </div>
    </section>
  </div>
</template>
