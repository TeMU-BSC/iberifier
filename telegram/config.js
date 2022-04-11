module.exports = {
  session: {
    apiId: 12821895,
    apiHash: 'be747a2e71bf5995e06742f96b2529dc',
    stringSession: '1BAAOMTQ5LjE1NC4xNjcuOTEAUCgDOv/v8YrYG/cbSSK+P2LnsvgkiTxriVqrGfOHOp+4yeVWG9SxLkZERdMaLiH1rUBAe90vsBfQf/tcUNe5LmzacePhgdX+FZFMOWWqNwcc/gvi/3vBrL5jJdwAVunqZquFGj9oH6AvRm0OKFMhpOIoBaYtljQ8LXbBs4sGalwLKPHJeFS3uc5UubafFmGd/WrLXZeje6GpBBn5YA8dnrKyel5p9Wx7L7mtmoan0TUSTMCxe7Cm2RTxAogL+GK58ShE/ixTHRCgmrcDyMGMRQP5vWo0BXtBO4mfycDRko3McE7dKgsKXRePdeSVK3Ntsf32lexTbzzjNs8H9O/xTJM='
  },
  storage: {
    chatsFile: 'channels.txt'
  },

  environments: {
    development: {
      mongoUri: 'mongodb://localhost:27017/telegram_observer_development',
    },
    production: {
      mongoUri: 'mongodb://localhost:27017/telegram_observer',
    },
  },

}
