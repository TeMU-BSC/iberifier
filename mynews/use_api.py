
import requests
import os
import importlib.util

cred_path = os.path.join(os.path.dirname(__file__), "../credentials.py")
spec = importlib.util.spec_from_file_location("credentials", cred_path)
credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(credentials)
credentials = credentials.mynews_credentials

key="Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJvN3BtOElURWk4JjYxUXBJIiwiaWF0IjoxNjY0MjY2ODgyLjkzNzQ1MywiZXhwIjoxNjY0MjcwNDgyLjkzNzQ1M30.9qNyQrsfQAR3JOa2dzR8zBgSHIalIIVqYzZkzExSq0g"

url = 'https://api.mynews.es/api/hemeroteca/'

data = {"query": "(BSC AND BARCELONA) OR (BSC AND MADRID)", "maxResults":2}
header = {'Authorisation': key}

response = requests.post(url, headers=header, params=data)

print(response)

data = response.json()

print(data)