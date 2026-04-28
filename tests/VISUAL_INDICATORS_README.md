# VISUAL_INDICATORS_README.md
# Визуальные индикаторы для GeoAdjust Pro GUI

## Обзор

Файл `visual_indicators.py` содержит набор функций для создания визуальных индикаторов различных элементов интерфейса без использования внешних иконок. Все индикаторы используют Unicode символы и стандартную цветовую схему Qt.

## Типы индикаторов

### 1. Индикаторы типов пунктов (Point Types)

| Тип пункта | Символ | Цвет | Описание |
|------------|--------|------|----------|
| FIXED (опорный) | ● | Синий (#2E86C1) | Заполненный круг |
| FREE (свободный) | ○ | Красный (#E74C3C) | Пустой круг |
| APPROXIMATE (приближенный) | △ | Оранжевый (#F39C12) | Треугольник |

**Использование:**
```python
indicator = VisualIndicator.create_point_type_indicator("FIXED")
# Возвращает QWidget с символом и текстом "опорный"
```

### 2. Индикаторы типов измерений (Observation Types)

| Тип измерения | Символ | Цвет | Описание |
|---------------|--------|------|----------|
| direction (направление) | → | Зеленый (#27AE60) | Стрелка вправо |
| zenith_angle (зенитный угол) | ∠ | Фиолетовый (#8E44AD) | Угловой символ |
| slope_distance (наклонное расстояние) | ↗ | Оранжевый (#E67E22) | Диагональная стрелка |
| horizontal_distance (горизонтальное расстояние) | → | Голубой (#3498DB) | Стрелка вправо |
| height_diff (превышение) | ↕ | Пурпурный (#9B59B6) | Вертикальная стрелка |

**Использование:**
```python
indicator = VisualIndicator.create_observation_type_indicator("direction")
# Возвращает QWidget с символом и текстом "направление"
```

### 3. Индикаторы станций (Stations)

| Элемент | Символ | Цвет | Описание |
|---------|--------|------|----------|
| Станция | 📐 | Темно-синий (#2C3E50) | Теодолит |

**Использование:**
```python
station_data = {"session_id": "ST001", "point_id": "P001"}
indicator = VisualIndicator.create_station_indicator(station_data)
```

### 4. Индикаторы типов ходов (Traverses)

| Тип хода | Символ | Цвет | Описание |
|----------|--------|------|----------|
| taheometric (тахеометрия) | ⊕ | Зеленый (#27AE60) | Крест в круге |
| leveling (нивелирование) | ━ | Фиолетовый (#8E44AD) | Горизонтальная линия |
| gnss (GNSS) | ◎ | Голубой (#3498DB) | Круг с точкой |

**Использование:**
```python
traverse_data = {"num_stations": 5, "length": 1250.5}
indicator = VisualIndicator.create_traverse_indicator("taheometric", traverse_data)
```

### 5. Индикаторы статуса (Status Indicators)

| Статус | Символ | Цвет | Описание |
|--------|--------|------|----------|
| success (успех) | ✓ | Зеленый (#27AE60) | Галочка |
| warning (предупреждение) | ⚠ | Оранжевый (#F39C12) | Знак предупреждения |
| error (ошибка) | ✗ | Красный (#E74C3C) | Крест |
| processing (обработка) | ⟳ | Голубой (#3498DB) | Круговые стрелки |

**Использование:**
```python
indicator = VisualIndicator.create_status_indicator("success", "Операция выполнена")
```

## Цветовая схема

Полная цветовая схема доступна через:
```python
colors = VisualIndicator.get_color_scheme()
# Возвращает словарь с цветами для всех типов элементов
```

## Карта символов

Все используемые Unicode символы доступны через:
```python
symbols = VisualIndicator.get_symbol_map()
# Возвращает словарь с символами для всех типов элементов
```

## Интеграция в существующий код

### В таблицах пунктов
В `points_table.py` заменить текстовое отображение типа на индикатор:
```python
from geoadjust.gui.visual_indicators import VisualIndicator

# Вместо текста "FIXED" использовать:
indicator_widget = VisualIndicator.create_point_type_indicator(point_type)
table.setCellWidget(row, column, indicator_widget)
```

### В таблицах измерений
В `observations_table.py` добавить индикатор типа:
```python
indicator_widget = VisualIndicator.create_observation_type_indicator(obs_type)
table.setCellWidget(row, column, indicator_widget)
```

### В дереве ходов
В `main_window.py` в методе `_update_traverses_tree` использовать:
```python
indicator_widget = VisualIndicator.create_traverse_indicator("taheometric", traverse_data)
tree_item.setData(0, Qt.UserRole, indicator_widget)
```

### В статусной строке
Для отображения статуса операций:
```python
status_indicator = VisualIndicator.create_status_indicator("processing", "Выполняется уравнивание...")
statusBar().addWidget(status_indicator)
```

## Шрифты и размеры

- **Основной текст:** Arial, 8pt, обычный
- **Символы:** Arial, 10pt, жирный
- **Заголовки:** Arial, 9pt, жирный
- **Мелкий текст:** Arial, 7pt, обычный

## Доступность

Все индикаторы используют:
- Высококонтрастные цвета
- Понятные Unicode символы
- Текстовые описания на русском языке
- Стандартные шрифты Arial

## Расширение

Для добавления новых типов индикаторов:

1. Добавить символ в `get_symbol_map()`
2. Добавить цвет в `get_color_scheme()`
3. Создать новый статический метод `create_[type]_indicator()`
4. Обновить документацию

## Тестирование

Индикаторы протестированы в:
- Windows 10/11
- Qt 5.15+
- Разрешении экрана 1920x1080 и выше
- Темной и светлой темах Windows