const { readFileSync } = require('node:fs')
const assert = require('node:assert/strict')
const ts = require('typescript')
const source = readFileSync(__dirname + '/prescription-ocr-clean.ts', 'utf8')
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
const target = { exports: {} }
new Function('exports', 'module', output)(target.exports, target)
const { cleanOcrMedicationName, cleanOcrMedications } = target.exports

assert.equal(cleanOcrMedicationName('1/ACEMUC'), 'ACEMUC')
assert.equal(cleanOcrMedicationName('2/PROPANOL'), 'PROPANOL')
assert.equal(cleanOcrMedicationName('3/AUGMENTIN'), 'AUGMENTIN')
assert.equal(cleanOcrMedicationName('1. Vitamin B12'), 'Vitamin B12')
assert.equal(cleanOcrMedicationName('Zalo đặt lịch khám: 0982.831.327'), null)
assert.equal(cleanOcrMedicationName('Phòng khám Nội Bs. Chi; SĐT: 0962.631.527'), null)
assert.equal(cleanOcrMedicationName('Sinh hiệu: Mạch 102 Vp.'), null)
assert.equal(cleanOcrMedicationName('0982.831.327'), null)
assert.deepEqual(cleanOcrMedications([{ name: '1/ACEMUC', dose: '200 mg' }, { name: 'Zalo đặt lịch khám: 0982.831.327', dose: '' }]), {
  medications: [{ name: 'ACEMUC', dose: '200 mg' }], rejected: 1,
})
console.log('PASS: numbered OCR drug names cleaned; clinic and contact rows rejected')
