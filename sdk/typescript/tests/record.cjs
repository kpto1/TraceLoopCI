const { test } = require('node:test');
const assert = require('node:assert/strict');
const sdk = require('../dist/index.js');

test('records auth, latency and errors without replacing application errors', async () => {
  const calls = [];
  global.fetch = async (url, options) => { calls.push({ url, options }); return { ok: true }; };
  sdk.configure({ apiUrl: 'http://test', apiKey: 'secret', projectId: 'demo' });
  await sdk.recordTrace('question', 'answer', 'model');
  assert.equal(calls[0].options.headers['X-API-Key'], 'secret');
  assert.equal(JSON.parse(calls[0].options.body).project_id, 'demo');
  assert.ok(calls[0].options.signal);
  const error = new Error('application failure');
  const descriptor = { value: async () => { throw error; } };
  sdk.traceLoop('model')({}, 'answer', descriptor);
  await assert.rejects(descriptor.value(), e => e === error);
  assert.equal(JSON.parse(calls[1].options.body).status, 'error');
});
