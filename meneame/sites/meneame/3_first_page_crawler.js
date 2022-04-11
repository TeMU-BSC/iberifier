const { MongoClient } = require('mongodb');

const redisClient = require('redis').createClient();

const { Cluster } = require('puppeteer-cluster');
const vanillaPuppeteer = require('puppeteer');

const { addExtra } = require('puppeteer-extra');
const Stealth = require('puppeteer-extra-plugin-stealth');

const { removeRequestAssetsWithGoogleAds, removeRequestAssets } = require('../../shared/utils');
const { loadHiddenComments, getCommentsList } = require('./helpers/dom');

const puppeteer = addExtra(vanillaPuppeteer);
puppeteer.use(Stealth());

require('dotenv').config();

const { mongo, redis } = require('./config/site.js');

const uri = mongo.uri;
const mongoClient = new MongoClient(uri);
const mongoDatabase = mongoClient.db(mongo.database);
const baseCollection = mongoDatabase.collection(mongo.collections.base);
const errorsCollection = mongoDatabase.collection(mongo.collections.errors);

const cacheListUrl = redis.keys.listUrl;
const cacheSecondaryListUrl = redis.keys.secondaryListUrl;

const startProcess = async (cluster) => {
  await cluster.task(async ({ page, data: url }) => {
    await page.setRequestInterception(true);
    await page.on('request', removeRequestAssets);
    const response = await page.goto(`${url}/threads`, {
      waitUntil: 'domcontentloaded',
    });
    if (response.status() === 200) {
      try {
        await page.addScriptTag({ path: '../../shared/utils.js' });
        await page.addScriptTag({ path: 'helpers/dom.js' });
        await page.addScriptTag({ path: '../../shared/helpers/luxon.min.js' });

        const meneo = await page.evaluate(async () => {
          const hiddenComments = Array.from(
            document.querySelectorAll('a[title="ver comentario"], a[title="resto del comentario"]'),
            (a) => a.parentNode.id
          );
          if (hiddenComments.length > 0) {
            await loadHiddenComments(hiddenComments);
          }

          const commentList = await getCommentsList(`#comments-top`);

          return {
            meneoId: link_id.toString(),
            content: {
              title: document
                .querySelector('div.news-body div.center-content h2 a, div.main-content h1')
                ?.innerText?.trim(),
              summary: document
                .querySelector('.news-summary .news-content, div.text')
                ?.innerText?.trim(),
              tags: Array.prototype.map.call(document.querySelectorAll('span.news-tags a'), (tag) =>
                tag?.innerText?.trim()
              ),
              pages: [
                {
                  page: '1',
                  comments: commentList,
                },
              ],
              karma: document.querySelector('.karma-number')?.innerText.trim(),
              total_pages:
                document.querySelector('.pages')?.getAttribute('data-total-pages') || '1',
            },
            comment_pages: Array.from(
              document.querySelectorAll("div.pages a:not([rel='next'])"),
              (item) => item.href
            ),
          };
        });

        if (!meneo.meneoId) {
          throw new Error(`ID is null`);
        }

        await baseCollection.updateOne(
          { meneoId: meneo.meneoId },
          { $set: meneo.content },
          { upsert: true }
        );

        if (meneo.comment_pages.length > 0) {
          await redisClient.sAdd(cacheSecondaryListUrl, meneo.comment_pages);
        }
      } catch (error) {
        await errorsCollection.insertOne({
          url: url,
          date: new Date().toISOString(),
          error: error.toString(),
        });
      }
    }
  });
  for await (const member of redisClient.sScanIterator(cacheListUrl)) {
    await cluster.queue(member);
  }
};

(async () => {
  await redisClient.connect();
  await mongoClient.connect();
  const cluster = await Cluster.launch({
    puppeteer,
    concurrency: Cluster.CONCURRENCY_PAGE,
    maxConcurrency: 30,
    monitor: true,
    puppeteerOptions: {
      headless: true,
      defaultViewport: false,
      userDataDir: '../../chrome-data',
    },
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  await startProcess(cluster);
  await cluster.idle();
  await cluster.close();

  await redisClient.disconnect();
  await mongoClient.close();
})();
