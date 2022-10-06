import logging
from datetime import datetime, timedelta

from searchtweets import ResultStream, gen_request_parameters
from tenacity import after_log, retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


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
        yield i


def search_twitter(twitter_credentials, query, search_params, rule_params):

    def prepare_query(query, additional_query):
        if isinstance(query, list):
            return "({})".format(" OR ".join(query) +
                                 ' ' + ' '.join(additional_query))
        else:
            return query

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

            date = datetime.strptime(
                search_params['date'], "%Y-%m-%dT%H:%M:%S%z")

            if search_params['days_before'] == 0 and search_params['days_after'] == 0:
                start_time = date - timedelta(minutes=1)
                end_time = date + timedelta(hours=23, minutes=59)
            else:
                start_time = date - \
                    timedelta(days=search_params["days_before"])
                end_time = date + timedelta(
                    days=search_params["days_after"], hours=23, minutes=59)

            rule_params["start_time"] = start_time.strftime("%Y-%m-%d %H:%M")
            print(rule_params['start_time'])
            rule_params["end_time"] = end_time.strftime("%Y-%m-%d %H:%M")
            print(rule_params['end_time'])
        else:
            pass
        return rule_params

    additional_query = search_params['additional_query']
    max_tweets = search_params["max_tweets"]
    output_format = search_params["output_format"]

    rule_params = prepare_time(search_params, rule_params)
    rule_params = prepare_rule(rule_params)
    rule_params['query'] = prepare_query(query, additional_query)

    rule = gen_request_parameters(**rule_params)
    return _search_twitter(
        rule,
        max_tweets,
        output_format=output_format,
        twitter_credentials=twitter_credentials,
    )
