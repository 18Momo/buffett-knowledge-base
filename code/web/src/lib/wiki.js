export async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

export async function loadText(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.text();
}

export function parseFrontmatter(text = "") {
  if (!text.startsWith("---")) {
    return { meta: {}, body: text };
  }
  const parts = text.split("---", 3);
  if (parts.length < 3) {
    return { meta: {}, body: text };
  }
  const meta = {};
  for (const line of parts[1].split("\n")) {
    const idx = line.indexOf(":");
    if (idx === -1) {
      continue;
    }
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim();
    if (value.startsWith("[") && value.endsWith("]")) {
      meta[key] = value
        .slice(1, -1)
        .split(",")
        .map((item) => item.trim().replace(/^"|"$/g, ""))
        .filter(Boolean);
    } else {
      meta[key] = value.replace(/^"|"$/g, "");
    }
  }
  return { meta, body: parts[2].replace(/^\n+/, "") };
}

export function convertWikiLinks(markdown = "", items = []) {
  const byTitle = new Map(items.map((item) => [item.title, item]));
  return markdown.replace(/\[\[([^\]]+)\]\]/g, (_, title) => {
    const target = byTitle.get(title);
    if (!target) {
      return title;
    }
    return `[${title}](${target.path})`;
  });
}

export function inferRawPath(source = "") {
  if (!source) {
    return "";
  }
  const normalized = source.replace(/^raw\//, "");
  return `/data/raw/${normalized}`;
}

export function typeLabel(category) {
  return {
    concepts: "核心概念",
    companies: "投资公司",
    people: "关键人物",
    interviews: "访谈与演讲",
    letters: "股东信",
    insights: "交叉洞察",
  }[category] || category;
}

export function categoryColor(category) {
  return {
    concepts: "var(--color-concept)",
    companies: "var(--color-company)",
    people: "var(--color-person)",
    interviews: "var(--color-interview)",
    letters: "var(--color-letter)",
    unknown: "#8E8E93",
  }[category] || "#8E8E93";
}
