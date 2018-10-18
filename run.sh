#!/usr/bin/env bash

trap "exit" INT TERM
trap "kill -9 0" EXIT

# every day rerun init.py
(while true ; do sleep 86400 ; setup ; done) &

set -e

setup

echo Starting Nginx 
nginx -g "daemon off;"