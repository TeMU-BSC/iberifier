const { Schema, model } = require('mongoose')

const messageSchema = new Schema({
  messageId: Number,
  channelId: Number,
  date: Date,
  replyTo: {
    reply_to_msg_id: Number,
    reply_to_top_id: Number,
  },
  message: String,
  replies: {type: Array, required: false, default: undefined},

  mentioned: Boolean,
  post: Boolean,
  sender: {type: Object},
  views: {type: Number, default: 0},
  instantCrawled: {type: Object, default: undefined},

}, { versionKey: false })

messageSchema.index({ channelId: 1, messageId: -1}, )


module.exports = model('Message', messageSchema)