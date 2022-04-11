
const {StringSession} = require("telegram/sessions");
const {TelegramClient, Api} = require("telegram");
const input = require("input");
const {session} = require("../config");
const fs = require("fs");
const apiId = session.apiId
const apiHash = session.apiHash
const stringSession = new StringSession("1BAAOMTQ5LjE1NC4xNjcuOTEAUCgDOv/v8YrYG/cbSSK+P2LnsvgkiTxriVqrGfOHOp+4yeVWG9SxLkZERdMaLiH1rUBAe90vsBfQf/tcUNe5LmzacePhgdX+FZFMOWWqNwcc/gvi/3vBrL5jJdwAVunqZquFGj9oH6AvRm0OKFMhpOIoBaYtljQ8LXbBs4sGalwLKPHJeFS3uc5UubafFmGd/WrLXZeje6GpBBn5YA8dnrKyel5p9Wx7L7mtmoan0TUSTMCxe7Cm2RTxAogL+GK58ShE/ixTHRCgmrcDyMGMRQP5vWo0BXtBO4mfycDRko3McE7dKgsKXRePdeSVK3Ntsf32lexTbzzjNs8H9O/xTJM=");


;(async () => {

    const client = new TelegramClient(stringSession, apiId, apiHash, { connectionRetries: 5 })
    await client.start({
        phoneNumber: async () => await input.text('number ?'),
        password: async () => await input.text('password?'),
        phoneCode: async () => await input.text('Code ?'),
        onError: (err) => console.log(err),
    })


    // const saveSession = client.session.save()

    // console.log(saveSession)

    console.log('[Telegram Observer] Connected!')


    const result = await client.invoke(
        new Api.channels.GetFullChannel({
            channel: "https://t.me/agorachain",
        })
    );

    const channel = await client.getEntity("https://t.me/agorachain")

    // const fullChannelInfo = await client.invoke(new Api.channels.GetFullChannel({
    //     channel: channel,
    // }))

    // const info = {about: fullChannelInfo.fullChat.about}

    console.log(channel.broadcast)
})();
