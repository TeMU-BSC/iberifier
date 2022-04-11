
import requests

response = requests.get("https://repositorio.iberifier.eu/api/contents?page=1&itemsPerPage=30", auth=requests.auth.HTTPBasicAuth('bcalvo', '5FybPQ8mD46vrRqN'))

print(response.json())