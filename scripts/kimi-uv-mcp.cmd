@echo off
setlocal EnableExtensions
set "UV_EXE="
if defined UV_EXE if exist "%UV_EXE%" goto run
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV_EXE for %%I in (uv.exe) do if not "%%~$PATH:I"=="" set "UV_EXE=%%~$PATH:I"
if not defined UV_EXE (
  >&2 echo uv.exe not found. Install uv or add %%USERPROFILE%%\.local\bin to PATH.
  exit /b 9009
)
:run
set "KIMI_RUNTIME_HOME=%KIMI_CODE_HOME%"
if not defined KIMI_RUNTIME_HOME set "KIMI_RUNTIME_HOME=%USERPROFILE%\.kimi-code"
set "UV_PROJECT_ENVIRONMENT=%KIMI_RUNTIME_HOME%\cache\uv-projects\agent-handoff"
"%UV_EXE%" run --project "%~dp0.." python %*
