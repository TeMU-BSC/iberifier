
// COMMANDS TO EXPLORE TELEGRAM

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

// Only the last three fields are not always there:
db.messages.find({ 'instantCrawled': { "$exists": true } }).count(); // 10826
db.messages.find({ 'replyTo': { "$exists": true } }).count(); // 87751
db.messages.find({ 'replies': { "$exists": true } }).count(); // 173539

// SETTING THE DATES TO DATETIME FORMAT

dateConversionStage = {$addFields: {date: { $toDate: "$created_at" }}};
db.twitter_test2.aggregate( [dateConversionStage] ).forEach(function (x){db.twitter_test2.updateOne({_id: x._id}, {$set: {"date": x.date}})})

// GET TWITS FROM SPECIFIC DATES

db.twitter_test2.find({"date":{$gte:ISODate("2022-02-01"),$lt:ISODate("2022-02-11")}})