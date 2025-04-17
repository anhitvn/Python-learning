#!/bin/bash
# Start supervisor
supervisord -c supervisor.conf

# Tail logs
tail -f ./logs/db-monitor-*.log./
