@echo off
REM Wrapper called by Windows Task Scheduler.
REM Redirects stdout/stderr into the rolling log file.
cd /d "C:\viniciusdev\Projects\Aula-Antonio\Web Scraping"
py -3 src\scraper.py >> logs\scraper.log 2>&1
exit /b %ERRORLEVEL%
