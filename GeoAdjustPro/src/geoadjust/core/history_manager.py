# src/geoadjust/core/history_manager.py
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class HistoryManager:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.history_file = project_dir / 'history' / 'history.json'
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[Dict] = []
        self._load()

    def _load(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.entries = json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки истории: {e}")
                self.entries = []

    def _save(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории: {e}")

    def add_entry(self, action: str, description: str, user: str = "system", severity: str = "info"):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "description": description,
            "user": user,
            "severity": severity
        }
        self.entries.append(entry)
        self._save()
        logger.info(f"[ИСТОРИЯ] {action}: {description}")

    def get_entries(self, limit: int = None, severity: str = None) -> List[Dict]:
        filtered = self.entries
        if severity:
            filtered = [e for e in filtered if e.get("severity") == severity]
        return filtered[-limit:] if limit else filtered

    def clear(self):
        self.entries.clear()
        self._save()