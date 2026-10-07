const { readFileSync } = require('node:fs')
const assert = require('node:assert/strict')
const ts = require('typescript')
const source = readFileSync(__dirname + '/prescription-normalize.ts', 'utf8')
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
const target = { exports: {} }
new Function('exports', 'module', output)(target.exports, target)
const { normalizePrescriptionText: normalize, extractPrescriptionText: extract, replaceOcrRows, matchCatalogProduct } = target.exports
assert.deepEqual(normalize(''), [])
assert.deepEqual(normalize('Họ tên: Nguyễn Văn A\nChẩn đoán: Viêm họng\n1. Paracetamol 500mg\nUống ngày 2 lần\n2. Vitamin D3 1000 IU'), [
  { name: 'Paracetamol', dose: '500 mg', frequency: 'Uống ngày 2 lần' },
  { name: 'Vitamin D3', dose: '1000 IU', frequency: '' },
])
assert.deepEqual(normalize('1. Thuốc chưa rõ'), [{name: 'Thuốc chưa rõ', dose: '', frequency: ''}])
assert.equal(normalize('1. Amoxicillin 250 mg/5ml')[0].dose, '250 mg/5 ml')
assert.equal(normalize('Bệnh nhân: A 50mg').length, 0)
assert.equal(normalize('1. ThuốcX 0,5mg')[0].dose, '0,5 mg')
assert.equal(normalize('1. Thuốc X 500 MG')[0].dose, '500 MG')
assert.deepEqual(normalize('1. Thuốc A 500mg\nSáng 1 viên\nTối 1 viên\nNgày 07/10/2026\nBác sĩ: ABC'), [{name:'Thuốc A', dose:'500 mg', frequency:'Sáng 1 viên; Tối 1 viên'}])
assert.deepEqual(normalize('1. Thuốc A\n500mg\nUống sau ăn'), [{name:'Thuốc A', dose:'500 mg', frequency:'Uống sau ăn'}])
assert.deepEqual(normalize('Thuốc A\n500mg\nUống sau ăn'), [{name:'Thuốc A', dose:'500 mg', frequency:'Uống sau ăn'}])
assert.equal(normalize('1. Thuốc A 500mg + 125mg')[0].dose, '500 mg + 125 mg')
assert.equal(normalize('1. Thuốc A 325 mg; 37,5 mg')[0].dose, '325 mg; 37,5 mg')
assert.equal(normalize('1. Dung dịch X 0,9%')[0].dose, '0,9%')
assert.equal(normalize('1. Thuốc A 500mg\n20 viên\nUống 1 viên/lần')[0].frequency, 'Số lượng: 20 viên; Uống 1 viên/lần')
assert.equal(normalize('1. Thuốc A 500mg | 20 viên | Uống 1 viên/lần')[0].frequency, 'Uống 1 viên/lần; Số lượng: 20 viên')
assert.equal(normalize('1. Thuốc A 500mg\nUống 1 viên/lần\n2 lần/ngày\nTrong 5 ngày')[0].frequency, 'Uống 1 viên/lần; 2 lần/ngày; Trong 5 ngày')
assert.equal(normalize('STT Tên thuốc Hàm lượng\nNgày sinh: 2000\nĐịa chỉ: 12 ABC\nTái khám: 1. XYZ').length, 0)
const result = extract('Tên đơn thuốc: OCR-DB-001\n1. Thuốc A 500mg\nNội dung chưa rõ !\nLời dặn: kiểm thử')
assert.equal(result.name, 'OCR-DB-001')
assert.deepEqual(result.unparsedLines, ['Nội dung chưa rõ !'])
const manual = {id: 9, name:'Thuốc tay',dose:'',frequency:''}
const imported = {name:'Thuốc A',dose:'500 mg',frequency:'',ocrSource:true}
const twice = replaceOcrRows(replaceOcrRows([manual, imported], normalize('1. Thuốc B 10mg')), normalize('1. Thuốc B 10mg'))
assert.equal(twice.length, 2)
assert.deepEqual(twice[0], manual)
assert.equal(twice[1].name, 'Thuốc B')
assert.equal(replaceOcrRows([], normalize('1. Thuốc B 10mg\n2. Thuốc B 10mg')).length, 2)
const products = [{product_id:1,name:'Brand 500mg',strength:'500mg',active_ingredients:'Ingredient'}, {product_id:2,name:'Brand Plus',strength:'100mg',active_ingredients:'Other'}]
assert.equal(matchCatalogProduct({name:'Brand',dose:'500 mg',frequency:''},products).product_id,1)
assert.equal(matchCatalogProduct({name:'Brand',dose:'100 mg',frequency:''},products),undefined)
assert.equal(matchCatalogProduct({name:'Brand Plus',dose:'500 mg',frequency:''},products),undefined)
assert.equal(matchCatalogProduct({name:'Brand Pluz',dose:'100 mg',frequency:''},products),undefined)
console.log('PASS: 20 OCR mapping cases, wrapped strengths, Vietnamese instructions, metadata, combinations, decimals, quantities and repeat imports')

const table = normalize(`1. Etoricoxib (Film-coated tablets) 90mg | 30 | Viên
Ngày uống 1 viên buổi sáng, sau ăn
2. Glucosamin (Glucosamine sulfate sodium chloride 1884mg) (Viartril-S) 1500mg | 30 | Gói
Ngày uống 1 gói sau ăn
3. Mecobalamin (Methylcobalamin Capsules) 500mcg | 60 | Viên
Ngày uống 2 viên chia 2 lần
4. Pregabalin (Lyrica 75mg) 75mg | 30 | Viên
Ngày uống 1 viên buổi tối
5. Lansoprazole 30mg (Scolanzo 30mg) | 30 | Viên
Ngày uống 1 viên buổi sáng, trước ăn
Lời dặn của bác sĩ: Đeo đai thắt lưng`)
assert.equal(table.length, 5)
assert.deepEqual(table.map(row=>row.dose), ['90 mg','1500 mg','500 mcg','75 mg','30 mg'])
assert.equal(table[4].name,'Lansoprazole (Scolanzo)')
assert.equal(table[3].name,'Pregabalin (Lyrica)')
assert(table.every(row=>row.frequency.includes('Số lượng:')))
assert(table[4].frequency.includes('trước ăn'))
assert(!table[4].frequency.includes('thắt lưng'))
assert.equal(normalize('1 Etoricoxib 90mg\n30 Viên\nNgày uống 1 viên')[0].name,'Etoricoxib')
assert.equal(normalize('1 Etoricoxib 90mg\n30 Viên\nNgày uống 1 viên')[0].frequency,'Số lượng: 30 Viên; Ngày uống 1 viên')
assert.equal(normalize('1. Paracetamol 500 mg\nHoạt chất: Paracetamol\nCách dùng: Theo đơn gốc')[0].frequency,'Cách dùng: Theo đơn gốc')
assert.equal(target.exports.prescriptionLookupName('Lansoprazole (Scolanzo)'), 'Lansoprazole')
assert.equal(target.exports.prescriptionLookupName('Glucosamin (Viartril-S)'), 'Glucosamin')
console.log('PASS: five-drug table, separate quantity columns, parenthetical composition, brand after strength, numbering without punctuation and footer isolation')
