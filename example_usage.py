#!/usr/bin/env python3
"""
Примеры использования SmartPDF-OCR

Этот файл демонстрирует различные способы использования системы
как через командную строку, так и программно.
"""

import os
import sys
from main import SmartPDFOCR

def example_basic_usage():
    """Базовый пример использования"""
    
    # Путь к PDF файлу (замените на реальный)
    pdf_path = "example_document.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️  Файл {pdf_path} не найден. Создайте тестовый PDF файл.")
        return
    
    print("🚀 Запуск базовой обработки...")
    
    # Создание экземпляра процессора
    processor = SmartPDFOCR(pdf_path=pdf_path)
    
    # Проверка входных данных
    if not processor.validate_input():
        print("❌ Ошибка валидации входных данных")
        return
    
    # Обработка PDF
    result = processor.process_pdf()
    
    # Вывод результатов
    processor.print_summary(result)

def example_custom_settings():
    """Пример с настраиваемыми параметрами"""
    
    pdf_path = "example_document.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️  Файл {pdf_path} не найден. Создайте тестовый PDF файл.")
        return
    
    print("🔧 Запуск с настраиваемыми параметрами...")
    
    # Создание процессора с настройками
    processor = SmartPDFOCR(
        pdf_path=pdf_path,
        output_dir="./custom_output",     # Своя директория вывода
        language="rus+eng",               # Русский и английский
        dpi=600,                          # Высокое разрешение
        max_workers=8                     # Больше потоков
    )
    
    if not processor.validate_input():
        print("❌ Ошибка валидации входных данных")
        return
    
    result = processor.process_pdf()
    processor.print_summary(result)

def example_batch_processing():
    """Пример пакетной обработки нескольких файлов"""
    
    # Список PDF файлов для обработки
    pdf_files = [
        "document1.pdf",
        "document2.pdf", 
        "document3.pdf"
    ]
    
    print("📚 Запуск пакетной обработки...")
    
    results = []
    
    for pdf_file in pdf_files:
        if not os.path.exists(pdf_file):
            print(f"⚠️  Пропускаем {pdf_file} - файл не найден")
            continue
        
        print(f"\n📄 Обработка {pdf_file}...")
        
        processor = SmartPDFOCR(
            pdf_path=pdf_file,
            output_dir=f"./batch_output/{os.path.splitext(pdf_file)[0]}"
        )
        
        if processor.validate_input():
            result = processor.process_pdf()
            results.append({
                'file': pdf_file,
                'result': result
            })
            processor.print_summary(result)
        else:
            print(f"❌ Ошибка валидации для {pdf_file}")
    
    # Общая статистика
    print("\n" + "="*60)
    print("ОБЩАЯ СТАТИСТИКА ПАКЕТНОЙ ОБРАБОТКИ")
    print("="*60)
    
    total_files = len(results)
    successful_files = len([r for r in results if r['result']['success']])
    
    print(f"📁 Всего файлов: {total_files}")
    print(f"✅ Успешно обработано: {successful_files}")
    print(f"📊 Процент успеха: {(successful_files/total_files*100):.1f}%")
    
    for result in results:
        status = "✅" if result['result']['success'] else "❌"
        print(f"{status} {result['file']}")

def example_error_handling():
    """Пример обработки ошибок"""
    
    print("🛠️  Демонстрация обработки ошибок...")
    
    # Попытка обработать несуществующий файл
    try:
        processor = SmartPDFOCR(pdf_path="nonexistent.pdf")
        
        if not processor.validate_input():
            print("❌ Ожидаемая ошибка: файл не найден")
        
    except Exception as e:
        print(f"🚫 Обработана ошибка: {e}")
    
    # Попытка обработать не-PDF файл
    try:
        # Создаем тестовый не-PDF файл
        with open("test.txt", "w") as f:
            f.write("This is not a PDF")
        
        processor = SmartPDFOCR(pdf_path="test.txt")
        
        if not processor.validate_input():
            print("❌ Ожидаемая ошибка: файл не является PDF")
        
        # Удаляем тестовый файл
        os.remove("test.txt")
        
    except Exception as e:
        print(f"🚫 Обработана ошибка: {e}")
        if os.path.exists("test.txt"):
            os.remove("test.txt")

def example_programmatic_access():
    """Пример программного доступа к результатам"""
    
    pdf_path = "example_document.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"⚠️  Файл {pdf_path} не найден для демонстрации")
        return
    
    print("💻 Программный доступ к результатам...")
    
    processor = SmartPDFOCR(pdf_path=pdf_path)
    
    if not processor.validate_input():
        return
    
    result = processor.process_pdf()
    
    if result['success']:
        stats = result['statistics']
        outputs = result['outputs']
        
        print(f"\n📊 Детальная статистика:")
        print(f"   Общий текст: {stats['total_text_length']} символов")
        print(f"   Время обработки: {stats['total_processing_time']:.2f} сек")
        
        print(f"\n📄 Доступные выходные форматы:")
        for format_name in outputs.keys():
            print(f"   - {format_name}")
        
        # Пример работы с текстом
        text_only = outputs.get('text_only', '')
        if text_only:
            words = len(text_only.split())
            print(f"\n📝 Извлеченный текст содержит {words} слов")
            
            # Первые 200 символов
            preview = text_only[:200] + "..." if len(text_only) > 200 else text_only
            print(f"\n👀 Предварительный просмотр:")
            print(f"   {preview}")

def main():
    """Главная функция с меню примеров"""
    
    print("🤖 SmartPDF-OCR - Примеры использования")
    print("="*50)
    
    examples = {
        "1": ("Базовое использование", example_basic_usage),
        "2": ("Настраиваемые параметры", example_custom_settings),
        "3": ("Пакетная обработка", example_batch_processing),
        "4": ("Обработка ошибок", example_error_handling),
        "5": ("Программный доступ", example_programmatic_access)
    }
    
    print("\nДоступные примеры:")
    for key, (description, _) in examples.items():
        print(f"  {key}. {description}")
    
    print("\n0. Запустить все примеры")
    print("q. Выход")
    
    choice = input("\nВыберите пример (1-5, 0, q): ").strip()
    
    if choice == "q":
        print("👋 До свидания!")
        return
    
    if choice == "0":
        print("\n🚀 Запуск всех примеров...\n")
        for description, func in examples.values():
            print(f"\n{'='*20} {description} {'='*20}")
            try:
                func()
            except Exception as e:
                print(f"❌ Ошибка в примере '{description}': {e}")
            print("="*60)
    
    elif choice in examples:
        description, func = examples[choice]
        print(f"\n🚀 Запуск примера: {description}")
        try:
            func()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    else:
        print("❌ Неверный выбор")

if __name__ == "__main__":
    main()