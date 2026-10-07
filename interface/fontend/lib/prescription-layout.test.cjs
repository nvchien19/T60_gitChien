const fs = require('node:fs')
const assert = require('node:assert/strict')
const ts = require('typescript')
function load(name) {
  const module = {exports:{}}
  const source = ts.transpileModule(fs.readFileSync(__dirname+'/'+name+'.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
  new Function('exports','module','require',source)(module.exports,module,()=>load('prescription-normalize'))
  return module.exports
}
const {prescriptionTextFromLayout, choosePrescriptionCandidate, prescriptionNeedsAnotherPass} = load('prescription-layout')
const word=(text,x,y,width=30)=>({text,confidence:90,bbox:{x0:x,y0:y,x1:x+width,y1:y+20}})
const block=words=>({paragraphs:[{lines:[{words}]}]})
const columns = {text:'1. Alpha 10mg\n2. Beta 20mg\n30\n60\nViên\nViên',confidence:90,blocks:[
  block([word('1.',10,10),word('Alpha',45,10,60),word('10mg',120,10,60),word('2.',10,70),word('Beta',45,70,60),word('20mg',120,70,60)]),
  block([word('30',430,12),word('60',430,72)]),
  block([word('Viên',550,10,50),word('Viên',550,70,50)]),
]}
const restored=prescriptionTextFromLayout(columns)
assert.equal(restored,'1. Alpha 10mg | 30 | Viên\n2. Beta 20mg | 60 | Viên')
const rows = load('prescription-normalize').normalizePrescriptionText(restored)
assert.equal(rows.length,2)
assert.equal(rows[0].frequency,'Số lượng: 30 Viên')
assert.equal(rows[1].frequency,'Số lượng: 60 Viên')
assert.equal(choosePrescriptionCandidate([columns]).text,restored)
assert.equal(prescriptionTextFromLayout({text:'original',confidence:80}), 'original')
assert.equal(choosePrescriptionCandidate([{text:'No drug recognized',confidence:95},{text:'1. Alpha 10mg\n2. Beta 20mg',confidence:85}]).confidence,85)
assert.equal(prescriptionTextFromLayout({text:'',confidence:0,blocks:[block([word('90',10,10,0)])]}),'')
assert(prescriptionNeedsAnotherPass('1. Alpha 10mg\n5. Beta 20mg',90))
assert(!prescriptionNeedsAnotherPass('1. Alpha 10mg\n2. Beta 20mg',90))
assert(prescriptionNeedsAnotherPass('1. Alpha 10mg\n2. Beta 20mg',55))
console.log('PASS: geometric row reconstruction across three OCR blocks, skewed baselines, quantity mapping, missing-block fallback and multi-pass selection')
