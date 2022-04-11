const { newTelegramClient } = require('./client.js')
const { Api } = require('telegram')

const { addNewChat } = require('../service/chats')
const { createMsgBody } = require('../helpers/msg_body')
const { insertLog } = require('../helpers/logger')
const { addNewMessage, findLastMessage } = require('../service/message')
const { DateTime } = require('luxon')

class TelegramService {
  client

  constructor () {
  }

  async initClient () {
    this.client = await newTelegramClient()
    return this
  }

  async destroyClient () {
    await this.client.destroy()
  }

  getReplies (channel, messageId) {
    return new Promise((resolve, reject) => {
      this.client.invoke(new Api.messages.GetReplies({
        peer: channel,
        msgId: messageId,
        offsetId: 0,
        offsetDate: 0,
        addOffset: 0,
        limit: 100,
        maxId: 0,
        minId: 0,
        hash: 0,
      }))
        .then(result => resolve(result))
        .catch(err => reject(err))
    })
  }

  async getMessages (chat) {
    console.log(`[${DateTime.now().toUTC()}] [INFO] - Getting messages from ${chat.url}]`)

    const requestLimitSleep = 50
    let requestCount = 0

    const telegramClient = this.client

    const entity = await telegramClient.getEntity(chat.url)
    const channelInfo = await telegramClient.invoke(new Api.channels.GetFullChannel({
      channel: entity,
    }))

    if (entity && channelInfo) {

      let offsetMessageId = 0

      const channel = {
        channelId: entity.id,
        group: !entity.broadcast,
        language: chat.language,
        title: entity.title,
        about: channelInfo.fullChat.about,
        fake: entity.fake,
        scam: entity.scam,
        url: chat.url
      }

      const updatedChat = await addNewChat(channel)

      if (!updatedChat)
      {
        throw new Error(`[${DateTime.now().toUTC()}] [ERROR] - Inserting Chat ${chat.url}`)
      }

      const lastMessage = await findLastMessage(entity.id)

      if (lastMessage !== null) {
        offsetMessageId = lastMessage?.messageId
      }

      console.log(`[${DateTime.now().toUTC()}] [INFO] - [${chat.url}: Start getting messages from offsetId: ${offsetMessageId}]`)


      for await (const messageResponse of telegramClient.iterMessages(chat.url, { reverse: true, offsetId: offsetMessageId })) {
        try {
          if (requestCount === requestLimitSleep) {
            await new Promise(r => setTimeout(r, 5000))
            requestCount = 0
          }

          requestCount++

          if (!messageResponse.message) {
            continue
          }

          const msg = await createMsgBody(messageResponse, entity)

          if (messageResponse.replies) {
            const repliesObj = await this.getReplies(entity, messageResponse.id)

            let msgBodies = await Promise.all(repliesObj.messages.map(async (element) => {
              return await createMsgBody(element, entity)
            }))

            for (let m of msgBodies){
              const replyToTopId = m.replyTo.reply_to_top_id

              if (!replyToTopId) {
                m.replyTo = undefined
              }else{
                m.replyTo.reply_to_top_id = msg.messageId
              }
            }

            msg.replies = msgBodies

          }

          await addNewMessage(msg)

        } catch (error) {
          await insertLog({ operationMessage: `On chat message iteration... `, errorMessage: error, url: chat.url })


        }

      }
    }

  }
}

module.exports = {
  TelegramService
}
