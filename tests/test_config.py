import stat
import tempfile
import unittest
from pathlib import Path

from core.config import Config


class ConfigSecurityTests(unittest.TestCase):
    @unittest.skipIf(__import__("os").name == "nt", "POSIX permission test")
    def test_save_uses_owner_only_permissions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config.__new__(Config)
            config.config_dir = Path(temp_dir)
            config.config_file = config.config_dir / "config.json"
            config.config = {"cookies": {"NID_AUT": "secret"}}

            config.save()

            mode = stat.S_IMODE(config.config_file.stat().st_mode)
            self.assertEqual(mode, 0o600)
            self.assertNotIn(".tmp", config.config_file.name)


if __name__ == "__main__":
    unittest.main()
