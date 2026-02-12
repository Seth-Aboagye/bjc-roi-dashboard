#!/usr/bin/env bash
set -e

# Render provides PORT; Streamlit must bind to 0.0.0.0 and that port.
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
