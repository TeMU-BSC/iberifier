
use telegram_observer;
show collections;

db.messages.count(); // 396249

db.messages.find();

db.messages.distinct("channelId"); // 34 diferents

var allKeys = {};
db.messages.find().forEach(function(doc){Object.keys(doc).forEach(function(key){allKeys[key]=1})});
allKeys;

//{
//  _id: 1,
//  messageId: 1,
//  channelId: 1,
//  date: 1,
//  message: 1,
//  mentioned: 1,
//  post: 1,
//  sender: 1,
//  views: 1,
//  instantCrawled: 1,
//  replyTo: 1,
//  replies: 1
//}

# ONLY THIS LAST THREE ARE NOT ALWAYS THERE:
db.messages.find({ 'instantCrawled': { "$exists": true } }).count(); // 10826
db.messages.find({ 'replyTo': { "$exists": true } }).count(); // 87751
db.messages.find({ 'replies': { "$exists": true } }).count(); // 173539
