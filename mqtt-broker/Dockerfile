FROM eclipse-mosquitto:latest

RUN apk update && apk add --no-cache openssl

# Generate SSL # TODO: Use elliptic curves
# RUN mkdir -p /mosquitto/certs
WORKDIR /mosquitto/certs

# Generate CA
RUN openssl genrsa -out ca.key 2048
RUN openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/CN=MQTT-CA"

# Generate Server Key & Certificate
RUN openssl genrsa -out server.key 2048
RUN openssl req -new -key server.key -out server.csr -subj "/CN=mosquitto"
RUN openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650
