# Wiki Schema

所有页面必须使用 Markdown，并包含如下 YAML frontmatter：

```yaml
---
title: "页面标题"
type: letter-summary | interview-summary | concept | company | person | insight | index
date: YYYY-MM-DD
source: "原始文件路径"
tags: [标签1, 标签2]
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## 规则

1. 必须使用 `[[双向链接]]` 关联实体
2. 每个实体必须有独立页面
3. 页面类型仅允许：`letter-summary`、`interview-summary`、`concept`、`company`、`person`、`insight`、`index`
4. 摘要页结构固定为：

```md
# 标题

## 核心要点

## 详细摘要

## 提到的概念

## 提到的公司

## 提到的人物

## 原文金句
```
