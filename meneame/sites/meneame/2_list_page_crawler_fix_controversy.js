const { MongoClient } = require('mongodb');

const redisClient = require('redis').createClient();

const { Cluster } = require('puppeteer-cluster');
const vanillaPuppeteer = require('puppeteer');

const { addExtra } = require('puppeteer-extra');
const Stealth = require('puppeteer-extra-plugin-stealth');
const { removeRequestAssets } = require('../../shared/utils');

const puppeteer = addExtra(vanillaPuppeteer);
puppeteer.use(Stealth());

require('dotenv').config();

const { mongo, redis } = require('./config/site.js');

const uri = mongo.uri;
const mongoClient = new MongoClient(uri);
const mongoDatabase = mongoClient.db(mongo.database);
const baseCollection = mongoDatabase.collection(mongo.collections.base);
const errorsCollection = mongoDatabase.collection(mongo.collections.errors);

const cachePageList = redis.keys.pageList;

const startProcess = async (cluster) => {
  await cluster.task(async ({ page, data: url }) => {
    await page.setRequestInterception(true);
    await page.on('request', removeRequestAssets);
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    try {
      await page.addScriptTag({ path: '../../shared/helpers/luxon.min.js' });

      const articlesList = await page.evaluate(() =>
        Array.from(document.querySelectorAll('.news-summary'), (e) => ({
          meneoId: e.querySelector('div.news-body').getAttribute('data-link-id')?.trim(),
          controversy:
            e.querySelector(
              'div.news-summary div.news-body div.warn, div.main-content div.warn'
            ) !== null,
        }))
      );

      for (let e of articlesList.filter((article) => article.controversy === true)) {
        await baseCollection.updateOne(
          { meneoId: e.meneoId },
          { $set: { controversy: true } },
          { upsert: false }
        );
      }


      await redisClient.sRem(cachePageList, url);
    } catch (error) {
      console.log(error);
      await errorsCollection.insertOne({
        url: url,
        date: new Date().toISOString(),
        error: error.toString(),
      });
    }
  });

  for await (const member of redisClient.sScanIterator(cachePageList)) {
    await cluster.queue(member);
  }
};

(async () => {
  try {
    await redisClient.connect();
    await mongoClient.connect();
    const cluster = await Cluster.launch({
      puppeteer,
      concurrency: Cluster.CONCURRENCY_PAGE,
      maxConcurrency: 1,
      monitor: true,
      puppeteerOptions: {
        headless: false,
        defaultViewport: false,
        userDataDir: '../../chrome-data',
      },
    });
    await startProcess(cluster);

    await cluster.idle();
    await cluster.close();

    await redisClient.disconnect();
    await mongoClient.close();
  } catch (e) {
    console.log(e);
  }
})();
