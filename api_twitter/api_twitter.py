import os
import yaml
import logging
from datetime import datetime, timedelta
import logging.config

from searchtweets import ResultStream, gen_request_parameters
from tenacity import after_log, retry, stop_after_attempt, wait_exponential

config_path = os.path.join(os.path.dirname(
    __file__), '../config', 'config.yaml')
config_all = yaml.safe_load(open(config_path))

logging_config_path = os.path.join(os.path.dirname(
    __file__), '../config', config_all['logging']['logging_filename'])
with open(logging_config_path,  "r") as f:
    yaml_config = yaml.safe_load(f.read())
    logging.config.dictConfig(yaml_config)

logger = logging.getLogger(config_all['logging']['level'])


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
        except KeyError:  # Sometime the searchtweets lib crash because it cannot find the right key in the max_tweets
            pass


def search_twitter(twitter_credentials, query, search_params, rule_params):

    def prepare_query(query, additional_query):
        # CAREFUL: The additional query need to be outside the () from the keyword query
        # https://twittercommunity.com/t/premium-account-is-retweet-not-working/128064/14
        return ' '.join(additional_query) + ' (' + query + ')'     # if isinstance(query, list):
        #     return "({})".format(" OR ".join(query)) + ' ' + ' '.join(additional_query)
        # else:
        #     return query 

    def prepare_rule(params):
        for k in params:
            if isinstance(params[k], list):
                if len(params[k]) > 0:
                    params[k] = ",".join(params[k])
                else:
                    params[k] = None
        return params

    def prepare_time(search_params, rule_params):

        if search_params["date"] is not None and rule_params["since_id"] is None:

            date = search_params['date']
            if isinstance(date, str):
                date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z")

            if search_params['days_before'] == 0 and search_params['days_after'] == 0:
                start_time = date - timedelta(minutes=1)
                end_time = date + timedelta(hours=23, minutes=59)
            else:
                start_time = date - \
                    timedelta(days=search_params["days_before"])
                # Replace the hours and minute to midnight for that day 
                start_time = start_time.replace(hour=0, minute=0, second=0)
                end_time = date + timedelta(
                    days=search_params["days_after"], hours=23, minutes=59)

                end_time = end_time.replace(hour=0, minute=0, second=0)
            rule_params["start_time"] = start_time.strftime("%Y-%m-%d %H:%M")
            rule_params["end_time"] = end_time.strftime("%Y-%m-%d %H:%M")
        else:
            pass
        return rule_params

    additional_query = search_params['additional_query']
    max_tweets = search_params["max_tweets"]
    output_format = search_params["output_format"]

    rule_params = prepare_time(search_params, rule_params)
    rule_params = prepare_rule(rule_params)
    rule_params['query'] = prepare_query(query, additional_query)
    print(rule_params['query'])

    rule = gen_request_parameters(**rule_params)
    return _search_twitter(
        rule=rule,
        max_tweets=max_tweets,
        output_format=output_format,
        twitter_credentials=twitter_credentials,
    )
