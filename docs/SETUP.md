# 本地启动说明

## 1. 初始化知识库

```bash
cd /Users/sumo/Documents/4.Codex/buffett
python3 code/init_project.py
python3 code/make_ingest_batches.py
```

## 2. Codex 批量精修访谈和信件

```bash
python3 code/codex_refine_summaries.py --file raw/letters/berkshire/2013\ 巴菲特致股东信.md --force
python3 code/codex_refine_summaries.py --letters --force
python3 code/codex_refine_summaries.py --interviews --force
python3 code/codex_refine_summaries.py --all --force
```

精修完成后刷新索引和前端数据：

```bash
python3 code/update_index.py
python3 code/web/scripts/build-data.py
python3 code/audit_data.py
```

## 3. 启动 Web

```bash
cd /Users/sumo/Documents/4.Codex/buffett/code/web
cp .env.example .env
python3 scripts/build-data.py
npm install
node --env-file=.env server.js
npx vite --host 127.0.0.1
```

## 4. 环境变量

- `ACCESS_PASSWORD`
- `AI_PROVIDER`
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
