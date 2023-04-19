
// GENERAL STATS

use backward_pipeline
db.maldita.find().count()
db.google.find().count()
db.tweets.find().count()
db.mynews.find().count()

use telegram_observer
db.messages.find().count()

// FIELD STATS

use backward_pipeline

db.maldita.aggregate([{"$group": {"_id": "$categories", "count":{"$sum": 1}}}])
db.maldita.aggregate([{"$group": {"_id": "$organization", "count":{"$sum": 1}}}])
db.maldita.aggregate([{"$group": {"_id": "$type", "count":{"$sum": 1}}}])
db.maldita.aggregate([{"$group": {"_id": "$organizationCalification.calification.name", "count":{"$sum": 1}}}])

db.google.aggregate([{"$group": {"_id": "$claimReview.publisher", "count":{"$sum": 1}}}])
db.google.aggregate([{"$group": {"_id": "$claimReview.textualRating", "count":{"$sum": 1}}}])

db.tweets.aggregate([{"$group": {"_id": null, "average":{"$avg": "$tweet.public_metrics.retweet_count"}}}])
db.tweets.aggregate([{"$group": {"_id": null, "average":{"$avg": "$tweet.public_metrics.reply_count"}}}])
db.tweets.aggregate([{"$group": {"_id": null, "average":{"$avg": "$tweet.public_metrics.like_count"}}}])
db.tweets.aggregate([{"$group": {"_id": null, "average":{"$avg": "$tweet.public_metrics.quote_count"}}}])

db.mynews.aggregate([{"$group": {"_id": "$Newspaper", "count":{"$sum": 1}}}])
db.mynews.aggregate([{"$group": {"_id": "$Edition", "count":{"$sum": 1}}}])

// TIME STATS

db.maldita.find({},{'date':1}).sort({ date: 1 }).limit(1)
db.maldita.find({},{'date':1}).sort({ date: -1 }).limit(1)

db.google.find({},{'date':1}).sort({ date: 1 }).limit(1)
db.google.find({},{'date':1}).sort({ date: -1 }).limit(1)

db.tweets.find({},{'date':1}).sort({ date: 1 }).limit(1)
db.tweets.find({},{'date':1}).sort({ date: -1 }).limit(1)

db.mynews.find({},{'date':1}).sort({ date: 1 }).limit(1)
db.mynews.find({},{'date':1}).sort({ date: -1 }).limit(1)

// DO WE NEED OTHER STATS?