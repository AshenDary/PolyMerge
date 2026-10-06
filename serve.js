/**
 * Minimal static file server for frontend-only development.
 * Serves everything from the repo root so /frontend/app.js etc. resolve.
 * API calls will return 404 — the UI handles that as "graph unavailable".
 */
import http from 'node:http';
import fs   from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = 3000;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css',
  '.js':   'text/javascript',
  '.json': 'application/json',
  '.png':  'image/png',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
};

const server = http.createServer((req, res) => {
  // Serve index.html for root
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/frontend/index.html';

  const filePath = path.join(ROOT, urlPath);

  // Only allow files inside the repo root (basic path traversal guard)
  if (!filePath.startsWith(ROOT + path.sep) && filePath !== ROOT) {
    res.writeHead(403); res.end('Forbidden'); return;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      // Return a minimal JSON 503 for API paths so the UI shows its error state
      if (urlPath.startsWith('/api/')) {
        res.writeHead(503, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Backend not running — frontend-only mode' }));
      } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not found: ' + urlPath);
      }
      return;
    }
    const ext  = path.extname(filePath);
    const mime = MIME[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime });
    res.end(data);
  });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`\nPolyMerge frontend running at: http://localhost:${PORT}\n`);
  console.log('(API calls will return 503 — the dashboard will show the "graph unavailable" state)');
});
