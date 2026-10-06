@echo off
set VENV=c:\Users\Aron\Desktop\Codes\url-pattern-recognition\PolyMerge\ml_engine\.venv\Scripts\python.exe
set TESTS=c:\Users\Aron\Desktop\Codes\url-pattern-recognition\PolyMerge\ml_engine\tests\test_sprint6_frontend.py
set ROOTDIR=c:\Users\Aron\Desktop\Codes\url-pattern-recognition\PolyMerge\ml_engine
%VENV% -m pytest %TESTS% --tb=short -v --rootdir %ROOTDIR% --override-ini="addopts=" 2>&1
