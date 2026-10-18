# UI polish checks

This is a separate UI-only change on the v2.0.12 packaging base. No download/network, configuration, packaging, or release behavior changes.

- Full offline suite: 113 passed, 11 subtests passed.
- New focused tests: palette text contrast (4.5:1 minimum), empty-state visibility, repeated input-mode switching with preserved URL, status wrapping, Cancel/Remove signal, and completion action visibility.
- Offscreen visual QA: empty, batch, metadata, minimum 1000×750 with time-range selection, settings, warning dialog, menu, keyboard focus, and active/completed/error download items.
- Independent review covered the diff and empty/video/settings renders. Warning dialog and menu are explicitly dark and readable (QDialog/QMenu stylesheet rules).
- Native macOS/Windows rendering not verified here. No live downloads used for this presentation-only QA.

Reproduce screenshots with installed app dependencies:

    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python qa/render_ui.py

PNG previews are local QA output and deliberately excluded from git.
