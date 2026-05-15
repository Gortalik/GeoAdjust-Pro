# 📦 Внедрение нового конвейера обработки GeoAdjust Pro

## ✅ Созданные файлы

### 1. `src/geoadjust/core/processing_context.py`
**Назначение:** Единый объект-контекст для передачи данных между этапами конвейера.

**Ключевые возможности:**
- Хранит измерения, пункты, фиксированные точки, конфигурацию
- Автоматическое логирование всех этапов через `add_log()`
- Сборка и хранение матриц A, P, L
- Отчёт валидации (ранг, обусловленность, статус)
- Метод `get_pipeline_report()` для получения сводки

### 2. `src/geoadjust/gui/qlog_handler.py`
**Назначение:** Потокобезопасный мост между Python `logging` и PyQt5 `QTextEdit`.

**Ключевые возможности:**
- Наследуется от `logging.Handler` и `QObject`
- Передача логов через `pyqtSignal` (без блокировки GUI)
- Добавление GUI-таймстампа с миллисекундами
- Метод `attach_to_widget()` для привязки к QTextEdit

### 3. `src/geoadjust/core/adjustment/equations_builder.py`
**Назначение:** Построение матриц A и L с детальным логированием и валидацией.

**Ключевые возможности:**
- Поддержка нивелирования (LEVELING), расстояний, углов
- Проверка наличия точек и их координат перед сборкой
- Детальное логирование каждого этапа (каждое 50-е измерение)
- Валидация системы:
  - Проверка размерностей A и L
  - Расчёт ранга нормальной матрицы N = A^T·A
  - Вычисление числа обусловленности
  - Обнаружение дефекта ранга (свободные сети)

### 4. `src/geoadjust/processing_pipeline.py`
**Назначение:** Полный конвейер обработки данных.

**Этапы конвейера:**
1. **PREPROCESS** — предобработка (очистка, допуски, редукции)
2. **MATRIX_ASSEMBLY (A, L)** — построение уравнений поправок
3. **MATRIX_ASSEMBLY (P)** — расчёт весов по приборам
4. **VALIDATION** — финальная проверка системы

**Статусы завершения:**
- `READY` — система валидна, готова к уравниванию
- `VALIDATION_FAILED` — ошибка на этапе сборки матриц
- `DIMENSION_MISMATCH` — несовпадение размерностей A, P, L
- `RANK_DEFICIENT` — дефект ранга > 3
- `POORLY_CONDITIONED` — число обусловленности > 1e12
- `MATRICES_MISSING` — отсутствуют матрицы
- `CRASHED` — необработанная ошибка

### 5. `src/geoadjust/gui/main_window.py` (обновлён)
**Изменения:**
- Добавлен импорт новых модулей (`QLogHandler`, `ProcessingContext`, `ProcessingPipeline`)
- Создан класс `PipelineWorker(QThread)` для асинхронного запуска конвейера
- В `__init__()` подключён `QLogHandler` к `self.log_text`
- Метод `start_adjustment()` теперь запускает конвейер вместо прямого уравнивания
- Добавлены методы:
  - `on_pipeline_finished()` — обработка результатов конвейера
  - `on_pipeline_error()` — обработка ошибок конвейера
  - `_run_legacy_adjustment()` — запуск старого AdjustmentEngine после успешной валидации

---

## 🔗 Интеграция в существующий проект

### Шаг 1: Подключение логгера
В `main_window.py` после создания `self.log_text`:
```python
from geoadjust.gui.qlog_handler import QLogHandler

self.log_handler = QLogHandler()
self.log_handler.attach_to_widget(self.log_text)
logging.getLogger("geoadjust").addHandler(self.log_handler)
logging.getLogger("geoadjust").setLevel(logging.DEBUG)
```

### Шаг 2: Запуск конвейера
Вместо прямого вызова `engine.adjust_heights()`:
```python
from geoadjust.core.processing_context import ProcessingContext
from geoadjust.processing_pipeline import ProcessingPipeline

ctx = ProcessingContext(
    observations=self._current_observations,
    points={},
    fixed_points=self.fixed_points,  # из диалога
    config={"spec": self.engine.spec}
)

pipeline = ProcessingPipeline()
result = pipeline.run(ctx)

if result.status == "READY":
    # Запуск уравнивания
    engine.adjust_heights(...)
else:
    # Обработка ошибки
    QMessageBox.warning(self, "Ошибка", f"Статус: {result.status}")
```

