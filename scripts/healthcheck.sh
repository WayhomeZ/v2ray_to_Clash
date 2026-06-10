#!/bin/bash
echo "Waiting for Subconverter to start..."
timeout=30
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -s http://localhost:25500/version > /dev/null; then
        echo "Subconverter is up and running!"
        exit 0
    fi
    sleep 1
    elapsed=$((elapsed+1))
done
echo "Subconverter failed to start within $timeout seconds."
exit 1
