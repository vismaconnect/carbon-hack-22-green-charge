set ENV_DIR=env\
set PY_VERSON=3.9


if exist env\ (
  REM Delete existing virtual environment
  rd /s /q %ENV_DIR%
) 

REM Create new virtual environment
py -%PY_VERSON% -m venv env
set PYTHON_VENV=%ENV_DIR%\Scripts\python.exe

%PYTHON_VENV% -m pip install --upgrade pip
%PYTHON_VENV% -m pip install --upgrade -r .\requirements.txt
REM %PYTHON_VENV% -m pip install --editable .
%PYTHON_VENV% -m pip install pycodestyle
%PYTHON_VENV% -m pip install pylint
%PYTHON_VENV% -m pip list

