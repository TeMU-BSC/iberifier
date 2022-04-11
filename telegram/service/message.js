require('../store/mongo')

const Message = require('../models/Message')
const { insertLog } = require('../helpers/logger')
const addNewMessage = async (message) => {

  const messageSchema = new Message(message)

  try {
    await messageSchema.save()
  } catch (error) {
    await insertLog({ operationMessage: 'On save new message to Mongo DB', errorMessage: error, channelId: message.channelId })
  }
}

const findLastMessage = async (channelId) => {
  return await Message.findOne({ channelId: channelId }).exec()
}

module.exports = {
  addNewMessage,
  findLastMessage
}