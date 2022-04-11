const redisClient = require('redis').createClient();
const { url, redis } = require('./config/site');

const buildPageUrlList = (url, last) =>
  new Promise((resolve) =>
    resolve(
      Array(last)
        .fill()
        .map((_, i) => `${url}?page=${i + 1}`)
    )
  );

(async () => {
  try {
    await redisClient.connect();
    const pageList = await buildPageUrlList(url, 9558);
    await redisClient.sAdd(redis.keys.pageList, pageList);
  } catch (err) {
    console.log(err);
  }
})();
