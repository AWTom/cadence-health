#!/bin/bash
# Lambda entrypoint: the Lambda Web Adapter layer (/opt/bootstrap) proxies
# Function URL requests to this uvicorn server.
exec python -m uvicorn --port="$PORT" api.main:app
