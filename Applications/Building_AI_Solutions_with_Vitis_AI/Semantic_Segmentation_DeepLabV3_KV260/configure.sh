#!/bin/bash

# Script to reload the Kria KV260 accelerator with a specific application
# Description:
#   - Unloads the currently running Vitis-AI application
#   - Loads the kv260-benchmark-b4096 application

echo "Unloading current Kria accelerator application..."
sudo xmutil unloadapp

echo "Loading kv260-benchmark-b4096 application..."
sudo xmutil loadapp kv260-benchmark-b4096

echo "Accelerator reload complete."