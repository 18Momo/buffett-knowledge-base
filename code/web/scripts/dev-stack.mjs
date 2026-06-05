import net from "node:net";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const nodeBin = process.execPath;

const services = [
  {
    name: "api",
    label: "后端",
    port: 3001,
    command: nodeBin,
    args: ["--env-file=.env", "server.js"],
  },
  {
    name: "web",
    label: "前端",
    port: 5173,
    command: nodeBin,
    args: [join(root, "node_modules/vite/bin/vite.js"), "--host", "127.0.0.1"],
  },
];

const children = new Map();
let shuttingDown = false;

function log(name, message) {
  process.stdout.write(`[${name}] ${message}`);
}

function isPortOpen(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: "127.0.0.1", port });
    socket.setTimeout(500);
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.once("error", () => resolve(false));
  });
}

async function startService(service) {
  if (await isPortOpen(service.port)) {
    console.log(`[${service.name}] ${service.label}已在 127.0.0.1:${service.port} 运行，跳过重复启动。`);
    return;
  }

  const child = spawn(service.command, service.args, {
    cwd: root,
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  children.set(service.name, child);
  console.log(`[${service.name}] 启动${service.label}：127.0.0.1:${service.port}`);

  child.stdout.on("data", (chunk) => log(service.name, chunk.toString()));
  child.stderr.on("data", (chunk) => log(service.name, chunk.toString()));
  child.on("exit", (code, signal) => {
    children.delete(service.name);
    if (shuttingDown) {
      return;
    }
    console.log(`[${service.name}] 已退出 code=${code ?? "null"} signal=${signal ?? "null"}，2 秒后自动重启。`);
    setTimeout(() => startService(service), 2000);
  });
}

function stopAll() {
  shuttingDown = true;
  for (const child of children.values()) {
    child.kill("SIGTERM");
  }
}

process.on("SIGINT", () => {
  stopAll();
  process.exit(0);
});
process.on("SIGTERM", () => {
  stopAll();
  process.exit(0);
});

console.log("苏墨-巴菲特知识库开发服务守护中。前端：http://127.0.0.1:5173，后端：http://127.0.0.1:3001");
await Promise.all(services.map(startService));
