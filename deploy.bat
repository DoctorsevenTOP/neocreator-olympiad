@echo off
chcp 65001 >nul
echo ========================================
echo    NeoCreator - Auto Deploy
echo ========================================
echo.

:: Check Git installation
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git is not installed or not found in PATH
    echo Install Git from https://git-scm.com/
    pause
    exit /b 1
)

:: Check Node.js (optional for some hosting platforms)
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Node.js not found. Some features may be unavailable.
    echo Recommended to install Node.js from https://nodejs.org/
    echo.
)

echo [1] Initializing Git repository...
if not exist .git (
    git init
    echo Git repository initialized
) else (
    echo Git repository already exists
)

echo.
echo [2] Adding files to Git...
git add .
git status

echo.
echo [3] Creating commit...
set /p commit_message="Enter commit message (or press Enter for default): "
if "%commit_message%"=="" set commit_message=Deploy NeoCreator v1.0.0

git commit -m "%commit_message%"

echo.
echo [4] Choose deployment method:
echo    1. GitHub Pages
echo    2. Netlify
echo    3. Vercel
echo    4. Files preparation only
echo.
set /p deploy_choice="Your choice (1-4): "

if "%deploy_choice%"=="1" goto github_pages
if "%deploy_choice%"=="2" goto netlify
if "%deploy_choice%"=="3" goto vercel
if "%deploy_choice%"=="4" goto prepare_only

:github_pages
echo.
echo [GitHub Pages] Setting up deployment...
set /p github_repo="Enter your GitHub repository URL: "
git remote remove origin 2>nul
git remote add origin %github_repo%
git branch -M main
git push -u origin main

echo.
echo [SUCCESS] Project uploaded to GitHub!
echo Next steps:
echo 1. Go to your repository settings on GitHub
echo 2. Open "Pages" section
echo 3. Select source: "Deploy from a branch"
echo 4. Select branch: "main" and folder: "/ (root)"
echo 5. Your site will be available at: https://username.github.io/repository-name/
goto telegram_setup

:netlify
echo.
echo [Netlify] Preparing for deployment...
echo 1. Go to https://netlify.com/
echo 2. Click "Add new site" -> "Deploy manually"
echo 3. Drag project folder to upload area
echo 4. Or connect GitHub repository for automatic deployment
goto telegram_setup

:vercel
echo.
echo [Vercel] Preparing for deployment...
echo 1. Install Vercel CLI: npm i -g vercel
echo 2. Run command: vercel
echo 3. Follow terminal instructions
echo 4. Or go to https://vercel.com/ and connect GitHub repository
goto telegram_setup

:prepare_only
echo.
echo [Preparation] Files ready for deployment!
echo All necessary files are in the current folder.
goto telegram_setup

:telegram_setup
echo.
echo ========================================
echo    Telegram Mini App Setup
echo ========================================
echo.
echo To create Telegram Mini App:
echo.
echo 1. Create bot via @BotFather in Telegram:
echo    /newbot
echo    Enter name: NeoCreator Olympiad Bot
echo    Enter username: your_bot_username_bot
echo.
echo 2. Setup Mini App via @BotFather:
echo    /mybots -^> Select your bot -^> Bot Settings -^> Menu Button
echo    Enter URL: https://your-domain.com/telegram-app.html
echo.
echo 3. Setup bot description:
echo    /setdescription -^> Select bot
echo    Enter: System for creating and taking olympiad tests
echo.
echo 4. Setup commands:
echo    /setcommands -^> Select bot
echo    Enter:
echo    start - Launch application
echo    help - Help and instructions
echo.
echo 5. Update URLs in files:
echo    - Replace "https://your-domain.com/" with your real domain
echo    - Update links in telegram-app.html file
echo.
echo [SUCCESS] Deployment completed!
echo.
echo Your files:
echo - telegram-app.html (Mini App main page)
echo - runner-with-tests.html (test selection and runner)
echo - runner.html (test execution)
echo - runner-external.html (external test upload)
echo - tests/ (ready-made olympiad tests)
echo.
echo Next steps:
echo 1. Upload files to hosting
echo 2. Update URLs in configuration
echo 3. Setup Telegram bot
echo 4. Test the application
echo.
pause
