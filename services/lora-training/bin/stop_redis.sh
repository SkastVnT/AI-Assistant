#!/bin/bash
# Quick start script - stops Redis container
echo "Stopping Redis container..."
docker stop ai-assistant-redis
docker rm ai-assistant-redis
echo "Done!"
