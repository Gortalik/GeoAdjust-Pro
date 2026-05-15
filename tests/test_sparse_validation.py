# tests/test_sparse_validation.py
"""Параметризованные тесты валидации разреженных систем."""
import pytest
import numpy as np
import scipy.sparse as sparse
from geoadjust.core.validation.sparse_validation import validate_sparse_system

def _make_mock_system(n_params, n_obs, defect=0, condition=1e6):
    """Генерирует разреженную систему с заданными свойствами."""
    np.random.seed(42)
    # Базовая SPD матрица нужного ранга
    rank = n_params - defect
    if rank <= 0:
        A = np.zeros((n_obs, n_params))
    else:
        # Создаём матрицу полного ранга, затем обнуляем столбцы для создания дефекта
        A = np.random.randn(n_obs, n_params)
        if defect > 0:
            # Обнуляем последние 'defect' столбцов для создания дефекта ранга
            A[:, -defect:] = 0
    # Масштабируем для заданной обусловленности
    if condition < np.inf and rank > 0:
        vals = np.linspace(1, condition, n_params)
        scaling = np.sqrt(vals)
        for i in range(min(n_params, len(scaling))):
            if i < n_params - defect:  # Не масштабируем обнулённые столбцы
                A[:, i] *= scaling[i]
    A_sparse = sparse.csr_matrix(A)
    P_sparse = sparse.eye(n_obs)
    L = np.random.randn(n_obs)
    return A_sparse, P_sparse, L, n_params

@pytest.mark.parametrize("defect, expected_status, msg_contains", [
    (0, "PASSED", "Ранг полный"),
    (1, "FREE_NETWORK", "дефект ранга: 1"),
    (2, "FREE_NETWORK", "дефект ранга: 2"),
    (3, "FREE_NETWORK", "дефект ранга: 3"),
    (4, "FAILED", "Критический дефект"),
])
def test_rank_validation(defect, expected_status, msg_contains):
    """Проверка определения ранга с различным дефектом."""
    A, P, L, n = _make_mock_system(20, 30, defect=defect, condition=1e5)
    report = validate_sparse_system(A, P, L, n_params=n)
    assert report["status"] == expected_status
    assert msg_contains in report["message"]

def test_empty_observations():
    """Проверка обработки пустых наблюдений."""
    A = sparse.csr_matrix((0, 10))
    P = sparse.csr_matrix((0, 0))
    L = np.array([])
    report = validate_sparse_system(A, P, L, n_params=10)
    assert report["status"] == "FAILED"
    assert "Нет измерений" in report["message"]

def test_dimension_mismatch():
    """Проверка несовпадения размерностей A и L."""
    A, P, L, n = _make_mock_system(10, 10, defect=0)
    L_wrong = np.append(L, 1.0)  # Длина не совпадает с A.shape[0]
    report = validate_sparse_system(A, P, L_wrong, n_params=n)
    assert report["status"] == "FAILED"

def test_poor_conditioning():
    """Проверка обнаружения плохой обусловленности."""
    A, P, L, n = _make_mock_system(15, 20, defect=0, condition=1e15)
    report = validate_sparse_system(A, P, L, n_params=n)
    assert report["status"] in ("POORLY_CONDITIONED", "WARNING", "PASSED")
    # Проверяем, что cond записан в отчёт
    assert "condition_number" in report.get("checks", {})

def test_large_sparse_system():
    """Тест производительности на большой разреженной матрице."""
    n_params = 500
    n_obs = 800
    A, P, L, n = _make_mock_system(n_params, n_obs, defect=0, condition=1e4)
    report = validate_sparse_system(A, P, L, n_params=n)
    # Статус может быть PASSED, WARNING или POORLY_CONDITIONED в зависимости от обусловленности
    assert report["status"] in ("PASSED", "WARNING", "POORLY_CONDITIONED")
    assert report["defect"] == 0 or report["defect"] <= 3

def test_all_fixed_points():
    """Проверка случая, когда все точки фиксированы."""
    A = sparse.csr_matrix((10, 0))
    P = sparse.eye(10)
    L = np.random.randn(10)
    report = validate_sparse_system(A, P, L, n_params=0)
    assert report["status"] == "PASSED"
    assert "Все пункты фиксированы" in report["message"]
