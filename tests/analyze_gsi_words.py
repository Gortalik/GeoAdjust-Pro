#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ всех типов слов в GSI файле
"""

import sys
from pathlib import Path
import re

def analyze_gsi_words():
    """Анализ всех слов в GSI файле"""
    gsi_file = Path("test_real_mes/b_g/niv/GRO2209.GSI")
    
    word_counts = {}
    word_examples = {}
    
    with open(gsi_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            # Ищем все слова в строке
            words = re.findall(r'(\d+(?:\.\.\d+|\.\d+)?[\+\-][\+\-\d]+[^\s]*)', line)
            
            for word in words:
                # Парсинг номера слова
                if '..' in word:
                    parts = word.split('..')
                    word_code = int(parts[0])
                elif '.' in word:
                    parts = word.split('.')
                    word_code = int(parts[0])
                else:
                    word_code = int(re.match(r'(\d+)', word).group(1))
                
                # Подсчет
                if word_code not in word_counts:
                    word_counts[word_code] = 0
                    word_examples[word_code] = []
                
                word_counts[word_code] += 1
                
                # Сохраняем примеры (не более 3 на тип)
                if len(word_examples[word_code]) < 3:
                    word_examples[word_code].append(f"Line {line_num}: {word}")
    
    print("Анализ слов в GSI файле:")
    print(f"Всего уникальных типов слов: {len(word_counts)}")
    print()
    
    # Сортируем по частоте
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    
    for word_code, count in sorted_words[:20]:  # Первые 20 наиболее частых
        print(f"Слово {word_code}: {count} раз")
        for example in word_examples[word_code]:
            print(f"  {example}")
        print()

if __name__ == "__main__":
    analyze_gsi_words()