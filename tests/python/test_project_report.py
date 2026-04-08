from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.docker_smoke import run_docker_smoke
from scripts.project_report import build_report


class ProjectReportTestCase(unittest.TestCase):
    def test_inventory_only_report_includes_assistant_surface_and_docker_sections(self) -> None:
        report = build_report(run_commands=False)
        self.assertEqual(report['verification']['overall_status'], 'not-run')
        self.assertEqual(report['assistant_surfaces']['primary_contract'], '/ws/assistant')
        self.assertIn('web_console', report['assistant_surfaces'])
        self.assertEqual(report['docker_smoke']['status'], 'skipped')

    def test_docker_smoke_skips_cleanly_when_docker_is_unavailable(self) -> None:
        with patch('scripts.docker_smoke.shutil.which', return_value=None):
            result = run_docker_smoke(require_docker=False)
        self.assertEqual(result['status'], 'skipped')
        self.assertIn('docker CLI', result['reason'])


if __name__ == '__main__':
    unittest.main()