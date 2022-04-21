from functools import reduce
import math
import requests
import numpy as np
import math
import searchtweets
from tenacity import retry, stop_after_attempt, wait_exponential, after_log
import logging

logger = logging.getLogger(__name__)


class TweetSearchUtil:

    def __init__(self, path_cred, yaml_key="search_tweets_api", logging_level=logging.INFO) -> None:

        logging.basicConfig(level=logging_level)
        self.twitter_cred = searchtweets.load_credentials(path_cred,
                                          yaml_key=yaml_key,
                                          env_overwrite=False)


    @retry(
    wait=wait_exponential(multiplier=1, min=4, max=60 * 10),
    stop=stop_after_attempt(10),
    after=after_log(logger, logging.INFO),
    )
    def _make_tweets_request(self,rule, max_results=500):
        """Wrap the request with tenacity 
        to make sure to retry if exceptions are raised.  
        Since a limit calls per time, there is an exponential grow in the
        waiting time
        """

        tweets = searchtweets.collect_results(rule,
                result_stream_args=self.twitter_cred,
                max_tweets=max_results)

        return tweets
    

    def search_tweets_by_query(self,query, results_total=500,
        results_per_call=500, start_time=None, end_time=None,
        since_id=None, until_id=None, tweet_fields=None, user_fields=None,
        media_fields=None, place_fields=None, poll_fields=None,
        expansions=None, stringify=True):
        """
        Search tweets by the given query using the official API v2.
        For more information about the parameters see the official Twitter API.
        https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference/get-tweets-search-all 
        
        Parameters
        ----------
        query : str
            Query to search tweets for. For a guide to how build a query visit
            the API documentation: https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query
        results_total : int
            Number of maximum results to be retrieved
        results_per_call : int
            number of maximum results retrieved in each API call.
            Maximum and by default is 500
        stringify: bool
            specifies the return type, dict
            or json-formatted str
        
        For the next parameters they determine the fields to be returned, see API docs.
        start_time : str
        end_time : str
        since_id : str
        until_id : str
        tweet_fields : str
        user_fields : str
        media_fields : str
        place_fields : str 
        poll_fields : str
        expansions : str

        Returns
        -------
        list
            A list of json representing tweets.
        """

        rule = searchtweets.gen_request_parameters(query,
                        results_per_call=results_per_call,
                        start_time=start_time,
                        end_time=end_time,
                        since_id=since_id,
                        until_id=until_id,
                        tweet_fields=tweet_fields,
                        user_fields=user_fields,
                        media_fields=media_fields,
                        place_fields=place_fields,
                        poll_fields=poll_fields,
                        expansions=expansions,
                        granularity=None,
                        stringify=stringify)
        
        tweets_data = self._make_tweets_request(rule, results_total)

        return tweets_data[0]['data']

    @retry(
    wait=wait_exponential(multiplier=1, min=4, max=60 * 10),
    stop=stop_after_attempt(10),
    after=after_log(logger, logging.INFO),
    )
    def _request_api_call(self, url,headers):
        response = requests.request("GET", url, headers=headers)
        logging.debug("Status code: {}".format(response.status_code))
        if response.status_code != 200:
            raise Exception(
                "Request returned an error: {} {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()
    
    def _process_response(self, resp):
        if "data" not in resp.keys():
            logging.debug("No data in response: {}".format(resp))
            return []
                
        return resp["data"]

    
    def _from_strlist_to_list(self, strlist):
        return [s.strip for s in strlist.split(',')]
        
    
    def retreive_tweets_by_id(self,ids,tweet_fields=None,
                        user_fields=None,
                        expansions=None):
        """
        Fetches and returns the tweets for the ids passed in parameters.  
        Does not guarantees all the tweets will be returned (e.g. tweets who
        have been deleted)

        The fields to be returned in the tweets json have to be specified.
        For more information refer to the twitter API.
        https://developer.twitter.com/en/docs/twitter-api/tweets/lookup/api-reference/get-tweets

        Parameters
        ----------
        ids : str list
            List of ids to retrieve
        tweet_fields : str list or str
            list of fields for tweet fields to be retrieved
        user_fields : str list or str
            list of fields for user fields to be retrieved
        expansions : str list or str
            list of fields for expansion fields to be retrieved

        Returns
        -------
        list
            A list of json representing tweets.

        """

        # Create end of URL call
        fields = ''
        if tweet_fields:
            if isinstance(tweet_fields, str):
                tweet_fields = self._from_strlist_to_list(tweet_fields)
            fields += '&tweets.fields='+','.join(tweet_fields)
        if user_fields:
            if isinstance(user_fields, str):
                user_fields = self._from_strlist_to_list(user_fields)
            fields += '&user.fields='+','.join(user_fields)
        if expansions:
            if isinstance(expansions, str):
                expansions = self._from_strlist_to_list(expansions)
            fields += '&expansions='+','.join(expansions)
        
        # create header with bearer token
        bearer_token = self.twitter_cred['bearer_token']
        headers = {"Authorization": "Bearer {}".format(bearer_token)}


        twitter_data = []

        # Twitter limits to 100 ids per call
        ids_chunks = np.array_split(ids, math.ceil(len(ids)/100))
        for arr in ids_chunks:
            id_list = list(arr)
            ids_str = "ids=" +",".join(map(str,id_list))
            url = "https://api.twitter.com/2/tweets?{}".format(ids_str)

            response = self._request_api_call(url,headers)

            twitter_data += self._process_response(response)
        

        return twitter_data

    def retreive_users_by_id(self, ids, user_fields=None):
        """
        Fetches and returns the users for the ids passed in parameters.  
        Does not guarantees all the users will be returned (e.g. users who
        have been deleted)

        The fields to be returned in the users json have to be specified.
        For more information refer to the twitter API.
        https://developer.twitter.com/en/docs/twitter-api/users/lookup/api-reference/get-users

        Parameters
        ----------
        ids : str list
            List of ids to retrieve
        user_fields : str list or str
            list of fields for user fields to be retrieved

        Returns
        -------
        list
            A list of json representing users.

        """

        # Create end of URL call
        fields = ''
        if user_fields:
            if isinstance(user_fields, str):
                user_fields = self._from_strlist_to_list(user_fields)
            fields += '&user.fields='+','.join(user_fields)
        
        # create header with bearer token
        bearer_token = self.twitter_cred['bearer_token']
        headers = {"Authorization": "Bearer {}".format(bearer_token)}

        twitter_data = []

        # Twitter limits to 100 ids per call
        ids_chunks = np.array_split(ids, math.ceil(len(ids)/100))
        for arr in ids_chunks:
            id_list = list(arr)
            ids_str = "ids=" +",".join(map(str,id_list))
            url = "https://api.twitter.com/2/users?{}".format(ids_str)

            response = self._request_api_call(url,headers)

            twitter_data += self._process_response(response)
        

        return twitter_data