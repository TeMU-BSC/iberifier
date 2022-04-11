from googleapiclient.discovery import build
import json
import sys

query = sys.argv[1]

factCheckService = build("factchecktools", "v1alpha1", developerKey='AIzaSyAkulJMUBGrSBq0c5kBoZ-w97LpSiqPZus')
request = factCheckService.claims().search(query=query,
                                            #reviewPublisherSiteFilter="Maldita.es",
                                            pageSize=1000000,#)
                                           #query=query,
                                           languageCode="pt")#,
                                           #pageToken='CAs',
                                           # maxAgeDays='',
                                           #offset=10)
                                           #reviewPublisherSiteFilter="Maldita.es",
response = request.execute()

with open("results_{}.json".format(query), "w") as f:
    f.write(json.dumps(response))

