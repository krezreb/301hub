#!/usr/bin/env bash

# every day rerun init.py
(while true ; do sleep 86400 ; /init.py ; nginx -s reload; done) &

set -e

/init.py

echo Starting Nginx 
nginx -g "daemon off;"