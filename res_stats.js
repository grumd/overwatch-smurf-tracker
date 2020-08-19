const fs = require('fs');

const results = JSON.parse(fs.readFileSync('./results.json'))
const resultsOld = JSON.parse(fs.readFileSync('./results_backup.json'))

console.log(results.length)
console.log(resultsOld.length)