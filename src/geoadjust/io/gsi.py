"""Обёртка для обратной совместимости"""
from .formats.gsi import GSIParser, GSIObservation

__all__ = ["GSIParser", "GSIObservation"]
