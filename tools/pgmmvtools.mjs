#!/usr/bin/env node
// pgmmvtools -- export a native PGMMV game as a static website for the generic WASM runtime.
//   pgmmvtools web <GameDir> <OutDir> [--runtime <dir>] [--title <t>] [--no-decrypt] [--python <py>]
//   pgmmvtools serve <Dir> [port]
// Needs Node 22+. The original game folder is never modified.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import http from 'node:http';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SKIP = /(\.bak|\.tmp)$|before-decrypt|decrypted-candidate/;

function usage(code = 0) {
  console.log(`pgmmvtools web <GameDir> <OutDir> [--game-dir <dir>] [--game-url <url>] [--runtime <dir>] [--title <text>] [--no-decrypt] [--python <py>]
pgmmvtools serve <Dir> [port] [--map /game/=<dir>]...

web     copy the game into <OutDir>/game (or --game-dir), decrypt it, write manifest.json, add the runtime and shell page.
          --game-dir <dir>   write the game files to another folder (e.g. external storage) instead of <OutDir>/game
          --game-url <url>   default game location baked into index.html (relative or absolute; default "game/")
serve   static server with COOP/COEP + CORS headers. --map /game/=<dir> serves a URL prefix from another folder.`);
  process.exit(code);
}
function die(m) { console.error('error: ' + m); process.exit(1); }

function parse(argv) {
  const pos = [], opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--no-decrypt') opt.noDecrypt = true;
    else if (a === '--map') (opt.map ||= []).push(argv[++i]);
    else if (['--runtime', '--title', '--python', '--game-dir', '--game-url'].includes(a)) opt[a.slice(2)] = argv[++i];
    else if (a.startsWith('--')) die('unknown option ' + a);
    else pos.push(a);
  }
  return { pos, opt };
}

// The Resources dir is the one that contains data/project.json (search up to 2 levels deep).
function findResources(dir, depth = 2) {
  if (fs.existsSync(path.join(dir, 'data', 'project.json'))) return dir;
  if (depth === 0) return null;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      const r = findResources(path.join(dir, e.name), depth - 1);
      if (r) return r;
    }
  }
  return null;
}

function walk(dir, base = dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, base, out);
    else if (e.isFile() && !SKIP.test(e.name)) out.push(path.relative(base, p).split(path.sep).join('/'));
  }
  return out.sort();
}

function web(pos, opt) {
  if (pos.length < 2) usage(1);
  const [gameArg, outArg] = pos;
  const src = findResources(path.resolve(gameArg));
  if (!src) die(`no data/project.json under ${gameArg} (expected a PGMMV output folder)`);
  const out = path.resolve(outArg);
  const gameOut = opt['game-dir'] ? path.resolve(opt['game-dir']) : path.join(out, 'game');
  const gameUrl = opt['game-url'] || (opt['game-dir'] ? '' : 'game/');
  if (!gameUrl) die('with --game-dir you must also pass --game-url (where the browser will find that folder, e.g. ../games/rabbit/ or https://host/rabbit/)');
  if (fs.existsSync(gameOut) && fs.readdirSync(gameOut).length && !fs.existsSync(path.join(gameOut, 'manifest.json')))
    die(`${gameOut} is not empty and is not a previous export; refusing to overwrite it`);
  const runtime = path.resolve(opt.runtime || path.join(REPO, 'build', 'runtime'));
  if (!fs.existsSync(path.join(runtime, 'pgmmv.js')) || !fs.existsSync(path.join(runtime, 'pgmmv.wasm')))
    die(`runtime not found in ${runtime} (need pgmmv.js + pgmmv.wasm; build the pgmmv target or pass --runtime)`);

  console.log('resources: ' + src);
  fs.rmSync(gameOut, { recursive: true, force: true });
  fs.mkdirSync(gameOut, { recursive: true });
  fs.cpSync(src, gameOut, { recursive: true, filter: (s) => !SKIP.test(path.basename(s)) });

  if (!opt.noDecrypt) {
    const r = spawnSync(opt.python || 'python3', [path.join(HERE, 'decrypt_game.py'), gameOut], { stdio: 'inherit' });
    if (r.status !== 0) die(`decrypt step failed (exit ${r.status}); use --no-decrypt if the game is already clear`);
  }

  const files = walk(gameOut).map((p) => {
    const buf = fs.readFileSync(path.join(gameOut, p));
    return { p, s: buf.length, h: crypto.createHash('sha1').update(buf).digest('hex').slice(0, 8) };
  });
  const total = files.reduce((a, f) => a + f.s, 0);
  const version = crypto.createHash('sha1').update(files.map((f) => f.p + f.h).join('|')).digest('hex').slice(0, 10);
  fs.writeFileSync(path.join(gameOut, 'manifest.json'),
    JSON.stringify({ format: 1, root: '/app/Resources', version, total, files }));

  fs.cpSync(runtime, path.join(out, 'runtime'), { recursive: true, filter: (s) => !/\.(html|data|map)$/.test(s) });
  const webDir = path.join(REPO, 'web');
  const title = (opt.title || path.basename(path.dirname(src) === path.resolve(gameArg) ? src : path.resolve(gameArg))).replace(/[<&>"]/g, '');
  fs.writeFileSync(path.join(out, 'index.html'), fs.readFileSync(path.join(webDir, 'index.html'), 'utf8').replaceAll('{{TITLE}}', title).replaceAll('{{GAME_URL}}', gameUrl.replace(/[\\'<]/g, '')));
  fs.copyFileSync(path.join(webDir, 'coi-sw.js'), path.join(out, 'coi-sw.js'));
  for (const extra of ['virtual_keyboard.js']) {
    const p = [path.join(webDir, extra), path.join(REPO, 'build', 'web', extra)].find((x) => fs.existsSync(x));
    if (p) fs.copyFileSync(p, path.join(out, extra));
  }
  console.log(`done: ${files.length} files, ${(total / 1048576).toFixed(1)} MB -> ${out}`);
  if (total > 300 * 1048576) console.warn('warning: > 300 MB is loaded into memory at startup in this version (see lazy loading)');
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
  '.ogg': 'audio/ogg', '.mp3': 'audio/mpeg', '.mp4': 'video/mp4', '.webm': 'video/webm', '.ttf': 'font/ttf', '.css': 'text/css' };

function serve(pos, opt) {
  const dir = path.resolve(pos[0] || '.');
  const maps = (opt.map || []).map((m) => { const [u, d] = m.split('='); return [u.endsWith('/') ? u : u + '/', path.resolve(d)]; });
  const port = Number(pos[1] || 8000);
  http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (p.endsWith('/')) p += 'index.html';
    let root = dir, rel = p;
    for (const [u, d] of maps) if (p.startsWith(u)) { root = d; rel = p.slice(u.length); break; }
    const f = path.join(root, path.normalize('/' + rel));
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
    res.setHeader('Cross-Origin-Resource-Policy', 'cross-origin');
    if (!f.startsWith(root + path.sep) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { res.statusCode = 404; return res.end('404'); }
    res.setHeader('Content-Type', MIME[path.extname(f).toLowerCase()] || 'application/octet-stream');
    fs.createReadStream(f).pipe(res);
  }).listen(port, '127.0.0.1', () => console.log(`serving ${dir} at http://127.0.0.1:${port}/`));
}

const [cmd, ...rest] = process.argv.slice(2);
const { pos, opt } = parse(rest);
if (cmd === 'web') web(pos, opt);
else if (cmd === 'serve') serve(pos, opt);
else usage(cmd === 'help' || cmd === undefined ? 0 : 1);
