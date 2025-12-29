@echo off
echo ============================================================
echo   Checking GPU Status for Stable Diffusion
echo ============================================================
echo.

echo [1] Checking NVIDIA GPU...
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu --format=csv,noheader
echo.

echo [2] Checking if SD WebUI is using GPU...
curl -s http://127.0.0.1:7861/sdapi/v1/cmd-flags
echo.
echo.

echo [3] Testing simple generation...
echo Generating 512x512 image with 10 steps...
python -c "import requests, time; start=time.time(); r=requests.post('http://127.0.0.1:7861/sdapi/v1/txt2img', json={'prompt':'test','steps':10,'width':512,'height':512}, timeout=120); elapsed=time.time()-start; print(f'\n✅ Generation time: {elapsed:.1f}s'); print('⚠️ WARNING: Too slow!' if elapsed > 30 else '✅ Speed OK')"
echo.

echo ============================================================
echo   Analysis Complete
echo ============================================================
pause
