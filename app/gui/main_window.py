from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from datetime import datetime
from app.gui.tabs.pdf_master_tab import PdfMasterTab
from app.gui.tabs.converter_tab import ConverterTab
from app.gui.tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Rider Nex")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        self.status_label = None
        self.setup_ui()
        self.apply_style()

    def setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # MENU
        self.create_menu_bar()
        layout.addWidget(self.menu_bar)

        # KONTENER ZAKŁADEK
        self.create_tab_bar()
        layout.addWidget(self.tab_container)

        # LINIA
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #313244; max-height: 1px;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # STOS ZAKŁADEK - TYLKO 3 DZIAŁAJĄCE
        self.stacked = QStackedWidget()
        self.stacked.addWidget(PdfMasterTab(self))
        self.stacked.addWidget(ConverterTab(self))
        self.stacked.addWidget(SettingsTab(self))
        layout.addWidget(self.stacked)

        # STATUS BAR
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(28)
        self.status_label = QLabel("Gotowy")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(QLabel(f"{datetime.now().strftime('%H:%M')}"))
        self.status_bar.addPermanentWidget(QLabel(f"{datetime.now().strftime('%d/%m/%Y')}"))
        layout.addWidget(self.status_bar)

        self.setCentralWidget(central)
        self.switch_tab(0)

    def create_menu_bar(self):
        self.menu_bar = QMenuBar()
        self.menu_bar.setFixedHeight(32)
        for name in ["Plik", "Edycja", "Widok", "Narzedzia", "Pomoc"]:
            self.menu_bar.addMenu(name)

    def create_tab_bar(self):
        """Ładne zakładki - tylko 3 działające"""
        self.tab_container = QWidget()
        self.tab_container.setFixedHeight(70)
        self.tab_container.setStyleSheet("background-color: #1e1e2e;")
        
        layout = QHBoxLayout(self.tab_container)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # Spacer przesuwający zakładki w prawo
        spacer = QWidget()
        spacer.setFixedWidth(820)
        layout.addWidget(spacer)
        
        self.tab_btns = []
        # TYLKO 3 ZAKŁADKI
        texts = ["PDF Master", "Konwerter", "Ustawienia"]
        
        for i, text in enumerate(texts):
            btn = QPushButton(text)
            btn.setFixedSize(150, 40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda ch, idx=i: self.switch_tab(idx))
            
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cdd6f4;
                    border: none;
                    border-radius: 0px;
                    padding: 8px 16px;
                    font-size: 13px;
                    font-weight: normal;
                }
                QPushButton:hover {
                    color: #89b4fa;
                }
            """)
            layout.addWidget(btn)
            self.tab_btns.append(btn)
        
        layout.addStretch()

    def switch_tab(self, idx):
        self.stacked.setCurrentIndex(idx)
        
        # Styl aktywnej zakładki
        for i, btn in enumerate(self.tab_btns):
            if i == idx:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #89b4fa;
                        border: none;
                        border-bottom: 2px solid #89b4fa;
                        padding: 8px 16px;
                        font-size: 13px;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #cdd6f4;
                        border: none;
                        border-radius: 0px;
                        padding: 8px 16px;
                        font-size: 13px;
                        font-weight: normal;
                    }
                    QPushButton:hover {
                        color: #89b4fa;
                    }
                """)
        
        if self.status_label:
            self.status_label.setText(f"Przelaczono na {self.tab_btns[idx].text()}")

    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #181825; }
            QMenuBar { background-color: #1e1e2e; color: #cdd6f4; border-bottom: 1px solid #313244; }
            QMenuBar::item:selected { background-color: #89b4fa; color: #1a1a2e; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 8px; padding: 8px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
            QStatusBar { background-color: #1e1e2e; color: #a6adc8; border-top: 1px solid #313244; }
            QLabel { color: #cdd6f4; }
            
            QDialog {
                background-color: #f0f0f0;
            }
            QDialog QLabel {
                color: #000000;
                font-size: 12px;
            }
            QDialog QPushButton {
                background-color: #313244;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QDialog QPushButton:hover {
                background-color: #89b4fa;
                color: #1a1a2e;
            }
            QDialog QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 6px;
            }
            QDialog QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #313244;
                border-radius: 4px;
            }
            QDialog QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #313244;
                border-radius: 4px;
                padding: 4px;
            }
            QDialog QCheckBox {
                color: #000000;
            }
            QDialog QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #313244;
                border-radius: 4px;
            }
            
            QMessageBox {
                background-color: #f0f0f0;
            }
            QMessageBox QLabel {
                color: #000000;
                font-size: 12px;
            }
            QMessageBox QPushButton {
                background-color: #313244;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #89b4fa;
                color: #1a1a2e;
            }
            
            QInputDialog {
                background-color: #f0f0f0;
            }
            QInputDialog QLabel {
                color: #000000;
            }
            QInputDialog QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #313244;
                border-radius: 4px;
            }
        """)