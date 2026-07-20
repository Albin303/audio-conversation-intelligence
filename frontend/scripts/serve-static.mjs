import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, resolve } from 'node:path';

const root = resolve(process.cwd(), 'out');
const portFlagIndex = process.argv.findIndex((arg) => arg === '-p' || arg === '--port');
const portArg = portFlagIndex >= 0 ? process.argv[portFlagIndex + 1] : undefined;
const port = Number.parseInt(process.env.PORT || portArg || '3000', 10);

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
};

function resolveRequestPath(url) {
  const pathname = decodeURIComponent(new URL(url, 'http://localhost').pathname);
  const cleanPath = normalize(pathname).replace(/^(\.\.[/\\])+/, '');
  let filePath = resolve(root, `.${cleanPath}`);

  if (!filePath.startsWith(root)) {
    return null;
  }

  if (existsSync(filePath) && statSync(filePath).isDirectory()) {
    filePath = join(filePath, 'index.html');
  }

  if (!existsSync(filePath)) {
    filePath = join(root, 'index.html');
  }

  return filePath;
}

if (!existsSync(root)) {
  console.error('Static export directory not found. Run npm run build first.');
  process.exit(1);
}

createServer((request, response) => {
  const filePath = resolveRequestPath(request.url || '/');
  if (!filePath || !existsSync(filePath)) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not found');
    return;
  }

  response.writeHead(200, {
    'Content-Type': contentTypes[extname(filePath)] || 'application/octet-stream',
  });
  createReadStream(filePath).pipe(response);
}).listen(port, () => {
  console.log(`Serving ${root} at http://localhost:${port}`);
});
