from PyQt5.QtWidgets import QDialog


class OcrDialog(QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle("OCR")
        self.resize(400, 300)
