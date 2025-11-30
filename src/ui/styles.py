"""
Modern UI Styles for Chzzk Downloader
"""

# Color palette
COLORS = {
    'primary': '#6366f1',      # Indigo
    'primary_hover': '#4f46e5',
    'secondary': '#8b5cf6',    # Purple
    'background': '#1e1e2e',   # Dark background
    'surface': '#2a2a3e',      # Card background
    'surface_light': '#363650',
    'text': '#e0e0e0',         # Light text
    'text_secondary': '#a0a0b0',
    'success': '#10b981',      # Green
    'error': '#ef4444',        # Red
    'warning': '#f59e0b',      # Orange
    'border': '#3a3a4e',
}

def get_stylesheet() -> str:
    """Get the complete application stylesheet"""
    return f"""
    /* Global Styles */
    QWidget {{
        background-color: {COLORS['background']};
        color: {COLORS['text']};
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 13px;
    }}
    
    /* Main Window */
    QMainWindow {{
        background-color: {COLORS['background']};
    }}
    
    /* Push Buttons */
    QPushButton {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 600;
        min-height: 36px;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS['primary_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: #3730a3;
    }}
    
    QPushButton:disabled {{
        background-color: {COLORS['surface_light']};
        color: {COLORS['text_secondary']};
    }}
    
    QPushButton#secondaryButton {{
        background-color: {COLORS['surface']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['border']};
    }}
    
    QPushButton#secondaryButton:hover {{
        background-color: {COLORS['surface_light']};
    }}
    
    QPushButton#dangerButton {{
        background-color: {COLORS['error']};
    }}
    
    QPushButton#dangerButton:hover {{
        background-color: #dc2626;
    }}
    
    /* Line Edit (Text Input) */
    QLineEdit {{
        background-color: {COLORS['surface']};
        border: 2px solid {COLORS['border']};
        border-radius: 6px;
        padding: 10px 12px;
        color: {COLORS['text']};
        selection-background-color: {COLORS['primary']};
    }}
    
    QLineEdit:focus {{
        border-color: {COLORS['primary']};
    }}
    
    /* Combo Box (Dropdown) */
    QComboBox {{
        background-color: {COLORS['surface']};
        border: 2px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px 12px;
        color: {COLORS['text']};
        min-height: 36px;
    }}
    
    QComboBox:hover {{
        border-color: {COLORS['primary']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {COLORS['text']};
        margin-right: 10px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['primary']};
        color: {COLORS['text']};
    }}
    
    /* Progress Bar */
    QProgressBar {{
        background-color: {COLORS['surface']};
        border: none;
        border-radius: 4px;
        text-align: center;
        height: 8px;
    }}
    
    QProgressBar::chunk {{
        background-color: {COLORS['primary']};
        border-radius: 4px;
    }}
    
    /* Labels */
    QLabel {{
        color: {COLORS['text']};
        background-color: transparent;
    }}
    
    QLabel#titleLabel {{
        font-size: 16px;
        font-weight: 700;
        color: {COLORS['text']};
    }}
    
    QLabel#subtitleLabel {{
        font-size: 12px;
        color: {COLORS['text_secondary']};
    }}
    
    /* Group Box */
    QGroupBox {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: 600;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {COLORS['text']};
    }}
    
    /* List Widget */
    QListWidget {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px;
    }}
    
    QListWidget::item {{
        background-color: transparent;
        border: none;
        padding: 4px;
    }}
    
    QListWidget::item:selected {{
        background-color: {COLORS['surface_light']};
        border-radius: 4px;
    }}
    
    /* Scroll Bar */
    QScrollBar:vertical {{
        background-color: {COLORS['surface']};
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {COLORS['surface_light']};
        border-radius: 6px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['border']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    /* Menu Bar */
    QMenuBar {{
        background-color: {COLORS['background']};
        color: {COLORS['text']};
        border-bottom: 1px solid {COLORS['border']};
    }}
    
    QMenuBar::item {{
        padding: 6px 12px;
        background-color: transparent;
    }}
    
    QMenuBar::item:selected {{
        background-color: {COLORS['surface']};
    }}
    
    QMenu {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
    }}
    
    QMenu::item {{
        padding: 8px 24px;
    }}
    
    QMenu::item:selected {{
        background-color: {COLORS['primary']};
    }}
    
    /* Dialog */
    QDialog {{
        background-color: {COLORS['background']};
    }}
    
    /* Tab Widget */
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        background-color: {COLORS['surface']};
    }}
    
    QTabBar::tab {{
        background-color: {COLORS['surface']};
        color: {COLORS['text_secondary']};
        padding: 10px 20px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    
    QTabBar::tab:selected {{
        background-color: {COLORS['primary']};
        color: white;
    }}
    
    QTabBar::tab:hover:!selected {{
        background-color: {COLORS['surface_light']};
    }}
    """
