Write-Host "🚀 Starting Elsie Development Environment" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Start the database first
Write-Host "🗄️ Starting database..." -ForegroundColor Yellow
docker-compose -f docker-compose.db.yml up -d

# Wait for database to be healthy
Write-Host "⏳ Waiting for database to be ready..." -ForegroundColor Yellow
do {
    Start-Sleep 2
    $dbStatus = docker-compose -f docker-compose.db.yml ps | Select-String "healthy"
    if (-not $dbStatus) {
        Write-Host "   ⏳ Database starting up..." -ForegroundColor Cyan
    }
} while (-not $dbStatus)
Write-Host "✅ Database is ready!" -ForegroundColor Green

# Start the application services
Write-Host "🤖 Starting application services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "✅ Development environment is ready!" -ForegroundColor Green
Write-Host "📊 Services:" -ForegroundColor Cyan
Write-Host "   • Database: http://localhost:5433" -ForegroundColor White
Write-Host "   • AI Agent: http://localhost:8000" -ForegroundColor White
Write-Host "   • Discord Bot: Running" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Management commands:" -ForegroundColor Cyan
Write-Host "   • Stop apps only: docker-compose down" -ForegroundColor White
Write-Host "   • Stop database: docker-compose -f docker-compose.db.yml down" -ForegroundColor White
Write-Host "   • Stop everything: docker-compose down; docker-compose -f docker-compose.db.yml down" -ForegroundColor White
Write-Host "   • Rebuild apps: docker-compose down; docker-compose up --build -d" -ForegroundColor White 