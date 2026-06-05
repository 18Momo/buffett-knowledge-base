<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { loadJson } from "./lib/wiki";

const route = useRoute();
const items = ref([]);

const counts = computed(() => {
  const totalBy = (category) => items.value.filter((item) => item.category === category).length;
  return {
    concepts: totalBy("concepts"),
    companies: totalBy("companies"),
    people: totalBy("people"),
    interviews: totalBy("interviews"),
    letters: totalBy("letters"),
  };
});

const navGroups = computed(() => [
  {
    label: "索引",
    items: [
      { to: "/category/concepts", icon: "💡", label: "核心概念", count: counts.value.concepts },
      { to: "/category/companies", icon: "🏢", label: "投资公司", count: counts.value.companies },
      { to: "/category/people", icon: "👤", label: "关键人物", count: counts.value.people },
    ],
  },
  {
    label: "来源",
    items: [
      { to: "/category/interviews", icon: "🎤", label: "访谈与演讲", count: counts.value.interviews },
      { to: "/category/letters", icon: "✉️", label: "股东信", count: counts.value.letters },
    ],
  },
  {
    label: "工具",
    items: [{ to: "/graph", icon: "🕸️", label: "知识图谱" }],
  },
]);

onMounted(async () => {
  try {
    items.value = await loadJson("/data/wiki-index.json");
  } catch (error) {
    console.warn(error);
  }
});
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink class="sidebar-logo" to="/">📚 苏墨-巴菲特知识库</RouterLink>
      <div class="sidebar-divider"></div>
      <RouterLink class="sidebar-home" to="/">🏠 知识库首页</RouterLink>

      <div v-for="group in navGroups" :key="group.label" class="sidebar-group">
        <div class="nav-label">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.path === item.to }"
        >
          <span>{{ item.icon }} {{ item.label }}</span>
          <span v-if="typeof item.count === 'number'" class="count-pill">{{ item.count }}</span>
        </RouterLink>
      </div>

      <div class="sidebar-divider bottom"></div>
      <RouterLink class="chat-cta" to="/chat">
        <span>🧑‍💼 AI 巴菲特</span>
        <span class="new-pill">NEW</span>
      </RouterLink>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>
