import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import dependency_check


class YtDlpResolutionTests(unittest.TestCase):
    def _make_executable(self, directory: Path, name: str, content: str) -> str:
        path = directory / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)
        return str(path)

    def test_broken_app_binary_falls_back_to_working_system_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            broken = self._make_executable(
                directory,
                "broken-yt-dlp",
                "#!/missing/python\n",
            )
            working = self._make_executable(
                directory,
                "working-yt-dlp",
                "#!/bin/sh\necho 2026.07.04\n",
            )

            with patch.object(
                dependency_check,
                "get_yt_dlp_binary_candidates",
                return_value=[broken, working, working],
            ):
                self.assertEqual(
                    dependency_check.resolve_yt_dlp_binary(),
                    working,
                )

    def test_system_binary_counts_as_installed_without_app_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            working = self._make_executable(
                Path(temp_dir), "yt-dlp", "#!/bin/sh\necho 2026.07.04\n"
            )
            with patch.object(
                dependency_check,
                "get_yt_dlp_binary_candidates",
                return_value=[None, working],
            ):
                status = dependency_check.check_yt_dlp()

        self.assertTrue(status.available)
        self.assertEqual(status.binary, working)

    def test_python_package_counts_as_installed_without_binary(self):
        package = SimpleNamespace(version=SimpleNamespace(__version__="2026.07.04"))
        with patch.object(
            dependency_check, "get_yt_dlp_binary_candidates", return_value=[]
        ), patch.dict(sys.modules, {"yt_dlp": package}):
            status = dependency_check.check_yt_dlp()

        self.assertTrue(status.available)
        self.assertEqual(status.binary, "bundled Python package")
        self.assertEqual(status.version, "2026.07.04")

    def test_rejects_non_executable_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "yt-dlp"
            path.write_text("#!/bin/sh\necho version\n", encoding="utf-8")
            path.chmod(0o644)

            self.assertFalse(
                dependency_check.is_yt_dlp_binary_usable(str(path))
            )


if __name__ == "__main__":
    unittest.main()
