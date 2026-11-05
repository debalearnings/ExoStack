"""
Central visual theme for the ROS2 ExoStack GUI (PACE).

This module is purely cosmetic. It defines a colour palette and a global
Qt Style Sheet (QSS) and applies them at the QApplication level. No widget
logic, signals, or behaviour are touched anywhere — importing and calling
apply_theme(app) only changes how things look.

Design language: a calm, high-contrast "clinical control-room" dark theme
with a single confident teal accent, hairline borders, soft rounded cards
and clear focus states — appropriate for a wearable assistive-device console.
"""

from PyQt5.QtGui import QColor, QPalette, QFont, QFontDatabase
from PyQt5.QtCore import Qt
import os

RES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources").replace("\\", "/")


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COLORS = {
    "bg_0":         "#0F141A",   # app background (deepest)
    "bg_1":         "#161D26",   # panels / cards
    "bg_2":         "#1C2530",   # inputs / elevated
    "bg_3":         "#232E3B",   # hover
    "border":       "#2A3543",   # hairline
    "border_strong":"#3A4A5E",
    "text":         "#E8EEF4",   # primary text
    "text_muted":   "#94A2B3",   # secondary text
    "text_faint":   "#5E6E80",
    "accent":       "#2DD4BF",   # teal — primary accent
    "accent_hi":    "#54E8D6",   # accent hover / highlight
    "accent_dim":   "#15786E",   # accent pressed / dim fill
    "accent_glow":  "#2DD4BF",
    "info":         "#5AA9FF",
    "success":      "#34D399",   # running / ok
    "warning":      "#F4B14C",
    "danger":       "#F2706B",   # stop / error
}


def _pick_font_family():
    """Choose the nicest available sans-serif without requiring extra packages."""
    try:
        available = set(QFontDatabase().families())
    except Exception:
        available = set()
    for fam in ("Inter", "Segoe UI", "Roboto", "Ubuntu", "Noto Sans",
                "DejaVu Sans", "Cantarell", "Helvetica Neue", "Arial"):
        if fam in available:
            return fam
    return "Sans Serif"


