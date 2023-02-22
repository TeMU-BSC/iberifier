import os
import yaml
import logging
import logging.config

from searchtweets import ResultStream, gen_request_parameters
from tenacity import after_log, retry, stop_after_attempt, wait_exponential

config_path = os.path.join(os.path.dirname(__file__), "../config", "config.yaml")
config_all = yaml.safe_load(open(config_path))

logging_config_path = os.path.join(
    os.path.dirname(__file__), "../config", config_all["logging"]["logging_filename"]
)
with open(logging_config_path, "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all["logging"]["level"])


@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60 * 10),
    stop=stop_after_attempt(10),
    after=after_log(logger, logging.INFO),
)
def _search_twitter(rule, max_tweets, output_format, twitter_credentials):
    rs = ResultStream(
        request_parameters=rule,
        max_tweets=max_tweets,
        output_format="a",
        **twitter_credentials
    )
    logger.info(rs)
    results = rs.stream()

    for i in results:
        try:
            yield i
        # Sometime the searchtweets lib crash
        # because it cannot find the right key in the max_tweets
        except KeyError:
            pass


def search_twitter(twitter_credentials, query, search_params, rule_params):
    def prepare_query(query, additional_query):
        # CAREFUL: The additional query need
        # to be outside the () from the keyword query
        # https://twittercommunity.com/t/premium-account-is-retweet-not-working/128064/14
        # if isinstance(query, list):
        return " ".join(additional_query) + " (" + query + ")"

    def prepare_rule(params):
        for k in params:
            if isinstance(params[k], list):
                if len(params[k]) > 0:
                    params[k] = ",".join(params[k])
                else:
                    params[k] = None
        return params

    additional_query = search_params["additional_query"]
    max_tweets = search_params["max_tweets"]
    output_format = search_params["output_format"]

    rule_params = prepare_rule(rule_params)
    rule_params["query"] = prepare_query(query, additional_query)
    print(rule_params["query"])

    rule = gen_request_parameters(**rule_params)
    return _search_twitter(
        rule=rule,
        max_tweets=max_tweets,
        output_format=output_format,
        twitter_credentials=twitter_credentials,
    )
