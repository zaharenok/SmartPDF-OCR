# SmartPDF-OCR Makefile

.PHONY: help install install-dev test clean lint format check setup example

# Default target
help:
	@echo "SmartPDF-OCR - Доступные команды:"
	@echo ""
	@echo "setup          - Полная настройка проекта"
	@echo "install        - Установка зависимостей"
	@echo "install-dev    - Установка зависимостей для разработки"
	@echo "test           - Запуск тестов"
	@echo "lint           - Проверка кода (flake8)"
	@echo "format         - Форматирование кода (black)"
	@echo "check          - Проверка типов (mypy)"
	@echo "example        - Запуск примеров"
	@echo "clean          - Очистка временных файлов"
	@echo "run            - Запуск с тестовым PDF"
	@echo ""

# Полная настройка проекта
setup: install
	@echo "🚀 Настройка проекта завершена!"
	@echo ""
	@echo "Для запуска используйте:"
	@echo "  python main.py your_document.pdf"
	@echo ""
	@echo "Или запустите примеры:"
	@echo "  make example"

# Установка основных зависимостей
install:
	@echo "📦 Установка зависимостей..."
	pip install -r requirements.txt

# Установка зависимостей для разработки
install-dev: install
	@echo "🛠️  Установка dev зависимостей..."
	pip install pytest pytest-cov black flake8 mypy

# Запуск тестов (когда будут созданы)
test:
	@echo "🧪 Запуск тестов..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "⚠️  Директория tests не найдена. Создайте тесты для запуска."; \
	fi

# Проверка кода
lint:
	@echo "🔍 Проверка кода..."
	flake8 *.py --max-line-length=100 --ignore=E203,W503

# Форматирование кода
format:
	@echo "✨ Форматирование кода..."
	black *.py --line-length=100

# Проверка типов
check:
	@echo "🔎 Проверка типов..."
	mypy *.py --ignore-missing-imports

# Запуск примеров
example:
	@echo "📚 Запуск примеров использования..."
	python example_usage.py

# Очистка временных файлов
clean:
	@echo "🧹 Очистка временных файлов..."
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf output/
	rm -rf temp/
	rm -rf cache/
	rm -rf *.log
	@echo "✅ Очистка завершена"

# Быстрый запуск с тестовым PDF
run:
	@echo "🏃 Запуск SmartPDF-OCR..."
	@if [ -f "test.pdf" ]; then \
		python main.py test.pdf --verbose; \
	else \
		echo "❌ Файл test.pdf не найден."; \
		echo "   Создайте тестовый PDF файл или укажите путь:"; \
		echo "   python main.py путь/к/вашему/файлу.pdf"; \
	fi

# Создание тестового PDF (требует дополнительных библиотек)
create-test-pdf:
	@echo "📄 Создание тестового PDF..."
	@python -c "
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os

if not os.path.exists('test.pdf'):
    c = canvas.Canvas('test.pdf', pagesize=letter)
    c.drawString(100, 750, 'Тестовый PDF документ')
    c.drawString(100, 700, 'Страница 1 - Простой текст')
    c.drawString(100, 650, 'Этот файл создан для тестирования SmartPDF-OCR')
    c.showPage()
    c.drawString(100, 750, 'Страница 2 - Дополнительный контент')
    c.drawString(100, 700, 'Здесь можно разместить таблицы и изображения')
    c.save()
    print('✅ Тестовый PDF создан: test.pdf')
else:
    print('ℹ️  Файл test.pdf уже существует')
" 2>/dev/null || echo "⚠️  Для создания тестового PDF установите: pip install reportlab"

# Показать статус проекта
status:
	@echo "📊 Статус проекта SmartPDF-OCR:"
	@echo ""
	@echo "📁 Структура файлов:"
	@ls -la *.py | head -10
	@echo ""
	@echo "📦 Python версия:"
	@python --version
	@echo ""
	@echo "📋 Зависимости:"
	@pip list | grep -E "(PyMuPDF|pytesseract|easyocr|Pillow)" || echo "⚠️  Основные зависимости не установлены"

# Быстрая проверка всего
check-all: lint check
	@echo "✅ Все проверки пройдены!"