#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграция ядра обработки с графическим интерфейсом
Обеспечивает связь между GUI и модулями уравнивания
"""

import logging
from typing import Dict, Any, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

from geoadjust.core.network.models import NetworkPoint, Observation
from geoadjust.core.adjustment.engine import AdjustmentEngine
from geoadjust.core.adjustment.equations_builder import EquationsBuilder
from geoadjust.core.adjustment.weight_builder import WeightBuilder
from geoadjust.core.preprocessing.module import PreprocessingModule

logger = logging.getLogger(__name__)


class ProcessingIntegration(QObject):
    """Полная интеграция ядра обработки с графическим интерфейсом"""
    
    progress_updated = pyqtSignal(int, str)
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal(dict)
    processing_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points_model = None
        self.observations_model = None
        self.engine = AdjustmentEngine()
        self.builder = EquationsBuilder()
        self.weight_builder = WeightBuilder()
        # Получаем допуски из проекта если доступны
        tolerances = {}
        if hasattr(self, '_project_points') and self._project_points:
            # Если данные проекта установлены напрямую, пытаемся получить допуски
            pass  # Допуски будут получены в prepare_data_for_adjustment если нужно
        self.preprocessing = PreprocessingModule(tolerances=tolerances)
    
    def set_models(self, points_view, observations_view):
        """Установка моделей данных для интеграции
        
        Args:
            points_view: PointsTableView - представление пунктов
            observations_view: ObservationsTableView - представление измерений
        """
        # Получаем модели из представлений
        self.points_model = points_view.model() if hasattr(points_view, 'model') else points_view
        self.observations_model = observations_view.model() if hasattr(observations_view, 'model') else observations_view
        
        # Сохраняем ссылки на представления для доступа к данным
        self.points_view = points_view
        self.observations_view = observations_view
    
    def set_project_data(self, points_dict, observations_list):
        """Установка данных проекта напрямую
        
        Args:
            points_dict: Dict[str, NetworkPoint] - словарь пунктов
            observations_list: List[Observation] - список измерений
        """
        self._project_points = points_dict
        self._project_observations = observations_list
    
    def prepare_data_for_adjustment(self) -> tuple:
        """Подготовка данных для уравнивания из моделей

        Returns:
            tuple: (points_dict, observations_list, fixed_points)
        """
        # Если данные проекта установлены напрямую, используем их
        if hasattr(self, '_project_points') and self._project_points:
            points_list = self._project_points
            observations_list = self._project_observations or []

            # Преобразуем список точек в словарь объектов Point для совместимости
            from geoadjust.core.network.models import NetworkPoint

            points_dict = {}
            for i, p in enumerate(points_list):
                if isinstance(p, dict):
                    # Конвертируем словарь в объект Point
                    point_id = p.get('point_id', str(i))
                    point = NetworkPoint(
                        point_id=point_id,
                        x=p.get('x'),
                        y=p.get('y'),
                        h=p.get('h'),
                        coord_type=p.get('point_type', 'FREE')
                    )
                    points_dict[point_id] = point
                else:
                    # Уже объект Point
                    points_dict[p.point_id] = p

            # Конвертируем измерения в объекты Observation
            from geoadjust.core.network.models import Observation

            converted_observations = []
            for obs in observations_list:
                if isinstance(obs, dict):
                    observation = Observation(
                        obs_id=f"OBS_{len(converted_observations):06d}",
                        obs_type=obs.get('obs_type') or obs.get('type', 'unknown'),
                        from_setup_id=obs.get('from_setup_id', f"{obs.get('from_point', 'UNK')}_SETUP"),
                        from_point_id=obs.get('from_point') or obs.get('from_point_id', 'UNK'),
                        to_point_id=obs.get('to_point') or obs.get('to_point_id', 'UNK'),
                        value=obs.get('value', 0.0),
                        sigma_apriori=obs.get('sigma_apriori', 0.00005),
                        face_position=obs.get('face_position'),
                        raw_line=obs.get('raw_line')
                    )
                    observation.is_active = True  # По умолчанию активны
                    converted_observations.append(observation)
                else:
                    # Уже объект Observation
                    converted_observations.append(obs)

            observations_list = converted_observations

            # Создаем недостающие точки из измерений
            from geoadjust.core.network.models import NetworkPoint
            for obs in observations_list:
                for point_id in [obs.from_point_id, obs.to_point_id]:
                    if point_id and point_id not in points_dict and point_id != 'UNK':
                        # Создаем новую точку с FREE типом и None координатами
                        points_dict[point_id] = NetworkPoint(
                            point_id=point_id,
                            x=None,
                            y=None,
                            h=None,
                            coord_type='FREE'
                        )
                        logger.info(f"Создана недостающая точка {point_id} из измерений")

            # Определяем фиксированные точки
            fixed_points = [pid for pid, p in points_dict.items() if p.coord_type == 'FIXED']

            logger.info(f"Подготовлено для уравнивания (из проекта): "
                       f"{len(points_dict)} пунктов, "
                       f"{len(observations_list)} измерений, "
                       f"{len(fixed_points)} исходных пунктов")
            
            return points_dict, observations_list, fixed_points
        
        # Иначе пытаемся получить из моделей
        if self.points_model is None or self.observations_model is None:
            raise ValueError("Модели данных не установлены")
        
        # Сбор пунктов
        points_dict = {}
        fixed_points = []
        
        for row in range(self.points_model.rowCount()):
            point = self.points_model.get_point(row)
            if point:
                points_dict[point.point_id] = point
                if point.coord_type == 'FIXED':
                    fixed_points.append(point.point_id)
        
        # Сбор измерений (только активных)
        observations_list = []
        for row in range(self.observations_model.rowCount()):
            obs = self.observations_model.get_observation(row)
            if obs and obs.is_active:
                observations_list.append(obs)

        # Создаем недостающие точки из измерений
        from geoadjust.core.network.models import NetworkPoint
        for obs in observations_list:
            for point_id in [obs.from_point_id, obs.to_point_id]:
                if point_id and point_id not in points_dict:
                    # Создаем новую точку с FREE типом и None координатами
                    points_dict[point_id] = NetworkPoint(
                        point_id=point_id,
                        x=None,
                        y=None,
                        h=None,
                        coord_type='FREE'
                    )
                    logger.info(f"Создана недостающая точка {point_id} из измерений")

        logger.info(f"Подготовлено для уравнивания: "
                    f"{len(points_dict)} пунктов, "
                    f"{len(observations_list)} измерений, "
                    f"{len(fixed_points)} исходных пунктов")
        
        return points_dict, observations_list, fixed_points
    
    def run_adjustment(self) -> Dict[str, Any]:
        """Запуск уравнивания
        
        Returns:
            Dict[str, Any]: Результаты уравнивания
        """
        try:
            self.processing_started.emit()
            self.progress_updated.emit(10, "Подготовка данных...")
            
            # Подготовка данных
            points_dict, observations_list, fixed_points = self.prepare_data_for_adjustment()

            self.progress_updated.emit(20, "Предобработка данных...")

            # Предобработка данных
            preprocessing_config = {}
            preprocessing_result = self.preprocessing.run_preprocessing(
                observations_list, points_dict, preprocessing_config
            )

            # Используем обработанные данные
            if preprocessing_result.get('corrected_observations'):
                observations_list = preprocessing_result['corrected_observations']
                logger.info(f"Предобработка применила коррекции к {len(observations_list)} измерениям")

            if preprocessing_result.get('preliminary_coordinates'):
                # Обновляем координаты пунктов предварительными
                prelim_coords_dict = preprocessing_result['preliminary_coordinates'].get('coordinates', {})
                for point_id, coords in prelim_coords_dict.items():
                    if point_id in points_dict:
                        points_dict[point_id].x = coords.get('x', points_dict[point_id].x)
                        points_dict[point_id].y = coords.get('y', points_dict[point_id].y)
                        if 'h' in coords and points_dict[point_id].h is not None:
                            points_dict[point_id].h = coords['h']
                logger.info(f"Предобработка рассчитала предварительные координаты для {len(prelim_coords_dict)} пунктов")

            self.progress_updated.emit(30, "Построение матрицы коэффициентов...")
            
            # Построение матрицы коэффициентов
            A, L = self.builder.build_adjustment_matrix(
                observations_list,
                points_dict,
                fixed_points
            )
            
            self.progress_updated.emit(50, "Формирование весовой матрицы...")
            
            # Формирование весовой матрицы
            P = self.weight_builder.build_weight_matrix(
                observations_list,
                points_dict
            )
            
            self.progress_updated.emit(70, "Уравнивание сети...")
            
            # Уравнивание
            result = self.engine.adjust(A, L, P)
            
            self.progress_updated.emit(90, "Обновление результатов...")
            
            # Обновление моделей с результатами
            self._update_models_with_results(result, points_dict, observations_list)
            
            self.progress_updated.emit(100, "Уравнивание завершено")
            self.processing_finished.emit(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка при уравнивании: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.processing_error.emit(error_msg)
            raise
    
    def _update_models_with_results(self, result: Dict[str, Any],
                                    points_dict: Dict[str, NetworkPoint],
                                    observations_list: List[Observation]):
        """Обновление моделей данных с результатами уравнивания
        
        Args:
            result: Результаты уравнивания
            points_dict: Словарь пунктов
            observations_list: Список измерений
        """
        # Обновление координат и СКО пунктов
        if 'coordinate_corrections' in result:
            corrections = result['coordinate_corrections']
            
            for row in range(self.points_model.rowCount()):
                point = self.points_model.get_point(row)
                if point and point.coord_type != 'FIXED':
                    idx = list(points_dict.keys()).index(point.point_id)
                    if idx * 2 < len(corrections):
                        point.x += corrections[idx * 2]
                        point.y += corrections[idx * 2 + 1]
                    
                    if 'covariance_matrix' in result:
                        Qxx = result['covariance_matrix']
                        if idx * 2 < Qxx.shape[0]:
                            point.sigma_x = np.sqrt(Qxx[idx * 2, idx * 2])
                            point.sigma_y = np.sqrt(Qxx[idx * 2 + 1, idx * 2 + 1])
                    
                    self.points_model.update_point(row, point)
        
        # Обновление поправок и СКО измерений
        if 'residuals' in result:
            residuals = result['residuals']
            
            for row in range(self.observations_model.rowCount()):
                obs = self.observations_model.get_observation(row)
                if obs and obs.is_active:
                    idx = observations_list.index(obs)
                    if idx < len(residuals):
                        obs.residual = residuals[idx]
                        
                        if 'sigma0' in result and hasattr(obs, 'weight'):
                            obs.sigma_aposteriori = result['sigma0'] / np.sqrt(obs.weight)
                        
                        self.observations_model.update_observation(row, obs)
