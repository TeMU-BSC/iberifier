const {createClient} = require("redis")
const {storage} = require("../config.js")


const redisClient = createClient();

redisClient.on('error', (err) => console.log('Redis Client Error', err));

redisClient.connect()
    .then(() => console.log(`Redis client connected!`))
    .catch(err => console.log(err))



const getChatsIterator = () => {
    return redisClient.sScanIterator(storage.chats)
}

const isMember = (member) => {
    return redisClient.sIsMember(storage.chats, member)
}

const addMember = (member) => {
    return redisClient.sAdd(storage.chats, member)
}

const publish = async (channel, message) => {
    await redisClient.publish(channel, message)

}

const createSubscriber = async () => {
    const subscriber = createClient()
    await subscriber.connect()

    return subscriber

}
module.exports = {
    getChatsIterator,
    isMember,
    addMember,
    publish,
    createSubscriber
}