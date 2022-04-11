const { DateTime } = require('luxon')

const createMsgBody = async (messageResponse, channel) => {
  let msg = {
    messageId: messageResponse.id,
    channelId: channel.id,
    date: DateTime.fromSeconds(messageResponse.date).toUTC().toISO(),
    replyTo: {
      reply_to_msg_id: messageResponse.replyTo?.replyToMsgId,
      reply_to_top_id: messageResponse.replyTo?.replyToTopId
    },
    message: messageResponse.message,
    sender: JSON.parse(JSON.stringify(messageResponse.fromId, (k, v) => v && typeof v === 'object' ? v : '' + v)),
    mentioned: messageResponse.mentioned,
    post: messageResponse.post,
    views: messageResponse.views,
  }


  if (messageResponse.media?.webpage?.cachedPage) {
    const cachedPage = messageResponse.media.webpage.cachedPage

    msg.instantCrawled = {
      url: cachedPage.url,
      blocks: JSON.parse(JSON.stringify(cachedPage.blocks, (k, v) => v && typeof v === 'object' ? v : '' + v))
    }
  }

  return msg

}

module.exports = {
  createMsgBody,
}

