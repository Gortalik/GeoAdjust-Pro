#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест парсинга GSI слов
"""

import sys
from pathlib import Path


from geoadjust.io.formats.gsi import GSIParser

# Тест парсинга слова
parser = GSIParser()

# Тестовая строка
test_line = "110002+00R52267 83..58+00000000"

import re
# Старое регулярное выражение
words_old = re.findall(r'(\d+(?:\.\.\d+|\.\d+)?[\+\-][\+\-\d]+[^\d]*)', test_line)
print(f"Старое regex - слова: {words_old}")

# Новое регулярное выражение
words_new = re.findall(r'(\d+(?:\.\.\d+|\.\d+)?[\+\-][\+\-\d]+[^\s]*)', test_line)
print(f"Новое regex - слова: {words_new}")

words = words_new
print(f"Найденные слова: {words}")

for word in words:
    print(f"\nПарсинг слова: {word}")
    match = re.match(r'(\d+(?:\.\.\d+|\.\d+)?)([\+\-])([\d\.]+)(.*)$', word)
    if match:
        word_code_str = match.group(1)
        sign = match.group(2)
        value_str = match.group(3).strip()
        identifier = match.group(4).strip('.')

        print(f"  word_code_str: {word_code_str}")
        print(f"  sign: {sign}")
        print(f"  value_str: {value_str}")
        print(f"  identifier: '{identifier}'")

        # Парсинг номера слова (исправленная логика)
        if '..' in word_code_str:
            parts = word_code_str.split('..')
            word_code = int(parts[0])
            decimal_digits = int(parts[1]) if parts[1] else 0
        elif '.' in word_code_str:
            parts = word_code_str.split('.')
            word_code = int(parts[0])
            decimal_digits = int(parts[1]) if parts[1].isdigit() else len(parts[1])
        else:
            word_code = int(word_code_str)
            decimal_digits = 0

        print(f"  word_code: {word_code}")
        print(f"  decimal_digits: {decimal_digits}")

        # Проверка условия
        print(f"  word_code starts with 11: {str(word_code).startswith('11')}")
        print(f"  identifier exists: {bool(identifier)}")