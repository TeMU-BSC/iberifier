const pjson = require('../package.json');


const { Command } = require('commander');
const program = new Command();


program
    .name('get-history')
    .description('Get chat history from telegram groups or channels')
    .version(pjson.version);

const command = program.command('history')
    .description('Get all channels/groups from txt file and saves the history to database')
    .requiredOption('--file <file>', 'File')



program.parse(process.argv)
const options = command.opts()

module.exports =
    {options,}