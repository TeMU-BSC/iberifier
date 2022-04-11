require('../store/mongo')

const Chat = require('../models/Chat')
const {insertLog } = require('../helpers/logger')

const addNewChat = async (chat) => {

    const updated = await Chat.findOneAndUpdate({
      channelId: chat.channelId
    }, chat, { upsert: true });

    console.log({chat: chat, updated: updated})

    if (!updated) {
      await insertLog({ operationMessage: 'On save new chat.', errorMessage: 'Not able to save new chat...' })
      throw new Error('Chat not updated')
    }

    await insertLog({ operationMessage: `New chat ${chat.title} saved to Database `})

    return updated


}


module.exports = {
  addNewChat,
}
