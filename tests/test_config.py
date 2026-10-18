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


class ConfigRecoveryTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.patch = patch('core.config.Path.home', return_value=self.home)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.path = self.home / '.clipcatcher' / 'config.json'
        self.path.parent.mkdir()

    def write(self, value):
        import json
        self.path.write_text(json.dumps(value), encoding='utf-8')
        return self.path.read_bytes()

    def test_nonobject_json_and_malformed_input_recover_without_rewriting(self):
        import json
        for value in ([], [1], 42, True, 'text', None):
            with self.subTest(value=value):
                original = self.write(value)
                config = Config()
                self.assertEqual(config.config, Config.DEFAULT_CONFIG)
                self.assertEqual(self.path.read_bytes(), original)
        for value in (b'{broken', b'\xff', b'[' * 2000 + b']' * 2000):
            self.path.write_bytes(value)
            self.assertEqual(Config().config, Config.DEFAULT_CONFIG)
            self.assertEqual(self.path.read_bytes(), value)

    def test_invalid_known_fields_keep_valid_preferences(self):
        self.write({'download_path': [], 'concurrent_downloads': True,
                    'default_quality': None, 'theme': 'light',
                    'cookies': {'NID_AUT': 5, 'NID_SES': 'valid'},
                    'future_option': {'enabled': True}})
        config = Config()
        self.assertEqual(config.get('download_path'), Config.DEFAULT_CONFIG['download_path'])
        self.assertEqual(config.get('concurrent_downloads'), 1)
        self.assertEqual(config.get('default_quality'), '1080p')
        self.assertEqual(config.get('theme'), 'light')
        self.assertEqual(config.get('future_option'), {'enabled': True})
        self.assertEqual(config.get('cookies'), {'NID_AUT': '', 'NID_SES': 'valid'})
        self.assertEqual(config.get_cookies(), '')

    def test_bad_field_types_and_control_characters(self):
        for value in (None, [], {}, False, 0, 6, '2', 2.5):
            self.write({'concurrent_downloads': value})
            self.assertEqual(Config().get('concurrent_downloads'), 1)
        for value in ('', '  ', 'a\x00b', 'a\nb', 123, []):
            self.write({'download_path': value, 'default_quality': value, 'theme': value})
            config = Config()
            for key in ('download_path', 'default_quality', 'theme'):
                self.assertEqual(config.get(key), Config.DEFAULT_CONFIG[key])
        for value in (None, [], 'cookie', 123, {'NID_AUT': 'a\nb', 'NID_SES': []}):
            self.write({'cookies': value})
            self.assertEqual(Config().get_cookies_netscape(), '')

    def test_save_keeps_one_owner_only_backup_of_exact_original(self):
        original = self.write({'concurrent_downloads': 'bad', 'cookies': {'NID_AUT': 'private'}})
        config = Config()
        config.save()
        backups = list(self.path.parent.glob('config.recovery.*.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        if __import__('os').name != 'nt':
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        config.save()
        self.assertEqual(len(list(self.path.parent.glob('config.recovery.*.json'))), 1)
        self.assertEqual(Config().get('concurrent_downloads'), 1)

    def test_backup_failure_does_not_overwrite_original(self):
        from unittest.mock import patch
        original = self.write([])
        config = Config()
        with patch.object(config, '_preserve_recovery_source', side_effect=OSError('denied')):
            config.save()
        self.assertEqual(self.path.read_bytes(), original)

    def test_valid_legacy_migration_and_current_file_precedence(self):
        import json
        legacy = self.home / '.chzzk-downloader' / 'config.json'
        legacy.parent.mkdir()
        value = {'download_path': str(self.home / 'clips'), 'concurrent_downloads': 3,
                 'cookies': {'NID_AUT': 'a', 'NID_SES': 'b'}}
        legacy.write_text(json.dumps(value))
        config = Config()
        self.assertEqual(config.get('concurrent_downloads'), 3)
        self.assertEqual(config.get_cookie_header(), 'NID_AUT=a; NID_SES=b')
        config.save()
        self.assertEqual(Config().get('concurrent_downloads'), 3)
        self.assertFalse(list(self.path.parent.glob('config.recovery.*.json')))
        self.write([])
        config = Config()
        self.assertEqual(config.get('concurrent_downloads'), 1)
        self.assertEqual(config.get_cookie_header(), '')

    def test_recovery_messages_never_log_cookie_values(self):
        import contextlib
        import io
        self.path.write_text('{"cookies": "DO_NOT_LOG_THIS"')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            Config()
        self.assertNotIn('DO_NOT_LOG_THIS', output.getvalue())


if __name__ == "__main__":
    unittest.main()
