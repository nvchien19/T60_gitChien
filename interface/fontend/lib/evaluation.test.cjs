const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const ts = require('typescript')
const output = ts.transpileModule(readFileSync(__dirname + '/api.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const target = { exports: {} }
new Function('exports', 'module', output)(target.exports, target)
const { loadEvaluation, ApiError } = target.exports
const latest = JSON.parse(readFileSync(__dirname + '/../../../eval/results/metrics_latest.json', 'utf8'))
const respond = (status, body) => new Response(JSON.stringify(body), { status })

async function main() {
  const calls = []
  global.fetch = async path => {
    calls.push(path)
    return path.endsWith('/all') ? respond(404, { detail: 'Missing summary' }) : respond(200, latest)
  }
  const data = await loadEvaluation()
  assert.deepEqual(calls, ['/api/v1/eval/metrics/all', '/api/v1/eval/metrics'])
  assert.equal(data.latestOnly, true)
  assert.equal(data.generated, latest.run)
  assert.equal(data.n_cases, latest.n_cases)
  assert.deepEqual(data.confusion, latest.confusion)
  assert.equal(data.metrics.find(m => m.key === 'recall').pooled, latest.metrics.find(m => m.key === 'recall').value)
  for (const status of [401, 403, 500]) {
    let count = 0
    global.fetch = async () => { count++; return respond(status, { detail: 'Failure' }) }
    await assert.rejects(loadEvaluation(), e => e instanceof ApiError && e.status === status)
    assert.equal(count, 1, 'Only missing summary triggers fallback')
  }
  global.fetch = async () => respond(404, { detail: 'No evaluation results' })
  await assert.rejects(loadEvaluation(), e => e.status === 404)
  const combined = { n_cases: 123 }
  global.fetch = async () => respond(200, combined)
  assert.deepEqual(await loadEvaluation(), combined)
  console.log('Evaluation fallback checks passed')
}
main().catch(error => { console.error(error); process.exitCode = 1 })
