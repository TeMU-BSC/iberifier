
TOKEN=$(curl --location --request POST 'https://api.mynews.es/api/token/' \
--form 'public_key="o7pm8ITEi8&61QpI"' \
--form 'password="Qs7A&!&aI56N"')

curl --location --request POST 'https://api.mynews.es/api/hemeroteca/' \
--header 'Authorization: Bearer '$TOKEN \
--form 'query="(baches AND descarriló AND mal) OR (baches AND descarriló AND ohio) OR (baches AND descarriló AND químicos) OR (baches AND mal AND ohio) OR (baches AND mal AND químicos) OR (baches AND ohio AND químicos) OR (descarriló AND mal AND ohio) OR (descarriló AND mal AND químicos) OR (descarriló AND ohio AND químicos) OR (mal AND ohio AND químicos)"' \
--form 'fromTime="1675296000"' \
--form 'toTime="1675382400"' \
--form 'maxResults="2"'

