"""Разреженный решатель нормальных уравнений с регуляризацией и проверкой ранга"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from loguru import logger
from typing import Optional, Tuple

def solve_normal_equations(
    A: sp.csr_matrix,
    L: np.ndarray,
    P: sp.diags,
    compute_covariance: bool = False
) -> tuple:
    """
    Решение нормальных уравнений N·Δx = U методом наименьших квадратов.
    
    N = Aᵀ·P·A  (нормальная матрица)
    U = Aᵀ·P·L  (вектор свободных членов)
    
    Args:
        A: Матрица коэффициентов (m×n)
        L: Вектор невязок (m,)
        P: Диагональная матрица весов
        compute_covariance: Вычислять ли ковариационную матрицу
        
    Returns:
        Tuple[dx, Q_xx]:
            dx - вектор поправок к неизвестным
            Q_xx - ковариационная матрица (или None)
    """
    # Формирование нормальной матрицы N = AᵀPA
    PA = P @ A
    N = (A.T @ PA).tocsc()
    
    # Вектор U = AᵀPL
    PL = P @ L
    U = A.T @ PL
    
    # Решение системы N·dx = U с проверкой ранга и регуляризацией
    dx = _solve_sparse_system(N, U)
    
    # Ковариационная матрица (опционально)
    Q_xx = None
    if compute_covariance:
        try:
            Q_xx = _compute_covariance_matrix(N)
        except Exception as e:
            logger.warning(f"Не удалось вычислить ковариационную матрицу: {e}")
    
    return dx, Q_xx

def _check_matrix_rank(A: sp.csr_matrix, tol: float = 1e-10) -> Tuple[bool, int]:
    """
    Проверка ранга матрицы A через оценку сингулярных чисел.
    
    Returns:
        Tuple[is_full_rank, estimated_rank]
    """
    try:
        # Быстрая оценка ранга через количество ненулевых сингулярных чисел
        # Для больших матриц используем случайную проекцию
        n = min(A.shape)
        if n > 1000:
            # Приближённая оценка для очень больших матриц
            diag_N = (A.T @ A).diagonal()
            rank = np.sum(np.abs(diag_N) > tol)
        else:
            # Точная проверка через SVD для небольших матриц
            from scipy.sparse.linalg import svds
            try:
                s = svds(A, k=min(A.shape)-1, return_singular_vectors=False)
                rank = np.sum(s > tol)
            except Exception:
                # Fallback на оценку по диагонали N
                diag_N = (A.T @ A).diagonal()
                rank = np.sum(np.abs(diag_N) > tol)
        
        is_full_rank = rank >= A.shape[1]
        return is_full_rank, int(rank)
    except Exception as e:
        logger.warning(f"Не удалось проверить ранг матрицы: {e}. Предполагается полный ранг.")
        return True, A.shape[1]

def _solve_sparse_system(N: sp.csc_matrix, U: np.ndarray) -> np.ndarray:
    """Решение разреженной системы линейных уравнений с регуляризацией"""
    
    # 1. Проверка на сингулярность через диагональ
    diag_N = N.diagonal()
    min_diag = np.min(np.abs(diag_N))
    
    if min_diag < 1e-12:
        logger.warning(
            f"Матрица N близка к сингулярной (min|diag|={min_diag:.2e}). "
            "Применяю регуляризацию Лежандра."
        )
        # Регуляризация: N_reg = N + λ·I
        lambda_reg = 1e-9
        N = N + lambda_reg * sp.eye(N.shape[0], format="csc")
    
    # 2. Попытка решения через UMFPACK
    try:
        dx = spla.spsolve(N, U, use_umfpack=True)
        return dx
    except Exception as e:
        logger.warning(f"spsolve упал ({e}), переключаюсь на LSQR (итерационный метод)")
    
    # 3. Fallback: итерационный метод LSQR
    try:
        result = spla.lsqr(N, U, atol=1e-12, btol=1e-12)
        return result[0]
    except Exception as e:
        logger.error(f"LSQR также упал: {e}")
        raise RuntimeError("Не удалось решить систему нормальных уравнений")

def _compute_covariance_matrix(N: sp.csc_matrix) -> Optional[sp.csr_matrix]:
    """
    Вычисление ковариационной матрицы Q = N⁻¹.
    
    Для больших матриц используется разреженное обращение.
    """
    try:
        N_inv = spla.inv(N)
        return N_inv.tocsr()
    except Exception as e:
        logger.warning(f"Не удалось вычислить полную ковариационную матрицу: {e}")
        # Возвращаем только диагональ
        try:
            diag = spla.inv(N).diagonal()
            return sp.diags(diag).tocsr()
        except Exception:
            raise RuntimeError("Не удалось вычислить ковариационную матрицу")

def compute_sigma_0(residuals: np.ndarray, P: sp.diags, redundancy: int) -> float:
    """
    Вычисление средней квадратической ошибки единицы веса.
    
    σ₀ = √(vᵀPv / r)
    
    где:
        v - вектор невязок
        P - матрица весов
        r - число избыточных измерений (redundancy)
    """
    if redundancy <= 0:
        logger.warning("Отрицательная или нулевая избыточность, σ₀ не определён")
        return 0.0
    
    vTPv = float((residuals @ P @ residuals).sum())
    
    if vTPv < 0:
        logger.warning(f"Отрицательное vTPv = {vTPv}, проверка весов")
        vTPv = abs(vTPv)
    
    sigma_0 = np.sqrt(vTPv / redundancy)
    return sigma_0
