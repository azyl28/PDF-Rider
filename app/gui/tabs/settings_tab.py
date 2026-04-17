from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout


class SettingsTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Ustawienia - funkcja w przygotowaniu"))