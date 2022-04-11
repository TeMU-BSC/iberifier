const { Schema, model } = require('mongoose')

const logSchema = new Schema({
  date: {type: Date, default: Date.now},
  error: {type: String, default: undefined},
  operation: String,
  channelId: {type: Number, default: undefined}
}, { versionKey: false })


module.exports = model('Log', logSchema)