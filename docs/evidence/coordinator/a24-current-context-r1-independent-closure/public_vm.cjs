'use strict';
// Host only loads vm; product program receives no require/process/browser/network.
const vm = require('node:vm');
let data = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { data += chunk; });
process.stdin.on('end', async () => {
  const input = JSON.parse(data), rows = [];
  for (const mode of ['OK200', 'HTTP403', 'FETCH_THROW']) {
    let sends = 0, storage = 0, safeOptions = false;
    const context = vm.createContext({
      localStorage: { getItem() { storage++; throw Error('NO_REAL_OR_FAKE_ACCOUNT_READ'); } },
      AbortController: class { constructor() { this.signal = {}; } abort() {} },
      setTimeout: () => 1, clearTimeout: () => {},
      fetch: async (url, options) => {
        sends++;
        safeOptions = url === input.url && options.method === 'GET' &&
          options.credentials === 'omit' && options.redirect === 'error' &&
          (!options.headers || !Object.keys(options.headers).some(key => key.toLowerCase() === 'authorization'));
        if (mode === 'FETCH_THROW') throw Error('INDEPENDENT_PRIVATE_THROW_SENTINEL');
        return { status: mode === 'HTTP403' ? 403 : 200, json: async () => [] };
      }
    });
    const program = vm.runInContext('(' + input.program + ')', context);
    const result = await program(input.url);
    const text = JSON.stringify(result);
    const status = mode === 'OK200' ? 200 : mode === 'HTTP403' ? 403 : 0;
    const success = sends === 1 && storage === 0 && safeOptions && result.http_status === status &&
      !text.includes('INDEPENDENT_PRIVATE_THROW_SENTINEL');
    rows.push({ mode, success, sends, storageReads: storage, safeOptions, returnedHttpStatus: result.http_status });
    if (!success) break;
  }
  process.stdout.write(JSON.stringify({ results: rows }) + '\n');
  if (rows.length !== 3 || !rows.every(row => row.success)) process.exitCode = 1;
});
