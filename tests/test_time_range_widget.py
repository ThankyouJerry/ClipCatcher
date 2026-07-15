import os
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtWidgets import QApplication

from ui.time_range_widget import TimeRangeWidget


class TimeRangeWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_widget(self, duration, enforce_limit):
        widget = TimeRangeWidget()
        widget.set_duration(duration, enforce_limit=enforce_limit)
        widget.radio_partial.setChecked(True)
        return widget

    def test_accepts_target_range_when_fast_replay_duration_is_provisional(self):
        widget = self.make_widget(7799, enforce_limit=False)
        widget.start_input.setText('01:05:12')
        widget.end_input.setText('04:03:00')

        self.assertEqual(
            widget.get_time_range(),
            {'start': 3912.0, 'end': 14580.0},
        )

    def test_reliable_duration_still_rejects_out_of_range_end(self):
        widget = self.make_widget(7799, enforce_limit=True)
        widget.start_input.setText('01:05:12')
        widget.end_input.setText('04:03:00')

        with self.assertRaisesRegex(ValueError, '종료 시간'):
            widget.get_time_range()


if __name__ == '__main__':
    unittest.main()
