# src/geoadjust/core/validation/sparse_validation.py
"""Проверка ранга и обусловленности нормальной матрицы N = AᵀPA без перевода в плотный формат."""
import logging
from typing import Any, Dict

import numpy as np
import scipy.sparse as sparse
from scipy.sparse.linalg import eigsh

logger = logging.getLogger("geoadjust.validation.sparse")

def validate_sparse_system(
    A: sparse.spmatrix,
    P: sparse.spmatrix,
    L: np.ndarray,
    n_params: int,
    dense_threshold: int = 200,
    tol_rank: float = 1e-10,
    tol_cond: float = 1e12
) -> Dict[str, Any]:
    """
    Валидация разреженной системы уравнений.
    Возвращает структурированный отчёт для ctx.validation_report.
    """
    report = {"status": "PASSED", "checks": {}, "message": "Система валидна", "defect": 0}
    n_obs = len(L)

    if n_obs == 0:
        return _fail(report, "Нет измерений для уравнивания")
    if n_obs != A.shape[0]:
        return _fail(report, "Размерности A и L не совпадают")
    if n_params == 0:
        report["message"] = "Все пункты фиксированы. Уравнивание не требуется."
        return report

    # Формируем нормальную матрицу N = A^T P A (разреженную)
    N = (A.T @ P @ A).tocsr()

    # Для малых матриц используем точный плотный расчёт
    if n_params <= dense_threshold:
        try:
            N_dense = N.toarray()
            rank = np.linalg.matrix_rank(N_dense, tol=tol_rank)
            cond = np.linalg.cond(N_dense) if rank == n_params else np.inf
            return _build_report(report, rank, n_params, cond)
        except Exception:
            logger.warning("Переход к разреженной валидации (ошибка dense fallback)")

    # Разреженная оценка спектра
    try:
        # eigsh требует SPD матрицу. Добавляем небольшой регуляризатор для стабильности
        k = min(n_params - 1, max(10, n_params // 4))
        sigma = 1e-12 if n_params > 500 else 0

        # Оценка максимального собственного значения
        try:
            eig_max = eigsh(N, k=1, which='LM', sigma=sigma, return_eigenvectors=False)[0]
        except Exception:
            eig_max = 1.0

        # Оценка наименьшего ненулевого eigenvalue
        try:
            eig_vals = eigsh(N, k=min(k, 10), which='SM', sigma=tol_rank*10, return_eigenvectors=False)
            eig_vals = np.abs(eig_vals)
            nonzero = eig_vals[eig_vals > tol_rank]
            eig_min = np.min(nonzero) if len(nonzero) > 0 else tol_rank
        except Exception:
            eig_min = tol_rank

        # Оценка ранга через подсчет собственных значений меньше порога
        try:
            small_eigs = eigsh(N, k=min(n_params, 50), which='SM', sigma=1e-14, return_eigenvectors=False)[0]
            rank_est = int(n_params - np.sum(np.abs(small_eigs) < tol_rank))
        except Exception:
            rank_est = n_params

        cond_est = eig_max / max(eig_min, tol_rank)

        return _build_report(report, rank_est, n_params, cond_est, is_sparse=True)
    except Exception as e:
        logger.warning(f"Не удалось оценить спектр: {e}")
        report["status"] = "WARNING"
        report["message"] = "Требуется ручная проверка связности сети"
        return report

def _build_report(report, rank, n_params, cond, is_sparse=False):
    report["checks"]["rank"] = f"{int(rank)}/{n_params}"
    report["checks"]["condition_number"] = f"{cond:.2e}"
    report["defect"] = max(0, int(n_params - rank))

    if report["defect"] == 0:
        report["message"] = "Ранг полный. Сеть жёстко закреплена."
    elif report["defect"] <= 3:
        report["status"] = "FREE_NETWORK"
        report["message"] = f"⚠️ Свободная сеть (дефект ранга: {report['defect']}). Требуется S-преобразование."
    else:
        report["status"] = "FAILED"
        report["message"] = f"❌ Критический дефект ранга: {report['defect']}. Проверьте исходные пункты."

    if cond > 1e12:
        report["status"] = "POORLY_CONDITIONED" if report["status"] == "PASSED" else report["status"]
        report["message"] += f" | ⚠️ Высокая обусловленность (cond≈{cond:.2e})"
    return report

def _fail(report, msg):
    report["status"] = "FAILED"
    report["message"] = msg
    return report
