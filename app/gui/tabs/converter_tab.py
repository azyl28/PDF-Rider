from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout


class ConverterTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Konwerter - funkcja w przygotowaniu"))