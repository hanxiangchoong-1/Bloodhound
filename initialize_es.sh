#!/bin/bash

# Read environment variables
ES_HOST=${ELASTIC_CLOUD_ENDPOINT}
USERNAME=${ELASTIC_USERNAME}
PASSWORD=${ELASTIC_PASSWORD}

# Remove trailing slash from ES_HOST if it exists
ES_HOST=$(echo $ES_HOST | sed 's:/*$::')

# Print the environment variables for debugging purposes
echo "ES_HOST: $ES_HOST"
echo "USERNAME: $USERNAME"

# Test endpoint accessibility
echo "Testing Elasticsearch endpoint accessibility..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -u $USERNAME:$PASSWORD -X GET "$ES_HOST")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | awk -F ":" '{print $2}')
RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" -eq 200 ]; then
  echo "Elasticsearch endpoint is accessible."
else
  echo "Failed to access Elasticsearch endpoint. HTTP response code: $HTTP_CODE"
  echo "Response body: $RESPONSE_BODY"
  exit 1
fi

# Function to create index with alias
create_index() {
  INDEX=$1
  ALIAS=$2
  RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -u $USERNAME:$PASSWORD -X PUT "$ES_HOST/$INDEX" -H 'Content-Type: application/json' -d'{
    "aliases": {
      "'$ALIAS'": {
        "is_write_index": true
      }
    }
  }')

  # Extract HTTP status code
  HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | awk -F ":" '{print $2}')
  # Extract response body
  RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

  if [ "$HTTP_CODE" -eq 200 ]; then
    echo "Successfully created index $INDEX with alias $ALIAS"
  else
    echo "Failed to create index $INDEX with alias $ALIAS. HTTP response code: $HTTP_CODE"
    echo "Response body: $RESPONSE_BODY"
  fi
}

# Create indices with aliases
create_index "webcrawler_content-000001" "webcrawler_content"
create_index "webcrawler_app_logs-000001" "webcrawler_app_logs"
create_index "webcrawler_metrics-000001" "webcrawler_metrics"