#!/usr/bin/env python3
"""
Setup script for SmartPDF-OCR
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="smartpdf-ocr",
    version="1.0.0",
    author="SmartPDF-OCR Team",
    author_email="contact@smartpdf-ocr.com",
    description="Intelligent PDF text extraction system with multi-OCR support and markdown output",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/smartpdf-ocr/smartpdf-ocr",
    packages=find_packages(),
    py_modules=[
        'main',
        'config', 
        'utils',
        'pdf_processor',
        'ocr_engine', 
        'markdown_converter',
        'page_merger'
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License", 
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Text Processing",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0", 
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.812"
        ],
        "gpu": [
            "torch>=1.9.0",
            "torchvision>=0.10.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "smartpdf-ocr=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "pdf", "ocr", "text-extraction", "markdown", "tesseract", 
        "easyocr", "document-processing", "llm", "ai"
    ],
    project_urls={
        "Bug Reports": "https://github.com/smartpdf-ocr/smartpdf-ocr/issues",
        "Source": "https://github.com/smartpdf-ocr/smartpdf-ocr",
        "Documentation": "https://github.com/smartpdf-ocr/smartpdf-ocr/wiki",
    },
)