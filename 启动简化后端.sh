#!/bin/bash
cd /Users/yuan/Coding/Qcode/backend_server
python3 -m pip install -q --user fastapi uvicorn
python3 -m uvicorn main_simple:app --host 0.0.0.0 --port 8000
