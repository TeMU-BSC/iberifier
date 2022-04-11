require('../store/mongo')
const { DateTime } = require('luxon')
const Log = require('../models/Log')

const insertLog = async ({operationMessage, errorMessage, channelId}) => {

  const log = new Log({
    date: DateTime.now().toUTC(),
    error: errorMessage,
    operation: operationMessage,
    channelId: channelId
  })

  await log.save()
    .catch(error => printErrorToConsole(error))
}


const printErrorToConsole = (error) => console.log(error)

module.exports = {
  printErrorToConsole,
  insertLog,
}