### Шаг 3: Асинхронный запуск (рекомендуется)
Использовать `PipelineWorker` как в обновлённом `main_window.py`:
```python
class PipelineWorker(QThread):
    finished = pyqtSignal(ProcessingContext)
    error = pyqtSignal(str)
    
    def run(self):
        pipeline = ProcessingPipeline()
        result = pipeline.run(ctx)
        self.finished.emit(result)
```

---

## 📊 Пример вывода в журнал

```
[14:32:01.245] [INFO    ] [PIPELINE] Запуск полного конвейера обработки
[14:32:01.248] [INFO    ] [PREPROCESS] Начало предобработки измерений и сети
[14:32:01.251] [DEBUG   ] [PREPROCESS] Исходных измерений: 142
[14:32:01.253] [INFO    ] [PREPROCESS] Предобработка завершена...
[14:32:01.255] [INFO    ] [MATRIX_ASSEMBLY] Построение матрицы A и вектора L
[14:32:01.267] [DEBUG   ] [MATRIX_ASSEMBLY] Сформировано 45 индексов пунктов
[14:32:01.289] [INFO    ] [MATRIX_ASSEMBLY] Матрицы собраны и провалидированы
[14:32:01.291] [INFO    ] [MATRIX_ASSEMBLY] Построение весовой матрицы P
[14:32:01.295] [DEBUG   ] [MATRIX_ASSEMBLY] Матрица P собрана. Размер: (142, 142)
[14:32:01.297] [INFO    ] [VALIDATION] Система уравнений валидна. Готово к уравниванию.
[14:32:01.298] [INFO    ] [PIPELINE] Конвейер завершён успешно.
```

---

## ⚠️ Диагностика проблем

| Статус | Причина | Решение |
|--------|---------|---------|
| `RANK_DEFICIENT` | Дефект ранга > 3 | Добавить исходные пункты или проверить связность сети |
| `POORLY_CONDITIONED` | cond > 1e12 | Улучшить геометрию сети, проверить единицы измерений |
| `DIMENSION_MISMATCH` | A.shape[0] != len(L) | Проверить фильтрацию измерений в `_validate_observation` |
| `MATRICES_MISSING` | Нет A, P или L | Проверить этапы конвейера, логи на наличие ошибок |

---

## 🧪 Тестирование

```bash
cd /workspace
python -c "
from geoadjust.core.processing_context import ProcessingContext
from geoadjust.processing_pipeline import ProcessingPipeline
from geoadjust.io.base import Observation
from geoadjust.core.adjustment.weights import ObsType

obs = [
    Observation(station_id='A', target_id='B', value=1.5, distance=0.5, type=ObsType.LEVELING),
    Observation(station_id='B', target_id='C', value=2.3, distance=0.7, type=ObsType.LEVELING),
]

ctx = ProcessingContext(
    observations=obs,
    fixed_points={'A': 100.0, 'C': 103.8},
    config={}
)

result = ProcessingPipeline().run(ctx)
print(f'Статус: {result.status}')
print(f'Ранг: {result.validation_report.get(\"rank\")}')
"
```

---

## 📈 Преимущества новой архитектуры

1. **Прозрачность** — каждый этап логируется, видны все промежуточные результаты
2. **Безопасность** — валидация перед уравниванием блокирует запуск на некорректных данных
3. **Расширяемость** — легко добавить новые этапы в конвейер
4. **Потокобезопасность** — GUI не блокируется при вычислениях
5. **Единый контекст** — нет путаницы с передачей данных между модулями

---

## 🔄 Обратная совместимость

Старый `AdjustmentEngine` продолжает работать. Новый конвейер лишь добавляет этап валидации перед ним. Для полного перехода достаточно заменить вызовы `engine.adjust_heights()` на `pipeline.run(ctx)`.
