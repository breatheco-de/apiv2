#!/bin/bash

while ! nc -z $1 $2; do
  echo "Waiting for port $2 on $1 to be available..."
  sleep 2  # Wait 2 seconds before checking again
done

echo "Port $2 on $1 is now available!"
