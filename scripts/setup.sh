#!/bin/bash
git clone https://github.com/omerbacher/Job-Alert-Agent.git
cd job-alert-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Setup complete. Now create .env file and run start.sh"
