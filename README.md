$ curl -i -X PUT http://localhost:8000/tasks/5 -H "Content-Type: application/json" -d '{"done":true}'
HTTP/1.1 200 OK
date: Wed, 29 Jul 2026 08:52:13 GMT
server: uvicorn
content-length: 47
content-type: application/json

{"id":5,"title":"Test via Swagger","done":true}