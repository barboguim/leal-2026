import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(__dirname, '../../app/data.js');
const destDir = path.resolve(__dirname, '../public');
const dest = path.join(destDir, 'data.js');

if (!existsSync(src)) {
  console.error(`Missing ${src} — run scripts/06_build_vote_deltas.py and scripts/07_top_competitors.py from the repo root first.`);
  process.exit(1);
}
if (!existsSync(destDir)) mkdirSync(destDir, { recursive: true });
const raw = readFileSync(src, 'utf-8');
const content = raw.replace('const DATA', 'window.DATA');
if (content === raw) {
  throw new Error('sync-data: "const DATA" not found in app/data.js — pipeline output format changed, update the sync transform');
}
writeFileSync(dest, content);
console.log(`Synced data.js -> ${dest}`);
