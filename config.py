import os
from pathlib import Path

class Config:
    # Основные настройки
    OUTPUT_DIR = "output"
    TEMP_DIR = "temp"
    CACHE_DIR = "cache"
    
    # PDF настройки
    PDF_DPI = 300  # DPI для конвертации PDF в изображения
    PDF_FORMAT = "PNG"  # Формат изображений
    
    # OCR настройки
    TESSERACT_CONFIG = "--oem 3 --psm 6"  # Конфигурация Tesseract
    TESSERACT_LANG = "rus+eng"  # Языки для распознавания
    
    # EasyOCR настройки
    EASYOCR_LANGS = ['ru', 'en']  # Языки для EasyOCR
    EASYOCR_GPU = False  # Использовать GPU (если доступно)
    
    # Markdown настройки
    MARKDOWN_EXTENSIONS = ['tables', 'fenced_code', 'toc']
    
    # Настройки обработки
    MAX_WORKERS = 4  # Количество параллельных процессов
    MIN_TEXT_LENGTH = 10  # Минимальная длина текста для считывания страницы успешной
    
    # Настройки качества OCR
    OCR_CONFIDENCE_THRESHOLD = 60  # Минимальная уверенность OCR (0-100)
    
    # Логирование
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @staticmethod
    def ensure_dirs():
        """Создает необходимые директории если их нет"""
        dirs = [Config.OUTPUT_DIR, Config.TEMP_DIR, Config.CACHE_DIR]
        for dir_path in dirs:
            Path(dir_path).mkdir(exist_ok=True)
    
    @staticmethod
    def get_tesseract_path():
        """Определяет путь к Tesseract в зависимости от ОС"""
        import platform
        system = platform.system()
        
        if system == "Windows":
            # Обычные пути установки на Windows
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
        elif system == "Darwin":  # macOS
            possible_paths = [
                "/usr/local/bin/tesseract",
                "/opt/homebrew/bin/tesseract",
                "/usr/bin/tesseract"
            ]
        else:  # Linux
            possible_paths = [
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract"
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Если не найден, вернуть стандартное имя (должно работать если в PATH)
        return "tesseract"

# Настройки для различных типов документов
DOCUMENT_TYPES = {
    "text": {
        "ocr_config": "--oem 3 --psm 6",
        "preprocessing": ["deskew", "noise_removal"]
    },
    "table": {
        "ocr_config": "--oem 3 --psm 6",
        "preprocessing": ["deskew", "line_detection"]
    },
    "mixed": {
        "ocr_config": "--oem 3 --psm 3",
        "preprocessing": ["deskew", "noise_removal", "contrast_enhancement"]
    }
}