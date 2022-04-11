const getCookie = (cookieName) => {
  return new Promise((resolve) => {
    let cookie = {};
    document.cookie.split(';').forEach((el) => {
      let [key, value] = el.split('=');
      cookie[key.trim()] = value;
    });
    resolve(cookie[cookieName]);
  });
};

const removeRequestAssetsWithGoogleAds = (req) =>
  req.resourceType() === 'stylesheet' ||
  (req.resourceType() === 'script' && (req.url().includes('google') || req.url().includes('ad'))) ||
  req.resourceType() === 'media' ||
  req.resourceType() === 'font' ||
  req.resourceType() === 'image'
    ? req.abort()
    : req.continue();

const removeRequestAssets = (req) =>
  req.resourceType() === 'stylesheet' ||
  req.resourceType() === 'script' ||
  req.resourceType() === 'media' ||
  req.resourceType() === 'font' ||
  req.resourceType() === 'image'
    ? req.abort()
    : req.continue();

module.exports = {
  getCookie,
  removeRequestAssets,
  removeRequestAssetsWithGoogleAds,
};
