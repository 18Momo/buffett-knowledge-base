<script setup>
import MarkdownIt from "markdown-it";
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { convertWikiLinks, inferRawPath, loadJson, loadText, parseFrontmatter, typeLabel, categoryColor } from "../lib/wiki";

const route = useRoute();
const md = new MarkdownIt({ html: true, linkify: true, breaks: true });
const allPages = ref([]);
const page = ref(null);
const rendered = ref("");
const rawText = ref("");
const renderedRaw = ref("");
const badgeStyle = computed(() => ({
  background: categoryColor(route.params.category),
}));

function isTableSeparator(line) {
  const cells = line.trim().split(/\s+/);
  return cells.length >= 2 && cells.every((cell) => /^:?-{2,}:?$/.test(cell));
}

function splitTableRow(line, expectedColumns) {
  let cells = line.trim().split(/\s{2,}|\t+/).filter(Boolean);
  if (cells.length === expectedColumns) {
    return cells;
  }
  cells = line.trim().split(/\s+/).filter(Boolean);
  if (cells.length === expectedColumns) {
    return cells;
  }
  if (expectedColumns === 4) {
    const rowMatch = line.trim().match(/^(\S+)\s+(.+?)\s+(.+?)\s+(.+?)$/);
    if (rowMatch) {
      return rowMatch.slice(1);
    }
  }
  return null;
}

function normalizeRawMarkdown(text) {
  const filtered = text
    .split("\n")
    .filter((line) => !line.startsWith("> **Source**") && !line.startsWith("> **Type**") && line.trim() !== "---")
    .map((line) => line.replace(/<p align="center">\s*<\/p>/g, ""))
    .join("\n")
    .trim();

  const lines = filtered.split("\n");
  const output = [];
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const next = lines[index + 1] || "";
    if (isTableSeparator(next)) {
      const separatorCells = next.trim().split(/\s+/);
      const headerCells = splitTableRow(line, separatorCells.length) || line.trim().split(/\s+/);
      output.push(`| ${headerCells.join(" | ")} |`);
      output.push(`| ${separatorCells.map((cell) => (cell.includes(":") ? cell : "---")).join(" | ")} |`);
      index += 1;
      while (index + 1 < lines.length) {
        const row = lines[index + 1];
        if (!row.trim()) {
          break;
        }
        if (row.startsWith("#") || row.startsWith(">")) {
          break;
        }
        const rowCells = splitTableRow(row, headerCells.length);
        if (!rowCells) {
          break;
        }
        output.push(`| ${rowCells.join(" | ")} |`);
        index += 1;
      }
      output.push("");
      continue;
    }
    output.push(line);
  }

  return output.join("\n").replace(/\n{3,}/g, "\n\n");
}

async function loadPage() {
  allPages.value = await loadJson("/data/wiki-index.json");
  const text = await loadText(`/data/pages/${route.params.category}/${route.params.slug}.md`);
  const { meta, body } = parseFrontmatter(text);
  page.value = meta;
  rendered.value = md.render(convertWikiLinks(body, allPages.value));

  if (["letters", "interviews"].includes(route.params.category) && meta.source) {
    try {
      rawText.value = await loadText(inferRawPath(meta.source));
      renderedRaw.value = md.render(normalizeRawMarkdown(rawText.value));
    } catch (error) {
      rawText.value = "";
      renderedRaw.value = "";
    }
  } else {
    rawText.value = "";
    renderedRaw.value = "";
  }
}

watch(() => route.fullPath, loadPage);
onMounted(loadPage);
</script>

<template>
  <div v-if="page" class="page">
    <div class="breadcrumbs">
      <RouterLink to="/">首页</RouterLink><span>/</span>
      <RouterLink :to="`/category/${route.params.category}`">{{ typeLabel(route.params.category) }}</RouterLink><span>/</span>
      <strong>{{ page.title }}</strong>
    </div>

    <section class="page-header">
      <div class="type-badge" :style="badgeStyle">{{ typeLabel(route.params.category) }}</div>
      <h1>{{ page.title }}</h1>
      <p>{{ page.date }}</p>
    </section>

    <article class="page-body" v-html="rendered"></article>

    <details v-if="rawText" class="raw-toggle">
      <summary>▶ 📄 原文全文 — 展开阅读完整原文</summary>
      <article class="raw-content markdown-content" v-html="renderedRaw"></article>
    </details>
  </div>
</template>
