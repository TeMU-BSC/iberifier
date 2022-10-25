
TOKEN=$(curl --location --request POST 'https://api.mynews.es/api/token/' \
--form 'public_key="o7pm8ITEi8&61QpI"' \
--form 'password="Qs7A&!&aI56N"')

curl --location --request POST 'https://api.mynews.es/api/hemeroteca/' \
--header 'Authorization: Bearer '$TOKEN \
--form 'query="(BSC AND BARCELONA) OR (BSC AND MADRID)"' \
--form 'fromTime="1654321118"' \
--form 'toTime="1656913073"' \
--form 'maxResults="2"' \
--form 'publications="116"' \
--form 'publications="117"'

curl --location --request GET 'https://api.mynews.es/api/publicaciones/' \
--header 'Authorization: Bearer '$TOKEN