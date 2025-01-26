#!/bin/bash

# Определяем путь к директории скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Активируем виртуальное окружение
source "$SCRIPT_DIR/.venv/bin/activate"

# Запускаем main.py
python "$SCRIPT_DIR/main.py"

# Деактивируем виртуальное окружение
# deactivate
