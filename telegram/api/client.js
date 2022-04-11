const { session } = require('../config.js')

const {StringSession} = require("telegram/sessions");
const {TelegramClient} = require("telegram");
const input = require("input");
const apiId = session.apiId
const apiHash = session.apiHash
const stringSession = new StringSession(session.stringSession); // fill this later with the value from session.save()


const newTelegramClient = async () => {
    const client = new TelegramClient(stringSession, apiId, apiHash, { connectionRetries: 5 })
    await client.start({
        phoneNumber: async () => await input.text('number ?'),
        password: async () => await input.text('password?'),
        phoneCode: async () => await input.text('Code ?'),
        onError: (err) => console.log(err),
    })
    console.log('[Telegram Observer] Connected!')
    client.session.save()

    return client

}

module.exports = {
    newTelegramClient
}