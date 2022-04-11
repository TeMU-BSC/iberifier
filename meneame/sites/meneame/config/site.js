module.exports = {
  url: 'https://meneame.net/',
  mongo: {
    uri: 'mongodb://localhost:27017/?readPreference=primary&directConnection=true&ssl=false',
    database: 'andrei_testing',
    collections: {
      base: 'meneame',
      errors: 'errors',
    },
    enabled: true,
  },
  redis: {
    keys: {
      listUrl: 'meneameListUrl',
      pageList: 'meneamePageList',
      secondaryListUrl: 'meneameSecondaryListUrl',
    },
    enabled: true,
  },
};
