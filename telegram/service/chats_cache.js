const {getChatsIterator, isMember, addMember, publish} = require("../store/cache.js")

const getChats = async () => {
    let chats = []
    for await (const member of getChatsIterator()) {
        chats.push(member)
    }
    return chats
}

const exists = async (chat) => {
    return new Promise((resolve) => {
        resolve(isMember(chat))
    })
}

const addChat = (chat) => {
    return new Promise(async (resolve, reject) => {
        resolve(await addMember(chat))
    })
}

const publishUpdate = async (channel, message) => {
    await publish(channel, message)

}
module.exports = {
    addChat,
    getChats,
    exists,
    publishUpdate
}