const fs=require('node:fs')
const assert=require('node:assert/strict')
const ts=require('typescript')
const moduleTarget={exports:{}}
const js=ts.transpileModule(fs.readFileSync(__dirname+'/prescription-ocr.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
new Function('exports','module',js)(moduleTarget.exports,moduleTarget)
const crop=moduleTarget.exports.prescriptionCropRegion
assert.deepEqual(crop(2000,1200),{x:0,y:0,width:2000,height:1200})
assert.deepEqual(crop(2000,1200,{x:.1,y:.2,width:.8,height:.6}),{x:200,y:240,width:1600,height:720})
assert.deepEqual(crop(2000,1200,{x:.8,y:.9,width:.8,height:.8}),{x:1600,y:1080,width:400,height:120})
assert.throws(()=>crop(2000,1200,{x:0,y:0,width:0,height:1}))
assert.throws(()=>crop(2000,1200,{x:NaN,y:0,width:1,height:1}))
console.log('PASS: crop coordinate mapping, edge clamping, invalid/empty region validation')
