@echo off
echo 🤖 Starting Discord Bot (Windows)...

REM Navigate to discord_bot directory
cd /d "%~dp0..\..\discord_bot"

REM Copy .env file from parent directory if it exists
if exist "..\.env" (
    echo Copying .env file...
    copy "..\.env" ".env" >nul
)

REM Start the Discord bot
echo Starting Discord bot with Go...
go run main.go

pause 