def build_stylesheet(c=COLORS):
    """Return the global QSS string built from the palette."""
    return f"""
    /* ---------- base ---------- */
    QWidget {{
        background-color: {c['bg_0']};
        color: {c['text']};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background-color: {c['bg_0']}; }}

    QToolTip {{
        background-color: {c['bg_2']};
        color: {c['text']};
        border: 1px solid {c['border_strong']};
        border-radius: 6px;
        padding: 5px 8px;
    }}

    /* ---------- tabs ---------- */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: 12px;
        top: -1px;
        background: {c['bg_0']};
    }}
    QTabWidget::tab-bar {{
        left: 8px;
    }}
    QTabBar {{
        qproperty-drawBase: 0;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {c['text_muted']};
        padding: 10px 30px;
        margin-right: 6px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: 13px;
        font-weight: 600;
        min-width: 96px;
    }}
    QTabBar::tab:hover {{ color: {c['text']}; }}
    QTabBar::tab:selected {{
        color: {c['accent_hi']};
        border-bottom: 2px solid {c['accent']};
    }}

    /* ---------- group boxes / cards ---------- */
    QGroupBox {{
        background-color: {c['bg_1']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        margin-top: 14px;
        padding: 10px 8px 8px 8px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 11px;
        top: 2px;
        padding: 1px 8px;
        color: {c['accent_hi']};
        background-color: {c['bg_2']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.4px;
    }}

    /* ---------- buttons ---------- */
    QPushButton {{
        background-color: {c['bg_2']};
        color: {c['text']};
        border: 1px solid {c['border_strong']};
        border-radius: 8px;
        padding: 6px 8px;
        font-size: 11px;
        font-weight: 600;
        min-height: 15px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_3']};
        border: 1px solid {c['accent']};
        color: {c['accent_hi']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent_dim']};
        border: 1px solid {c['accent']};
        color: #FFFFFF;
    }}
    QPushButton:disabled {{
        background-color: {c['bg_1']};
        color: {c['text_faint']};
        border: 1px solid {c['border']};
    }}
    QPushButton:checked {{
        background-color: {c['accent_dim']};
        border: 1px solid {c['accent']};
        color: #FFFFFF;
    }}
    QPushButton[role="danger"] {{
        color: {c['danger']};
        border: 1px solid {c['border_strong']};
    }}
    QPushButton[role="danger"]:hover {{
        background-color: #34222B;
        border: 1px solid {c['danger']};
        color: #FFC4C0;
    }}
    QPushButton[role="danger"]:pressed {{
        background-color: {c['danger']};
        border: 1px solid {c['danger']};
        color: #FFFFFF;
    }}

    /* ---------- text inputs ---------- */
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_2']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 7px;
        padding: 5px 8px;
        selection-background-color: {c['accent_dim']};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {c['accent']};
        background-color: {c['bg_1']};
    }}
    QLineEdit::placeholder {{ color: {c['text_faint']}; }}
    QLineEdit:disabled {{ color: {c['text_faint']}; background-color: {c['bg_1']}; }}

    /* ---------- combo boxes ---------- */
    QComboBox {{
        background-color: {c['bg_2']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 7px;
        padding: 5px 8px;
        min-height: 16px;
    }}
    QComboBox:hover {{ border: 1px solid {c['border_strong']}; }}
    QComboBox:focus {{ border: 1px solid {c['accent']}; }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 26px;
        border-left: 1px solid {c['border']};
        border-top-right-radius: 7px;
        border-bottom-right-radius: 7px;
    }}
    QComboBox::down-arrow {{
        image: url({RES_DIR}/chevron_down.png);
        width: 15px;
        height: 15px;
    }}
    QComboBox::down-arrow:hover {{
        image: url({RES_DIR}/chevron_down_accent.png);
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_1']};
        color: {c['text']};
        border: 1px solid {c['border_strong']};
        border-radius: 8px;
        outline: none;
        selection-background-color: {c['accent']};
        selection-color: {c['bg_0']};
        padding: 4px;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 24px;
        padding: 3px 8px;
        border-radius: 6px;
        color: {c['text']};
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {c['accent']};
        color: {c['bg_0']};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {c['accent']};
        color: {c['bg_0']};
    }}

    /* ---------- check boxes ---------- */
    QCheckBox {{ spacing: 8px; color: {c['text']}; }}
    QCheckBox::indicator {{
        width: 17px; height: 17px;
        border: 1px solid {c['border_strong']};
        border-radius: 5px;
        background-color: {c['bg_2']};
    }}
    QCheckBox::indicator:hover {{ border: 1px solid {c['accent']}; }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent']};
        border: 1px solid {c['accent']};
    }}

    /* ---------- labels ---------- */
    QLabel {{ background: transparent; color: {c['text']}; }}

    /* ---------- scroll areas & bars ---------- */
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QAbstractScrollArea {{ background: transparent; }}

    QScrollBar:vertical {{
        background: transparent;
        width: 11px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['bg_3']};
        border-radius: 5px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {c['border_strong']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 11px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['bg_3']};
        border-radius: 5px;
        min-width: 28px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {c['border_strong']}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

    /* ---------- menus ---------- */
    QMenu {{
        background-color: {c['bg_1']};
        color: {c['text']};
        border: 1px solid {c['border_strong']};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 22px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{ background-color: {c['accent_dim']}; color: #FFFFFF; }}
    QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 8px; }}

    QHeaderView::section {{
        background-color: {c['bg_2']};
        color: {c['text_muted']};
        border: none;
        border-bottom: 1px solid {c['border']};
        padding: 6px 8px;
        font-weight: 600;
    }}

    /* ---------- tree / list (topic explorer) ---------- */
    QTreeWidget, QTreeView, QListWidget, QListView {{
        background-color: {c['bg_1']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        outline: none;
        padding: 4px;
    }}
    QTreeWidget::item, QTreeView::item {{
        padding: 3px 2px;
        border-radius: 5px;
    }}
    QTreeWidget::item:hover, QTreeView::item:hover {{ background: {c['bg_3']}; }}
    QTreeWidget::item:selected, QTreeView::item:selected {{
        background: {c['accent']};
        color: {c['bg_0']};
    }}
    """


def apply_theme(app):
    """Apply the Fusion base style, a dark palette, the app font and the QSS."""
    try:
        app.setStyle("Fusion")
    except Exception:
        pass

    c = COLORS
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["bg_0"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["bg_2"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["bg_1"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["bg_2"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["bg_2"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.Highlight, QColor(c["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor(c["bg_0"]))
    pal.setColor(QPalette.Link, QColor(c["info"]))
    pal.setColor(QPalette.PlaceholderText, QColor(c["text_faint"]))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(c["text_faint"]))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(c["text_faint"]))
    app.setPalette(pal)

    font = QFont(_pick_font_family())
    font.setPixelSize(13)
    app.setFont(font)

    app.setStyleSheet(build_stylesheet(c))
