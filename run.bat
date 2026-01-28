@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo     Установка приложения
echo ========================================

REM Проверка версии Python
echo Проверка версии Python...
for /f "tokens=2 delims==" %%i in ('python --version 2^>nul') do set "python_version=%%i"
if "%python_version%"=="" (
    echo ОШИБКА: Python не установлен или не добавлен в PATH
    pause
    exit /b 1
)

for /f "tokens=1,2 delims=. " %%a in ("%python_version%") do (
    set "major=%%a"
    set "minor=%%b"
)

if "%major%" NEQ "3" (
    echo ОШИБКА: Требуется Python 3, найдена версия %python_version%
    pause
    exit /b 1
)

if %minor% LSS 13 (
    echo ОШИБКА: Требуется Python 3.13 или выше, найдена версия %python_version%
    echo Пожалуйста, обновите Python до версии 3.13+
    pause
    exit /b 1
)

echo ✓ Python версия %python_version% удовлетворяет требованиям

REM Создание виртуальной среды
echo.
echo Создание виртуальной среды...
python -m venv venv
if errorlevel 1 (
    echo ОШИБКА: Не удалось создать виртуальную среду
    echo Убедитесь, что установлен модуль venv
    pause
    exit /b 1
)
echo ✓ Виртуальная среда создана

REM Активация виртуальной среды и установка зависимостей
echo.
echo Активация виртуальной среды и установка зависимостей...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ОШИБКА: Не удалось активировать виртуальную среду
    pause
    exit /b 1
)

if exist requirements.txt (
    echo Установка библиотек из requirements.txt...
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ОШИБКА: Не удалось установить все зависимости
        echo Проверьте файл requirements.txt
        pause
        exit /b 1
    )
    echo ✓ Зависимости установлены
) else (
    echo Файл requirements.txt не найден, установка зависимостей пропущена
)

REM Создание run.bat файла
echo.
echo Создание файла run.bat...
(
echo @echo off
echo chcp 65001 ^> nul
echo echo ========================================
echo echo     Запуск приложения
echo echo ========================================
echo.
echo REM Активация виртуальной среды
echo call venv\Scripts\activate.bat
echo if errorlevel 1 (
echo     echo ОШИБКА: Не удалось активировать виртуальную среду
echo     pause
echo     exit /b 1
echo )
echo.
echo REM Проверка наличия main.py
echo if not exist "main.py" (
echo     echo ОШИБКА: Файл main.py не найден
echo     echo Убедитесь, что main.py находится в той же папке
echo     pause
echo     exit /b 1
echo )
echo.
echo REM Запуск приложения
echo echo Запуск main.py...
echo python main.py
echo.
echo REM Пауза для просмотра результатов
echo echo.
echo echo Приложение завершило работу
echo pause
) > run.bat

if exist run.bat (
    echo ✓ Файл run.bat создан
) else (
    echo ОШИБКА: Не удалось создать run.bat
    pause
    exit /b 1
)

REM Деактивация виртуальной среды
deactivate

echo.
echo ========================================
echo     Установка завершена успешно!
echo ========================================
echo.
echo Для запуска приложения выполните:
echo   1. run.bat - запуск приложения
echo.
echo Или вручную:
echo   1. venv\Scripts\activate
echo   2. python main.py
echo.
pause