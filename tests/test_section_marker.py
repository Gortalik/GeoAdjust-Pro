#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест парсинга маркера секций
"""

# Тестовая строка маркера секций
test_line = "410001+?......1"

import re
words = re.findall(r'(\d+(?:\.\.\d+|\.\d+)?[\+\-][\+\-\d]+[^\s]*)', test_line)
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

        # Парсинг номера слова
        if '..' in word_code_str:
            parts = word_code_str.split('..')
            word_code = int(parts[0])
            decimal_digits = int(parts[1]) if parts[1] else 0
        elif '.' in word_code_str:
            parts = word_code_str.split('.')
            word_code = int(parts[0])
            decimal_digits = int(parts[1]) if parts[1].isdigit() else len(parts[1])
        else:
            word_code = int(word_code_str[:2])  # Первые 2 цифры для многоразрядных кодов
            decimal_digits = 0

        print(f"  word_code: {word_code}")
        print(f"  decimal_digits: {decimal_digits}")

        # Значение
        try:
            value = float(value_str) if value_str else 0.0
            if sign == '-':
                value = -value
        except ValueError:
            value = 0.0

        print(f"  value: {value}")
        print(f"  word_code == 41: {word_code == 41}")