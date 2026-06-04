"""Обёртка для обратной совместимости"""
from .formats.gsi import GSIParser

__all__ = ["GSIParser", "GSIObservation"]
