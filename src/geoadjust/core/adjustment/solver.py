"""Разреженный решатель нормальных уравнений с поддержкой CHOLMOD"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from loguru import logger
from typing import Optional

# Попытка импорта CHOLMOD для ускорения больших сетей
try:
    from sksparse.cholmod import cholesky as cholmod_cholesky
    HAS_CHOLMOD = True
    logger.info("✅ scikit-sparse (CHOLMOD) доступен для ускоренного решения")
except ImportError:
    HAS_CHOLMOD = False
    logger.warning(
        "⚠️ scikit-sparse не найден. Будет использован scipy.sparse.linalg.spsolve.\n"
        "Для сетей >500 пунктов рекомендуется установить:\n"
        "  conda install -c conda-forge scikit-sparse\n"
        "или скачать precompiled wheel с https://github.com/scikit-sparse/scikit-sparse"
    )

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
    # Используем efficient sparse multiplication
    # Правильный порядок: N = Aᵀ @ (P @ A)
    # P @ A: (m×m) @ (m×n) → (m×n)
    # Aᵀ @ (P @ A): (n×m) @ (m×n) → (n×n)
    PA = P @ A  # Умножаем диагональную P на A
    N = (A.T @ PA).tocsc()  # CSC формат для solver
    
    # Вектор U = AᵀPL
    PL = P @ L
    U = A.T @ PL
    
    # Решение системы N·dx = U
    dx = _solve_sparse_system(N, U)
    
    # Ковариационная матрица (опционально)
    Q_xx = None
    if compute_covariance:
        try:
            Q_xx = _compute_covariance_matrix(N)
        except Exception as e:
            logger.warning(f"Не удалось вычислить ковариационную матрицу: {e}")
    
    return dx, Q_xx

def _solve_sparse_system(N: sp.csc_matrix, U: np.ndarray) -> np.ndarray:
    """Решение разреженной системы линейных уравнений"""
    
    # Предпочитаем CHOLMOD для больших систем (>100 неизвестных)
    if HAS_CHOLMOD and N.shape[0] > 100:
        try:
            factor = cholmod_cholesky(N)
            dx = factor(U)
            return np.asarray(dx).flatten()
        except Exception as e:
            logger.warning(f"CHOLMOD упал ({e}), переключаюсь на scipy")
    
    # Fallback на scipy.sparse.linalg
    try:
        # UMFPACK (LU-разложение для разреженных матриц)
        dx = spla.spsolve(N, U, use_umfpack=True)
        return dx
    except Exception:
        # Последний fallback: итерационный метод LSQR
        logger.warning("spsolve упал, использую lsqr (итерационный)")
        dx = spla.lsqr(N, U)[0]
        return dx

def _compute_covariance_matrix(N: sp.csc_matrix) -> Optional[sp.csr_matrix]:
    """
    Вычисление ковариационной матрицы Q = N⁻¹.
    
    Для больших матриц используется разреженное обращение.
    """
    try:
        # Разрешенное обращение через scipy
        N_inv = spla.inv(N)
        return N_inv.tocsr()
    except Exception:
        # Альтернатива: разложение Холецкого с извлечением диагонали
        if HAS_CHOLMOD:
            try:
                factor = cholmod_cholesky(N)
                # Извлечение только диагонали (быстрее)
                diag = factor.P() ** 2
                return sp.diags(diag).tocsr()
            except Exception:
                pass
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
    
    # vᵀPv
    vTPv = float((residuals @ P @ residuals).sum())
    
    if vTPv < 0:
        logger.warning(f"Отрицательное vTPv = {vTPv}, проверка весов")
        vTPv = abs(vTPv)
    
    sigma_0 = np.sqrt(vTPv / redundancy)
    return sigma_0
