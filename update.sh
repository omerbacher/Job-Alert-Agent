#!/bin/bash
cd /root/Job-Alert-Agent
git pull
pkill -f "python3 main.py"
source venv/bin/activate
nohup python3 main.py > logs/agent.log 2>&1 &
echo "Bot updated and restarted!"
