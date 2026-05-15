"""Валидация и очистка наблюдений перед уравниванием"""
from typing import Dict, List, Set, Tuple

import networkx as nx

from .base import Observation


def validate_and_clean(observations: List[Observation]) -> Tuple[List[Observation], Dict]:
    """
    Предварительная валидация сети наблюдений.
    
    Выполняет:
    1. Удаление дубликатов (station, target, type)
    2. Удаление самопетель (station == target)
    3. Нормализацию расстояний
    4. Проверку связности графа
    5. Выделение наибольшего связного компонента
    
    Returns:
        Tuple[List[Observation], Dict]: Очищенный список и отчёт о валидации
    """
    report = {
        "total": len(observations),
        "removed_duplicates": 0,
        "removed_self_loops": 0,
        "removed_invalid": 0,
        "disconnected_components": 0,
        "largest_component_size": 0,
        "final": 0
    }

    # 1. Удаление дубликатов и самопетель
    seen: Set[tuple] = set()
    clean_obs: List[Observation] = []

    for obs in observations:
        # Пропуск невалидных записей
        if not obs.station_id or not obs.target_id:
            report["removed_invalid"] += 1
            continue

        key = (obs.station_id, obs.target_id, obs.type)

        # Дубликаты
        if key in seen:
            report["removed_duplicates"] += 1
            continue
        seen.add(key)

        # Самопетли
        if obs.station_id == obs.target_id:
            report["removed_self_loops"] += 1
            continue

        # Нормализация расстояния
        if obs.distance <= 0:
            obs.distance = 1.0

        clean_obs.append(obs)

    # 2. Построение графа для проверки связности
    graph = nx.Graph()
    all_points: Set[str] = set()

    for obs in clean_obs:
        graph.add_edge(obs.station_id, obs.target_id)
        all_points.update([obs.station_id, obs.target_id])

    # 3. Анализ связности
    if not all_points:
        report["final"] = 0
        return [], report

    components = list(nx.connected_components(graph))
    report["disconnected_components"] = len(components)

    # 4. Если сеть несвязная - оставляем только наибольший компонент
    if len(components) > 1:
        largest_component = max(components, key=len)
        report["largest_component_size"] = len(largest_component)

        clean_obs = [
            obs for obs in clean_obs
            if obs.station_id in largest_component and obs.target_id in largest_component
        ]

    report["final"] = len(clean_obs)
    return clean_obs, report

def check_network_quality(observations: List[Observation]) -> Dict:
    """
    Оценка качества сети перед уравниванием.
    
    Returns:
        Dict: Метрики качества сети
    """
    if not observations:
        return {"quality": "empty", "issues": ["Нет наблюдений"]}

    issues: List[str] = []
    metrics = {
        "num_observations": len(observations),
        "num_stations": len(set(obs.station_id for obs in observations)),
        "num_targets": len(set(obs.target_id for obs in observations)),
        "avg_distance": 0.0,
        "max_distance": 0.0,
        "min_distance": float('inf'),
    }

    distances = [obs.distance for obs in observations if obs.distance > 0]
    if distances:
        metrics["avg_distance"] = sum(distances) / len(distances)
        metrics["max_distance"] = max(distances)
        metrics["min_distance"] = min(distances)

    # Проверка на потенциальные проблемы
    if metrics["num_observations"] < metrics["num_stations"]:
        issues.append("Недостаточно наблюдений для количества станций")

    if metrics["max_distance"] > 1000:
        issues.append(f"Обнаружены очень длинные линии: {metrics['max_distance']:.1f} м")

    if metrics["avg_distance"] < 10:
        issues.append("Среднее расстояние слишком малое (< 10 м)")

    # Оценка качества
    if not issues:
        quality = "excellent"
    elif len(issues) == 1:
        quality = "good"
    elif len(issues) == 2:
        quality = "fair"
    else:
        quality = "poor"

    metrics["quality"] = quality
    metrics["issues"] = issues

    return metrics
