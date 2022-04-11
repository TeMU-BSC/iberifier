const events = require('events');
const fs = require('fs');
const readline = require('readline');

const processLineByLine = (file) => new Promise((resolve, reject) => {

    let lines = []
    const rl = readline.createInterface({
        input: fs.createReadStream(file),
        crlfDelay: Infinity
    })

    rl.on("line", (line) => lines.push(line) )

    events.once(rl, 'close')
        .then(() => resolve(lines))
        .catch((err) => reject(err))
})


module.exports = {
    processLineByLine,
}