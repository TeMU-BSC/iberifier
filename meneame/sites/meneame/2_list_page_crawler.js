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

const cacheListUrl = redis.keys.listUrl;
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
          crawledIsoDate: luxon.DateTime.now().toISO(),
          meneos: e
            .querySelector(
              'div.news-summary div.news-shakeit div.votes a, div.shake-container div.news-shakeit div.votes a'
            )
            ?.innerText?.trim(),
          url: e.querySelector('.news-details-main a.comments').href,
          category: e.querySelector('div.news-details .sub-name a.subname')?.innerText?.trim(),
          imageUrl: e.querySelector("div.news-body a[title='miniatura'] img")?.getAttribute('src'),
          articleUrl: e.querySelector('div.news-submitted span.showmytitle')?.title?.trim(),
          clics: e
            .querySelector(
              'div.news-summary div.news-shakeit div.clics span, div.shake-container div.news-shakeit div.clics'
            )
            ?.innerText.replace('clics', '')
            ?.trim(),
          creationIsoDate: luxon.DateTime.fromSeconds(
            parseInt(
              e
                .querySelector('div.news-submitted span.ts.visible, div.details .format-tag span')
                ?.getAttribute('data-ts')
            ),
            {
              zone: 'Europe/Madrid',
            }
          ).toISO(),
          creationTimestamp: e
            .querySelector('div.news-submitted span.ts.visible, div.details .format-tag span')
            ?.getAttribute('data-ts'),
          controversy:
            e.querySelector(
              'div.news-summary div.news-body div.warn, div.main-content div.warn'
            ) !== null,
          positive_votes: e
            .querySelector('div.news-details span.votes-up span.positive-vote-number')
            ?.innerText?.trim(),
          negative_votes: e
            .querySelector('div.news-details span.votes-down span.negative-vote-number')
            ?.innerText?.trim(),
          number_comments: e
            .querySelector('.news-details-main a.comments')
            ?.getAttribute('data-comments-number')
            ?.trim(),
        }))
      );
      await baseCollection.insertMany(articlesList);

      await redisClient.sAdd(
        cacheListUrl,
        articlesList.map((e) => e.url)
      );
      await redisClient.sRem(cachePageList, url);
    } catch (error) {
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
