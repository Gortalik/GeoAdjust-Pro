#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug GSI parser
"""

import sys
import os

import pathlib
import re

# Test regex
line = "110009+000000V1 571.08-00000001 572.08-00000001 573..8-00001835 574..8+04587738 83..08-00025316"
print("Line:", repr(line))

words = re.findall(r'(\d+(?:\.\.\d+|\.\d+)?[\+\-][\+\-\d]+[^\d]*)', line)
print("Found words:", words)

for word in words:
    match = re.match(r'(\d+(?:\.\.\d+|\.\d+)?)([\+\-])([\d\.]+)(.*)$', word)
    if match:
        word_code_str = match.group(1)
        sign = match.group(2)
        value_str = match.group(3).strip()
        identifier = match.group(4).strip('.')

        print(f"Word: '{word}' -> code_str: '{word_code_str}', sign: '{sign}', value_str: '{value_str}', identifier: '{identifier}'")

        # Parse
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

        value = float(value_str)
        if decimal_digits > 0:
            value /= (10 ** decimal_digits)
        if sign == '-':
            value = -value

        print(f"  Parsed: code={word_code}, value={value}, decimals={decimal_digits}")