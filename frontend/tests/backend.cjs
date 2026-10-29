const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const ts = require('typescript');

const source = fs.readFileSync('src/app/api/backend/[...path]/route.ts', 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const loaded = new Module('backend-route');
loaded._compile(compiled, 'backend-route.js');
const route = loaded.exports;
const request = (method = 'GET', origin = 'http://localhost:3000') => ({
  method, headers: new Headers({ origin }), nextUrl: new URL('http://localhost:3000/api/backend/v1/traces'),
  text: async () => JSON.stringify({ input_text: 'test' }),
});

test('server-side proxy authenticates upstream and rejects invalid routes/origins', async () => {
  process.env.TRACELOOP_API_KEY = 'server-only-test-key';
  process.env.TRACELOOP_API_URL = 'http://api:8000';
  let upstream;
  global.fetch = async (url, options) => {
    upstream = { url, options };
    return Response.json({ items: [] });
  };
  const response = await route.GET(request(), { params: Promise.resolve({ path: ['v1', 'traces'] }) });
  assert.equal(response.status, 200);
  assert.equal(upstream.url, 'http://api:8000/v1/traces');
  assert.equal(upstream.options.headers['X-API-Key'], 'server-only-test-key');
  assert.equal((await response.text()).includes('server-only-test-key'), false);
  assert.equal((await route.GET(request(), { params: Promise.resolve({ path: ['v1', '..', 'health'] }) })).status, 404);
  assert.equal((await route.POST(request('POST', 'https://other.example'), { params: Promise.resolve({ path: ['v1', 'datasets'] }) })).status, 403);
  global.fetch = async () => { throw new Error('connection failed'); };
  assert.equal((await route.GET(request(), { params: Promise.resolve({ path: ['v1', 'traces'] }) })).status, 502);
});
