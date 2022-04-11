const { processLineByLine } = require('./helpers/file_reader.js')
const { printErrorToConsole } = require('./helpers/logger')

const { storage } = require('./config')
const { TelegramService } = require('./api/telegram')
const { DateTime } = require('luxon')

const Agenda = require("agenda");

const updateChats = async (telegramService) => {
  await processLineByLine(storage.chatsFile)

    .then(async (chats) => {
      const chatsByLanguage = chats.map(e => {
        const splited = e.split(',')
        return {url: splited[0], language: splited[1]}
      })

      for await (let chat of chatsByLanguage) {
        try {
          await telegramService.getMessages(chat)

        } catch (error) {
          printErrorToConsole(error)
        }
      }

    })
    .catch((err) => printErrorToConsole(err))
}



const agenda = new Agenda({
  db: { address: process.env.MONGO_URI, collection: "jobs" },
  defaultConcurrency: 1
});

agenda.define("update chats", async () => {
  console.log(`[${DateTime.now().toUTC()}] [INFO] - [Updating chats] `)

  const telegramService = await new TelegramService().initClient()

  await updateChats(telegramService)

  await new Promise(r => setTimeout(r, 10000))

  await telegramService.destroyClient()



});

;(
  async () => {


    try {

      await agenda.start();

      // await agenda.every("0 18 * * *", "update chats");

      await agenda.now("update chats")

    } catch (error) {
      printErrorToConsole(error)
    }

  }
)()
