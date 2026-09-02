"""Tests for the persisted document-processing progress contract."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.processing_ui_registry import ProcessingUiRegistry


class ProcessingProgressTests(unittest.TestCase):
    def test_progress_moves_from_running_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = ProcessingUiRegistry(project_root=Path(directory))

            registry.start_processing(source="local")
            registry.set_processing_total(2)
            registry.update_processing(
                completed=0,
                total=2,
                current_file="nota-01.pdf",
                phase="Lendo PDF",
                stage_progress=0.4,
            )

            running = registry.processing_progress()
            self.assertEqual(running["status"], "running")
            self.assertEqual(running["total"], 2)
            self.assertEqual(running["currentFile"], "nota-01.pdf")
            self.assertGreater(running["progress"], 0)
            self.assertLess(running["progress"], 100)

            registry.update_processing(
                completed=2,
                total=2,
                current_file="nota-02.pdf",
                phase="Gerando arquivos de saída",
                stage_progress=0.95,
            )
            registry.complete_processing()

            completed = registry.processing_progress()
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["completed"], 2)
            self.assertEqual(completed["progress"], 100)
            self.assertEqual(completed["phase"], "Processamento concluído")


if __name__ == "__main__":
    unittest.main()
