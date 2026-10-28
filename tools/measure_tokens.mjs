// tools/measure_tokens.mjs — 统计某个 DSH 会话的 token 用量
// 用法：ego-browser nodejs tools/measure_tokens.mjs <会话目录>
// 说明：会话文件是 session.v4.jsonl.zstd；用 Node 24 内置 zstdDecompressSync 解压。
// 注意：usage.totalTokens 是**累计值**，不能求和；只累加 inputTokens / outputTokens。
import fs from "node:fs";
import zlib from "node:zlib";
import path from "node:path";

const dir = process.argv[2] || process.env.SESSION_DIR;
if (!dir) {
  console.error("用法: ego-browser nodejs tools/measure_tokens.mjs <会话目录>");
  process.exit(2);
}

const files = fs.readdirSync(dir).filter((f) => f.endsWith(".zstd"));
if (!files.length) {
  console.error("目录里没有 .zstd 会话文件:", dir);
  process.exit(3);
}

let text = "";
for (const f of files) {
  const buf = zlib.zstdDecompressSync(fs.readFileSync(path.join(dir, f)));
  text += buf.toString("utf8");
}

const lines = text.split("\n").filter(Boolean);
let calls = 0, inSum = 0, outSum = 0, lastTotal = 0, lastCache = 0;
let t0 = null, t1 = null;
const turns = new Set();
const tools = new Map();

for (const ln of lines) {
  let o;
  try { o = JSON.parse(ln); } catch { continue; }
  if (t0 === null && o.time) t0 = o.time;
  if (o.time) t1 = o.time;
  if (o.type === "assistant/message") {
    const u = o?.data?.usage;
    if (u) {
      calls++;
      inSum += u.inputTokens || 0;
      outSum += u.outputTokens || 0;
      lastTotal = Math.max(lastTotal, u.totalTokens || 0);
      lastCache = Math.max(lastCache, u.cacheReadTokens || 0);
    }
    if (o?.data?.turn != null) turns.add(o.data.turn);
  }
  // 粗略统计工具调用次数
  if (o.type === "tool/call" || (o.type && String(o.type).includes("tool") && o?.data?.name)) {
    const n = o?.data?.name || "unknown";
    tools.set(n, (tools.get(n) || 0) + 1);
  }
}

const minutes = t0 && t1 ? (t1 - t0) / 60000 : 0;
const topTools = [...tools.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);

console.log(JSON.stringify({
  session: path.basename(dir),
  records: lines.length,
  billingCalls: calls,
  turns: turns.size,
  inputTokens: inSum,
  outputTokens: outSum,
  totalIO: inSum + outSum,
  lastCumulativeTotal: lastTotal,
  peakCacheRead: lastCache,
  minutes: Math.round(minutes * 10) / 10,
  toolCalls: [...tools.values()].reduce((a, b) => a + b, 0),
  topTools,
}, null, 1));
