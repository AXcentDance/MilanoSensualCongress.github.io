// Local preview with the production site's extensionless routes and compression.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { gzipSync } from 'node:zlib';
import { root } from './site-pages.mjs';

const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.mp4': 'video/mp4', '.xml': 'application/xml', '.txt': 'text/plain; charset=utf-8' };

export async function startServer(port = 4173) {
  const server = createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      if (pathname.split('/').some(p => p.startsWith('.') && p !== '.well-known')) {
        response.writeHead(404).end(); return;
      }
      let file = resolve(root, '.' + pathname);
      if (!file.startsWith(root + sep) && file !== root) { response.writeHead(404).end(); return; }
      if (pathname.endsWith('/')) file = resolve(file, 'index.html');
      else if (!extname(file)) {
        try { await stat(file + '.html'); file += '.html'; }
        catch {
          try { if ((await stat(file)).isDirectory()) { response.writeHead(301, { Location: pathname + '/' }).end(); return; } }
          catch { file += '.html'; }
        }
      }
      let status = 200;
      let body;
      try { body = await readFile(file); }
      catch { file = resolve(root, '404.html'); body = await readFile(file); status = 404; }
      const type = types[extname(file)] || 'application/octet-stream';
      const headers = { 'Content-Type': type, 'Cache-Control': 'max-age=600', 'Vary': 'Accept-Encoding' };
      const range = /bytes=(\d+)-(\d*)/.exec(request.headers.range || '');
      if (range && extname(file) === '.mp4') {
        const start = Number(range[1]), end = Math.min(Number(range[2] || body.length - 1), body.length - 1);
        if (start > end) { response.writeHead(416, { 'Content-Range': `bytes */${body.length}` }).end(); return; }
        headers['Content-Range'] = `bytes ${start}-${end}/${body.length}`;
        headers['Accept-Ranges'] = 'bytes';
        body = body.subarray(start, end + 1); status = 206;
      } else if (/gzip/.test(request.headers['accept-encoding'] || '') && /^(text\/|application\/(json|xml))/.test(type)) {
        body = gzipSync(body); headers['Content-Encoding'] = 'gzip';
      }
      headers['Content-Length'] = body.length;
      response.writeHead(status, headers);
      response.end(request.method === 'HEAD' ? undefined : body);
    } catch { response.writeHead(400).end(); }
  });
  await new Promise((accept, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', accept); });
  return server;
}

if (process.argv[1] === resolve(import.meta.filename)) {
  const server = await startServer(Number(process.env.PORT || 4173));
  console.log(`Preview: http://127.0.0.1:${server.address().port}`);
}
