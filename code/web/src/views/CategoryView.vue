<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { loadJson, typeLabel } from "../lib/wiki";

const route = useRoute();
const allPages = ref([]);
const query = ref("");
const sortMode = ref("degree");

const categoryItems = computed(() => allPages.value.filter((item) => item.category === route.params.type));

const stats = computed(() => {
  const items = categoryItems.value;
  return {
    total: items.length,
    linked: items.filter((item) => (item.degree || 0) > 0).length,
    avgDegree: items.length
      ? Math.round(items.reduce((sum, item) => sum + (item.degree || 0), 0) / items.length)
      : 0,
  };
});

const items = computed(() => {
  const text = query.value.trim().toLowerCase();
  const filtered = categoryItems.value.filter((item) => {
    const haystack = `${item.title} ${item.summary} ${(item.links || []).join(" ")} ${(item.tags || []).join(" ")}`.toLowerCase();
    return !text || haystack.includes(text);
  });
  return [...filtered].sort((a, b) => {
    if (sortMode.value === "date") {
      return String(b.date || "").localeCompare(String(a.date || ""));
    }
    if (sortMode.value === "title") {
      return String(a.title || "").localeCompare(String(b.title || ""), "zh-Hans-CN");
    }
    return (b.degree || 0) - (a.degree || 0) || String(a.title || "").localeCompare(String(b.title || ""), "zh-Hans-CN");
  });
});

async function loadPages() {
  allPages.value = await loadJson("/data/wiki-index.json");
}

watch(() => route.params.type, loadPages);
onMounted(loadPages);
</script>

<template>
  <div class="page">
    <div class="breadcrumbs">
      <RouterLink to="/">首页</RouterLink><span>/</span>
      <strong>{{ typeLabel(route.params.type) }}</strong>
    </div>

    <section class="card">
      <div class="category-head">
        <div>
          <h1 class="section-title">{{ typeLabel(route.params.type) }}</h1>
          <div class="muted">{{ stats.total }} 个页面 · {{ stats.linked }} 个已入图谱 · 平均关联 {{ stats.avgDegree }}</div>
        </div>
        <div class="segmented">
          <button :class="{ active: sortMode === 'degree' }" @click="sortMode = 'degree'">关联</button>
          <button :class="{ active: sortMode === 'date' }" @click="sortMode = 'date'">时间</button>
          <button :class="{ active: sortMode === 'title' }" @click="sortMode = 'title'">标题</button>
        </div>
      </div>
      <div class="search-box category-search">
        <span>🔍</span>
        <input v-model="query" placeholder="按标题、摘要和关联实体过滤" />
      </div>
    </section>

    <section class="section list-stack">
      <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="list-item">
        <div class="list-item-header">
          <strong>{{ item.title }}</strong>
          <span class="muted">{{ item.date }}</span>
        </div>
        <div class="muted">{{ item.summary }}</div>
        <div class="item-meta">
          <span>关联 {{ item.degree || 0 }}</span>
          <span>引用 {{ item.inboundCount || 0 }}</span>
          <span>链接 {{ item.outboundCount || 0 }}</span>
        </div>
      </RouterLink>
      <div v-if="!items.length" class="card muted">当前分类还没有可展示页面。</div>
    </section>
  </div>
</template>
