const { Schema, model } = require('mongoose')

const chatSchema = new Schema({
  channelId: Number,
  group: Boolean,
  language: String,
  title: String,
  about: String,
  fake: Boolean,
  scam: Boolean,
  url: String,
}, { versionKey: false })

chatSchema.index({ channelId: 1}, { unique: true })


module.exports = model('Chat', chatSchema)
