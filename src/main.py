"""
Chzzk Downloader - Main Entry Point
"""
import sys
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

from ui.main_window import MainWindow
from ui.styles import get_stylesheet
from core.config import Config


def main():
    """Main application entry point"""
    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Chzzk Downloader")
    app.setOrganizationName("ChzzkDownloader")
    app.setApplicationVersion("1.0.0")
    
    # Apply stylesheet
    app.setStyleSheet(get_stylesheet())
    
    # Create event loop for async support
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Load configuration
    config = Config()
    
    # Create and show main window
    window = MainWindow(config)
    window.show()
    
    # Run application
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
