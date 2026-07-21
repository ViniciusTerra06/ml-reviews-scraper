@echo off
REM Registers the scraper as a daily Windows Scheduled Task.
REM Run this once. Re-run to update schedule.
REM Default: daily at 07:00. Edit /ST HH:MM to change.

schtasks /Create /SC DAILY /TN "ML_Reviews_Scraper" ^
  /TR "\"C:\viniciusdev\Projects\Aula-Antonio\Web Scraping\run_scraper.bat\"" ^
  /ST 07:00 /RL LIMITED /F

if %ERRORLEVEL% EQU 0 (
  echo.
  echo Task registered. Verify with: schtasks /Query /TN "ML_Reviews_Scraper"
  echo Trigger manually with: schtasks /Run /TN "ML_Reviews_Scraper"
) else (
  echo.
  echo Failed to register task. See error above.
)
