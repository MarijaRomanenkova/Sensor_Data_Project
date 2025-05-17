#!/bin/sh
# wait-for-mongodb.sh

set -e

host="$1"
shift
cmd="$@"

echo "Waiting for MongoDB at $host:27017..."

until nc -z "$host" 27017; do
  >&2 echo "MongoDB is unavailable - sleeping"
  sleep 2
done

>&2 echo "MongoDB is up - executing command: $cmd"
exec $cmd 
