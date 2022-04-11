const {environments} = require("./config.js");

module.exports = {
    apps : [{
        name   : "telegram-observer",
        script : "./index.js",
        env_production: {
            NODE_ENV: "production",
            MONGO_URI: environments.production.mongoUri
        },
        env_development: {
            NODE_ENV: "development",
            MONGO_URI: environments.development.mongoUri
        }
    }]
}
