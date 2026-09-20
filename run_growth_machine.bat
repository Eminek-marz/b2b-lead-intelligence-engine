@echo off
title Complete B2B Growth Machine
cd /d "%~dp0"

echo ========================================================
echo        THE COMPLETE B2B LEAD & OUTREACH MACHINE         
echo ========================================================
echo.
echo Step 1: Investigating and Enriching Leads...
.venv\Scripts\python.exe lead_engine.py --file sample_leads.csv

echo.
echo Step 2: Generating Automated 3-Step Cold Email Campaigns...
.venv\Scripts\python.exe campaign_builder.py

echo.
echo ========================================================
echo  All leads enriched & campaign files created in \exports!
echo ========================================================
pause
