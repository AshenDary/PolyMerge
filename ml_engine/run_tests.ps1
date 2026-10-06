$venv = 'C:\Users\Aron\Desktop\Codes\url-pattern-recognition\.venv\Scripts\python.exe'
if (-not (Test-Path $venv)) {
    $venv = 'C:\Users\Aron\Desktop\Codes\url-pattern-recognition\PolyMerge\.uv-cache\archive-v0\cqI_3Gw55Dnp2BVx\Scripts\python.exe'
}
& $venv -m pytest tests/test_sprint6_frontend.py --tb=short -q 2>&1
