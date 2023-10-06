#!/bin/bash

access_key="<your key here>"
secret_key="<your secret here>"

#the secret must be decoded from base64 first
signing_key=$(echo $secret_key|openssl enc -d -base64)
echo "Signing key:"
echo $signing_key

#information for 
host="https://api.testnet.paradigm.trade"
path="/v1/echo"
method="GET"
payload=""

#timestamp for current date with seconds and nanoseconds. 13 digits altogether
timestamp="$(date +%s%N | cut -b1-13)"

#the message the needs to be signed is the timestamp + method (uppercase) + API path + payload ("" if no payload)
message="$timestamp\n$method\n$path\n$payload"

echo "message:"
echo -ne $message

#sign the message using the signing key (decoded secret) and convert this signature to base64. if using echo, besure to use -ne!
signature=$(echo -ne $message | openssl sha256 -binary -hmac "$signing_key" | base64)
echo "signature:"
echo $signature

#assemble curl with timestamp, signature and authorization headers
curl -X $method "$host$path" \
  --data-binary "$payload" \
  -H "Paradigm-API-Timestamp: $timestamp" \
  -H "Paradigm-API-Signature: $signature" \
  -H "Authorization: Bearer $access_key" \
  -H "Accept: application/json" 
