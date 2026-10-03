const { readFileSync } = require('node:fs')
const assert = require('node:assert/strict')
const ts = require('typescript')
const source = readFileSync(__dirname + '/prescription-normalize.ts', 'utf8')
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
const target = { exports: {} }
new Function('exports', 'module', output)(target.exports, target)
const normalize = target.exports.normalizePrescriptionText
assert.deepEqual(normalize(''), [])
assert.deepEqual(normalize('Họ tên: Nguyễn Văn A\nChẩn đoán: Viêm họng\n1. Paracetamol 500mg\nUống ngày 2 lần\n2. Vitamin D3 1000 IU'), [
  { name: 'Paracetamol', dose: '500 mg', frequency: 'Uống ngày 2 lần' },
  { name: 'Vitamin D3', dose: '1000 IU', frequency: '' },
])
assert.deepEqual(normalize('1. Thuốc chưa rõ'), [{name: 'Thuốc chưa rõ', dose: '', frequency: ''}])
assert.equal(normalize('1. Amoxicillin 250 mg/5ml')[0].dose, '250 mg/5 ml')
assert.equal(normalize('Bệnh nhân: A 50mg').length, 0)
assert.equal(normalize('1. ThuốcX 0,5mg')[0].dose, '0,5 mg')
console.log('PASS: empty input, patient metadata, Vietnamese instructions, unknown names, concentrations, decimal doses')

