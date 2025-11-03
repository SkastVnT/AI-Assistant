# =============================================================================
#  PowerShell Script Wrapper để chạy Dual Model Speech-to-Text
#  Tự động kích hoạt virtual environment và chạy script
# =============================================================================

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "     DUAL MODEL SPEECH-TO-TEXT: Whisper + PhoWhisper + Gemini AI" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Kiểm tra virtual environment
if (-not (Test-Path "s2t\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment không tìm thấy!" -ForegroundColor Red
    Write-Host "Vui lòng chạy: python -m venv s2t" -ForegroundColor Yellow
    pause
    exit 1
}

# Kích hoạt virtual environment
Write-Host "[INFO] Kích hoạt virtual environment..." -ForegroundColor Green
& ".\s2t\Scripts\Activate.ps1"

Write-Host "[INFO] Bắt đầu xử lý audio..." -ForegroundColor Green
Write-Host ""

# Chạy script chính
& ".\s2t\Scripts\python.exe" run_dual_models.py

# Kiểm tra kết quả
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Hoàn thành! Kết quả đã được lưu vào thư mục ./result/" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Red
    Write-Host "[ERROR] Có lỗi xảy ra! Mã lỗi: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "================================================================================" -ForegroundColor Red
}

Write-Host ""
Write-Host "Nhấn phím bất kỳ để đóng..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
