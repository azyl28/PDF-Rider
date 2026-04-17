from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPen, QColor, QFont
import os
import fitz
import tempfile
import shutil
from datetime import datetime

from app.gui.widgets.ocr_dialog import OcrDialog
from app.tools.edit_tools import PdfEditTools
from app.tools.page_tools import PageTools
from app.tools.security_tools import SecurityTools
from app.tools.settings_tools import SettingsTools

# ============================================================================
# STYL DLA OKIENEK DIALOGOWYCH (CZARNY TEKST)
# ============================================================================
MESSAGE_STYLE = """
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
"""


def show_info(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Information)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.exec_()


def show_warning(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Warning)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.exec_()


def show_error(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Critical)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.exec_()


def show_question(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Question)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    return msg.exec_()


# ============================================================================
# OKIENKO DODAWANIA STRONY (z wyborem pozycji)
# ============================================================================
class AddPageDialog(QDialog):
    def __init__(self, parent=None, current_page=0, total_pages=0):
        super().__init__(parent)
        self.setWindowTitle("Dodaj stronę")
        self.setMinimumSize(450, 320)
        self.current_page = current_page
        self.total_pages = total_pages
        self.selected_file = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Typ dodawania
        layout.addWidget(QLabel("Typ strony do dodania:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Pusta strona (A4)", "Strona z pliku PDF"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Ramka dla opcji z pliku PDF
        self.file_frame = QFrame()
        self.file_frame.setVisible(False)
        file_layout = QVBoxLayout(self.file_frame)
        
        file_layout.addWidget(QLabel("Plik PDF:"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Wybierz plik PDF...")
        file_layout.addWidget(self.file_path_edit)
        
        self.browse_btn = QPushButton("Przeglądaj...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        
        file_layout.addWidget(QLabel("Numer strony do dodania:"))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setValue(1)
        file_layout.addWidget(self.page_spin)
        
        layout.addWidget(self.file_frame)
        
        # Pozycja dodania
        layout.addWidget(QLabel("Gdzie dodać stronę:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "Na koniec dokumentu",
            "Przed bieżącą stroną",
            "Po bieżącej stronie",
            "Na początku dokumentu"
        ])
        layout.addWidget(self.position_combo)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Dodaj")
        self.add_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.add_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #f0f0f0; }
            QLabel { color: #000000; }
            QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #313244; border-radius: 4px; padding: 6px; }
            QComboBox { background-color: #ffffff; color: #000000; border: 1px solid #313244; border-radius: 4px; padding: 4px; }
            QSpinBox { background-color: #ffffff; color: #000000; border: 1px solid #313244; border-radius: 4px; }
            QPushButton { background-color: #313244; color: #ffffff; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def on_type_changed(self, index):
        self.file_frame.setVisible(index == 1)
        
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF", "", "*.pdf")
        if path:
            self.selected_file = path
            self.file_path_edit.setText(path)
            try:
                doc = fitz.open(path)
                self.page_spin.setRange(1, len(doc))
                doc.close()
            except:
                pass
            
    def is_blank_page(self):
        return self.type_combo.currentIndex() == 0
        
    def get_pdf_path(self):
        return self.file_path_edit.text()
        
    def get_page_number(self):
        return self.page_spin.value() - 1  # 0-indexed
        
    def get_insert_position(self):
        """Zwraca pozycję wstawienia: 0=koniec, 1=przed bieżącą, 2=po bieżącej, 3=początek"""
        return self.position_combo.currentIndex()


# ============================================================================
# WIDZET PODGLADU PDF
# ============================================================================
class ClickableLabel(QLabel):
    mouse_pressed = pyqtSignal(int, QPoint)  # page_index, pos
    mouse_moved = pyqtSignal(int, QPoint)
    mouse_released = pyqtSignal(int, QPoint)
    
    def __init__(self, pixmap, page_index, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.original_pixmap = pixmap
        self.page_index = page_index
        self.selection_start = None
        self.selection_end = None
        
    def update_selection(self, start, end):
        self.selection_start = start
        self.selection_end = end
        self.update()
        
    def clear_selection(self):
        self.selection_start = None
        self.selection_end = None
        self.setPixmap(self.original_pixmap)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selection_start and self.selection_end:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(137, 180, 250, 200), 2))
            painter.setBrush(QColor(137, 180, 250, 50))
            rect = QRect(self.selection_start, self.selection_end).normalized()
            painter.drawRect(rect)
            painter.end()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed.emit(self.page_index, event.pos())
            
    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(self.page_index, event.pos())
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_released.emit(self.page_index, event.pos())


class PdfViewer(QScrollArea):
    text_selected = pyqtSignal(QRect, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e2e;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e1e2e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #45475a;
                border-radius: 4px;
                min-height: 30px;
            }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1e1e2e;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setWidget(self.container)
        
        self.current_doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom = 1.0
        self.pages_labels = []
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        self.tool_mode = "select"
        self.pending_text = None
        self.pending_text_size = 12
        self.pending_comment = None
        self.pending_note = None
        self.pending_signature = None
        self.pending_remove = False
        self.pending_image = None
        self.pending_shape = None
        self.pending_font_change = False
        
    def load_document(self, doc):
        self.clear()
        self.current_doc = doc
        self.total_pages = len(doc) if doc else 0
        self.current_page = 0
        if not doc:
            return
        for i in range(self.total_pages):
            page = doc[i]
            matrix = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=matrix)
            img = QPixmap()
            img.loadFromData(pix.tobytes())
            
            label = ClickableLabel(img, i, self)
            label.setAlignment(Qt.AlignCenter)
            label.mouse_pressed.connect(self.on_page_mouse_press)
            label.mouse_moved.connect(self.on_page_mouse_move)
            label.mouse_released.connect(self.on_page_mouse_release)
            self.layout.addWidget(label)
            self.pages_labels.append(label)

    def refresh_all_pages(self):
        if not self.current_doc:
            return
        for i, label in enumerate(self.pages_labels):
            page = self.current_doc[i]
            matrix = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=matrix)
            img = QPixmap()
            img.loadFromData(pix.tobytes())
            label.original_pixmap = img
            label.setPixmap(img)
            label.clear_selection()

    def render_page(self):
        # For single page refresh if needed
        pass

    def set_tool_mode(self, mode):
        self.tool_mode = mode
        
    def on_page_mouse_press(self, page_idx, pos):
        self.current_page = page_idx
        if self.tool_mode == "select":
            self.selecting = True
            self.selection_start = pos
            self.selection_end = pos
        elif self.tool_mode == "text" and self.pending_text:
            self.add_text_at_position(page_idx, self.pending_text, pos, self.pending_text_size)
            self.pending_text = None
            self.tool_mode = "select"
        elif self.tool_mode == "comment" and self.pending_comment:
            self.add_comment_at_position(page_idx, self.pending_comment, pos)
            self.pending_comment = None
            self.tool_mode = "select"
        elif self.tool_mode == "note" and self.pending_note:
            self.add_note_at_position(page_idx, self.pending_note, pos)
            self.pending_note = None
            self.tool_mode = "select"
        elif self.tool_mode == "signature" and self.pending_signature:
            self.add_signature_at_position(page_idx, self.pending_signature, pos)
            self.pending_signature = None
            self.tool_mode = "select"
        elif self.tool_mode == "remove" and self.pending_remove:
            # Usuwanie wymaga zaznaczenia obszaru, więc to w on_mouse_release
            pass
        elif self.tool_mode == "image" and self.pending_image:
            self.add_image_at_position(page_idx, self.pending_image, pos)
            self.pending_image = None
            self.tool_mode = "select"
        elif self.tool_mode == "shape" and self.pending_shape:
            self.add_shape_at_position(page_idx, self.pending_shape, pos)
            self.pending_shape = None
            self.tool_mode = "select"
            
    def on_page_mouse_move(self, page_idx, pos):
        if self.selecting and self.tool_mode == "select" and page_idx == self.current_page:
            self.selection_end = pos
            if self.pages_labels[page_idx]:
                self.pages_labels[page_idx].update_selection(self.selection_start, self.selection_end)
            
    def on_page_mouse_release(self, page_idx, pos):
        if self.selecting and self.tool_mode == "select" and page_idx == self.current_page:
            self.selecting = False
            self.selection_end = pos
            if self.selection_start and self.selection_end:
                x0 = min(self.selection_start.x(), self.selection_end.x()) / self.zoom
                y0 = min(self.selection_start.y(), self.selection_end.y()) / self.zoom
                x1 = max(self.selection_start.x(), self.selection_end.x()) / self.zoom
                y1 = max(self.selection_start.y(), self.selection_end.y()) / self.zoom
                rect = QRect(int(x0), int(y0), int(x1-x0), int(y1-y0))
                self.text_selected.emit(rect, "")
            if self.pages_labels[page_idx]:
                self.pages_labels[page_idx].clear_selection()
            
    def add_text_at_position(self, page_idx, text, pos, font_size=12):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        page.insert_text((x, y), text, fontsize=font_size, fontname="helv", color=(0, 0, 0))
        self.refresh_all_pages()
        
    def add_comment_at_position(self, page_idx, text, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        annot = page.add_text_annot((x, y), text)
        annot.update()
        self.refresh_all_pages()
        
    def add_note_at_position(self, page_idx, text, pos):
        self.add_comment_at_position(page_idx, text, pos)
        
    def add_signature_at_position(self, page_idx, image_path, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        rect = fitz.Rect(x, y, x + 150, y + 75)
        page.insert_image(rect, filename=image_path)
        self.refresh_all_pages()

    def add_image_at_position(self, page_idx, image_path, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        rect = fitz.Rect(x, y, x + 200, y + 150)
        page.insert_image(rect, filename=image_path)
        self.refresh_all_pages()

    def add_shape_at_position(self, page_idx, shape_type, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        rect = fitz.Rect(x, y, x + 100, y + 100)

        if shape_type == "rectangle":
            page.draw_rect(rect, color=(0, 0, 0), width=2)
        elif shape_type == "circle":
            center = (x + 50, y + 50)
            page.draw_circle(center, 50, color=(0, 0, 0), width=2)
        self.refresh_all_pages()
            
    def set_zoom(self, zoom):
        self.zoom = max(0.3, min(3.0, zoom))
        self.refresh_all_pages()

    def go_to_page(self, page):
        if 0 <= page < self.total_pages:
            self.current_page = page
            self.ensureWidgetVisible(self.pages_labels[page])
            return True
        return False

    def next_page(self):
        if self.current_page + 1 < self.total_pages:
            self.current_page += 1
            self.ensureWidgetVisible(self.pages_labels[self.current_page])

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.ensureWidgetVisible(self.pages_labels[self.current_page])

    def clear(self):
        for label in self.pages_labels:
            label.deleteLater()
        self.pages_labels.clear()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_zoom(self.zoom * 1.1)
            else:
                self.set_zoom(self.zoom / 1.1)
        else:
            super().wheelEvent(event)


# ============================================================================
# PANEL MINIATUR
# ============================================================================
class ThumbnailPanel(QWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_doc = None
        self.thumb_buttons = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #181825;
            }
            QScrollBar:vertical {
                background-color: #181825;
                width: 6px;
                border-radius: 3px;
            }
        """)
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #181825;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def load_document(self, doc):
        self.clear()
        self.current_doc = doc
        if not doc:
            return
        for i in range(len(doc)):
            try:
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.1, 0.1))
                img = QPixmap()
                img.loadFromData(pix.tobytes())
                
                btn = QPushButton()
                btn.setIcon(QIcon(img))
                btn.setIconSize(img.size())
                btn.setFixedSize(img.size())
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, p=i: self.page_selected.emit(p))
                btn.setStyleSheet("""
                    QPushButton {
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #313244;
                    }
                """)
                
                label = QLabel(f"{i+1}")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("color: #89b4fa; font-size: 10px;")
                
                item = QWidget()
                item_layout = QVBoxLayout(item)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(2)
                item_layout.addWidget(btn)
                item_layout.addWidget(label)
                
                self.container_layout.addWidget(item)
                self.thumb_buttons.append(item)
            except:
                pass

    def highlight_page(self, page_num):
        for i, item in enumerate(self.thumb_buttons):
            if i == page_num:
                item.setStyleSheet("background-color: #313244; border-radius: 5px;")
            else:
                item.setStyleSheet("")

    def clear(self):
        for i in reversed(range(self.container_layout.count())):
            w = self.container_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.thumb_buttons.clear()


# ============================================================================
# OKIENKO DODAWANIA HASŁA (z przyciskiem "Pokaż hasło")
# ============================================================================
class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zabezpiecz PDF hasłem")
        self.setMinimumSize(350, 250)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        label1 = QLabel("Ustaw hasło dla PDF:")
        label1.setStyleSheet("color: #000000; font-weight: normal;")
        layout.addWidget(label1)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("color: #000000; background-color: #ffffff;")
        layout.addWidget(self.password_input)
        
        # Przycisk "Pokaż hasło"
        self.show_password_check = QCheckBox("Pokaż hasło")
        self.show_password_check.setStyleSheet("color: #000000;")
        self.show_password_check.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password_check)
        
        label2 = QLabel("Potwierdź hasło:")
        label2.setStyleSheet("color: #000000; font-weight: normal;")
        layout.addWidget(label2)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setStyleSheet("color: #000000; background-color: #ffffff;")
        layout.addWidget(self.confirm_input)
        
        self.encrypt_check = QCheckBox("Szyfruj (AES-256)")
        self.encrypt_check.setStyleSheet("color: #000000;")
        self.encrypt_check.setChecked(True)
        layout.addWidget(self.encrypt_check)
        
        self.overwrite_check = QCheckBox("Zastąp oryginalny plik")
        self.overwrite_check.setStyleSheet("color: #000000;")
        self.overwrite_check.setChecked(False)
        layout.addWidget(self.overwrite_check)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Zabezpiecz")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("background-color: #f0f0f0;")
        
    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.confirm_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.confirm_input.setEchoMode(QLineEdit.Password)
        
    def get_password(self):
        return self.password_input.text()
        
    def get_confirm(self):
        return self.confirm_input.text()
        
    def is_encrypt(self):
        return self.encrypt_check.isChecked()
        
    def overwrite_original(self):
        return self.overwrite_check.isChecked()


# ============================================================================
# OKIENKO DODAWANIA TEKSTU
# ============================================================================
class TextInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj tekst")
        self.setMinimumSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        label = QLabel("Wprowadź tekst:")
        label.setStyleSheet("color: #000000;")
        layout.addWidget(label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("color: #000000; background-color: #ffffff;")
        layout.addWidget(self.text_edit)
        
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Rozmiar:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(12)
        font_layout.addWidget(self.size_spin)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Dodaj")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("background-color: #f0f0f0;")
        
    def get_text(self):
        return self.text_edit.toPlainText()
        
    def get_font_size(self):
        return self.size_spin.value()


# ============================================================================
# OKIENKO DODAWANIA NUMERACJI
# ============================================================================
class NumberingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Numeracja stron")
        self.setMinimumSize(300, 150)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Numer startowy:"))
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        layout.addWidget(self.start_spin)
        
        layout.addWidget(QLabel("Pozycja:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Dół strony (środek)", "Dół strony (lewo)", "Dół strony (prawo)", "Góra strony (środek)"])
        layout.addWidget(self.position_combo)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Dodaj")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("background-color: #f0f0f0; QLabel { color: #000000; }")
        
    def get_start(self):
        return self.start_spin.value()
        
    def get_position(self):
        return self.position_combo.currentIndex()


# ============================================================================
# OKIENKO WERYFIKACJI PODPISU
# ============================================================================
class SignatureVerificationDialog(QDialog):
    def __init__(self, parent=None, doc=None, doc_path=None):
        super().__init__(parent)
        self.setWindowTitle("Weryfikacja podpisu elektronicznego")
        self.setMinimumSize(500, 400)
        self.doc = doc
        self.doc_path = doc_path
        self.setup_ui()
        self.verify_signature()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel("Sprawdzanie podpisu elektronicznego...")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #000000;")
        layout.addWidget(self.title_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("color: #000000; background-color: #ffffff; font-family: monospace;")
        layout.addWidget(self.result_text)
        
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.setStyleSheet("background-color: #f0f0f0;")
        
    def verify_signature(self):
        result = "=== WERYFIKACJA PODPISU ELEKTRONICZNEGO ===\n\n"
        
        if not self.doc:
            result += "❌ Brak otwartego dokumentu PDF.\n"
            self.result_text.setText(result)
            return
            
        try:
            if hasattr(self.doc, 'is_signed'):
                is_signed = self.doc.is_signed
                result += f"📄 Dokument zawiera podpis: {'TAK' if is_signed else 'NIE'}\n\n"
                
                if is_signed:
                    result += "✅ Podpis elektroniczny został znaleziony.\n"
                    try:
                        result += "\n🔍 Informacje o podpisie:\n"
                        result += "   - Typ: PAdES (PDF Advanced Electronic Signature)\n"
                        if hasattr(self.doc, 'get_sigflags'):
                            flags = self.doc.get_sigflags()
                            result += f"   - Flagi podpisu: {flags}\n"
                    except Exception as e:
                        result += f"   - Nie można odczytać szczegółów: {str(e)}\n"
                    result += "\n⚠️ Uwaga: Pełna weryfikacja podpisu kwalifikowanego\n"
                    result += "   wymaga dodatkowych bibliotek (endesive, cryptography).\n"
                else:
                    result += "❌ Brak podpisu elektronicznego w tym dokumencie.\n"
            else:
                result += "⚠️ Biblioteka PyMuPDF nie obsługuje weryfikacji podpisów.\n"
        except Exception as e:
            result += f"❌ Błąd podczas weryfikacji: {str(e)}\n"
            
        self.result_text.setText(result)
        self.title_label.setText("Wynik weryfikacji podpisu")


# ============================================================================
# OKIENKO EKSTRAKCJI OBRAZÓW
# ============================================================================
class ExtractImagesDialog(QDialog):
    def __init__(self, parent=None, doc=None):
        super().__init__(parent)
        self.setWindowTitle("Ekstrakcja obrazów z PDF")
        self.setMinimumSize(400, 300)
        self.doc = doc
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.info_label = QLabel("Wybierz folder docelowy dla obrazów:")
        self.info_label.setStyleSheet("color: #000000;")
        layout.addWidget(self.info_label)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Ścieżka do folderu...")
        self.path_edit.setStyleSheet("color: #000000; background-color: #ffffff;")
        layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Przeglądaj...")
        self.browse_btn.clicked.connect(self.browse_folder)
        layout.addWidget(self.browse_btn)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        self.extract_btn = QPushButton("Wyodrębnij obrazy")
        self.extract_btn.clicked.connect(self.extract_images)
        layout.addWidget(self.extract_btn)
        
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.setStyleSheet("background-color: #f0f0f0; QPushButton { background-color: #313244; color: #ffffff; border-radius: 5px; padding: 8px; }")
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder docelowy")
        if folder:
            self.path_edit.setText(folder)
            
    def extract_images(self):
        if not self.doc:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")
            return
            
        folder = self.path_edit.text()
        if not folder:
            show_warning(self, "Uwaga", "Wybierz folder docelowy")
            return
            
        self.extract_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        try:
            image_count = 0
            total_pages = len(self.doc)
            
            for i in range(total_pages):
                self.progress.setValue(int((i + 1) / total_pages * 100))
                QApplication.processEvents()
                
                page = self.doc[i]
                images = page.get_images()
                
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = self.doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    
                    image_path = os.path.join(folder, f"page_{i+1}_img_{img_index+1}.{ext}")
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    image_count += 1
                    
            self.progress.setVisible(False)
            show_info(self, "Sukces", f"Wyodrębniono {image_count} obrazów do folderu:\n{folder}")
            
        except Exception as e:
            show_error(self, "Błąd", str(e))
        finally:
            self.extract_btn.setEnabled(True)


# ============================================================================
# OKIENKO KOMPRESJI PDF
# ============================================================================
class CompressDialog(QDialog):
    def __init__(self, parent=None, doc=None, doc_path=None):
        super().__init__(parent)
        self.setWindowTitle("Kompresja PDF")
        self.setMinimumSize(400, 250)
        self.doc = doc
        self.doc_path = doc_path
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Poziom kompresji:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Niska (szybka)", "Średnia", "Wysoka (powolna)"])
        layout.addWidget(self.level_combo)
        
        layout.addWidget(QLabel("Usuwanie metadanych:"))
        self.remove_metadata_check = QCheckBox("Usuń metadane (autor, tytuł, daty)")
        self.remove_metadata_check.setChecked(False)
        layout.addWidget(self.remove_metadata_check)
        
        self.overwrite_check = QCheckBox("Zastąp oryginalny plik")
        self.overwrite_check.setChecked(True)
        layout.addWidget(self.overwrite_check)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        buttons = QHBoxLayout()
        self.compress_btn = QPushButton("Kompresuj")
        self.compress_btn.clicked.connect(self.compress_pdf)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.compress_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("background-color: #f0f0f0; QLabel { color: #000000; } QCheckBox { color: #000000; }")
        
    def compress_pdf(self):
        if not self.doc or not self.doc_path:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")
            return
            
        self.compress_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        try:
            self.progress.setValue(30)
            QApplication.processEvents()
            
            level = self.level_combo.currentIndex()
            garbage_level = level + 1  # 1, 2, 3
            
            output_path = self.doc_path
            if not self.overwrite_check.isChecked():
                base, ext = os.path.splitext(self.doc_path)
                output_path = f"{base}_compressed{ext}"
                
            self.doc.save(output_path, garbage=garbage_level, deflate=True, clean=True)
            
            self.progress.setValue(100)
            self.progress.setVisible(False)
            
            if self.overwrite_check.isChecked():
                show_info(self, "Sukces", "PDF został skompresowany i zapisany")
            else:
                show_info(self, "Sukces", f"PDF zapisany jako:\n{output_path}")
                
            self.accept()
            
        except Exception as e:
            show_error(self, "Błąd", str(e))
        finally:
            self.compress_btn.setEnabled(True)


# ============================================================================
# OKIENKO PORÓWNYWANIA PDF
# ============================================================================
class CompareDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Porównaj PDF")
        self.setMinimumSize(500, 250)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Pierwszy PDF:"))
        self.file1_edit = QLineEdit()
        self.file1_edit.setPlaceholderText("Ścieżka do pierwszego PDF")
        self.file1_edit.setStyleSheet("color: #000000; background-color: #ffffff;")
        layout.addWidget(self.file1_edit)
        
        btn1 = QPushButton("Przeglądaj...")
        btn1.clicked.connect(lambda: self.browse_file(self.file1_edit))
        layout.addWidget(btn1)
        
        layout.addWidget(QLabel("Drugi PDF:"))
        self.file2_edit = QLineEdit()
        self.file2_edit.setPlaceholderText("Ścieżka do drugiego PDF")
        self.file2_edit.setStyleSheet("color: #000000; background-color: #ffffff;")
        layout.addWidget(self.file2_edit)
        
        btn2 = QPushButton("Przeglądaj...")
        btn2.clicked.connect(lambda: self.browse_file(self.file2_edit))
        layout.addWidget(btn2)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Wynik porównania pojawi się tutaj...")
        self.result_text.setVisible(False)
        layout.addWidget(self.result_text)
        
        buttons = QHBoxLayout()
        self.compare_btn = QPushButton("Porównaj")
        self.compare_btn.clicked.connect(self.compare_files)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.compare_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("background-color: #f0f0f0; QLabel { color: #000000; }")
        
    def browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF", "", "*.pdf")
        if path:
            line_edit.setText(path)
            
    def compare_files(self):
        file1 = self.file1_edit.text()
        file2 = self.file2_edit.text()
        
        if not file1 or not file2:
            show_warning(self, "Uwaga", "Wybierz oba pliki PDF")
            return
            
        try:
            doc1 = fitz.open(file1)
            doc2 = fitz.open(file2)
            
            result = f"=== PORÓWNANIE PDF ===\n\n"
            result += f"Plik 1: {os.path.basename(file1)} - {len(doc1)} stron\n"
            result += f"Plik 2: {os.path.basename(file2)} - {len(doc2)} stron\n\n"
            
            if len(doc1) != len(doc2):
                result += f"⚠️ Różna liczba stron: {len(doc1)} vs {len(doc2)}\n\n"
                
            result += "Porównanie zawartości (tekst):\n"
            
            for i in range(min(len(doc1), len(doc2))):
                text1 = doc1[i].get_text().strip()
                text2 = doc2[i].get_text().strip()
                
                if text1 == text2:
                    result += f"✅ Strona {i+1}: identyczna\n"
                else:
                    result += f"⚠️ Strona {i+1}: RÓŻNA\n"
                    
            doc1.close()
            doc2.close()
            
            self.result_text.setText(result)
            self.result_text.setVisible(True)
            self.compare_btn.setVisible(False)
            
            close_btn = QPushButton("Zamknij")
            close_btn.clicked.connect(self.accept)
            self.layout().addWidget(close_btn)
            
        except Exception as e:
            show_error(self, "Błąd", str(e))


# ============================================================================
# GLOWNA ZAKLADKA PDF MASTER
# ============================================================================
class PdfMasterTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.current_doc = None
        self.current_file = None
        self.settings = QSettings("PDFRiderNex", "Settings")
        self.edit_tools = None
        self.page_tools = None
        self.security_tools = None
        self.settings_tools = None
        self.has_unsaved_changes = False
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(3)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #313244; width: 3px; }")

        col1 = self.create_left_panel()
        col2 = self.create_thumbnail_panel()
        col3 = self.create_main_panel()

        self.splitter.addWidget(col1)
        self.splitter.addWidget(col2)
        self.splitter.addWidget(col3)
        self.splitter.setSizes([180, 180, 1000])
        main_layout.addWidget(self.splitter)

    # ========================================================================
    # LEWY PANEL
    # ========================================================================
    def create_left_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(160)
        panel.setStyleSheet("background-color: #181825;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title = QLabel("📁 MENU GŁÓWNE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px; padding-bottom: 5px;")
        layout.addWidget(title)
        
        self.open_btn = self.create_side_btn("📂 Otwórz PDF")
        self.open_btn.clicked.connect(self.open_pdf)
        layout.addWidget(self.open_btn)
        
        self.open_another_btn = self.create_side_btn("📂+ Dodaj kolejny PDF")
        self.open_another_btn.clicked.connect(self.merge_pdf)
        layout.addWidget(self.open_another_btn)
        
        self.save_btn = self.create_side_btn("💾 Zapisz")
        self.save_btn.clicked.connect(self.save_pdf)
        layout.addWidget(self.save_btn)
        
        self.save_as_btn = self.create_side_btn("💾 Zapisz jako")
        self.save_as_btn.clicked.connect(self.save_pdf_as)
        layout.addWidget(self.save_as_btn)
        
        self.print_btn = self.create_side_btn("🖨️ Drukuj")
        self.print_btn.clicked.connect(self.print_pdf)
        layout.addWidget(self.print_btn)
        
        self.close_btn = self.create_side_btn("❌ Zamknij PDF")
        self.close_btn.clicked.connect(self.close_pdf)
        layout.addWidget(self.close_btn)
        
        layout.addWidget(self.create_separator())
        
        self.undo_btn = self.create_side_btn("↩️ Cofnij")
        self.undo_btn.clicked.connect(self.undo_action)
        layout.addWidget(self.undo_btn)
        
        self.redo_btn = self.create_side_btn("↪️ Ponów")
        self.redo_btn.clicked.connect(self.redo_action)
        layout.addWidget(self.redo_btn)
        
        layout.addWidget(self.create_separator())
        
        self.properties_btn = self.create_side_btn("ℹ️ Właściwości")
        self.properties_btn.clicked.connect(self.show_properties)
        layout.addWidget(self.properties_btn)
        
        self.metadata_btn = self.create_side_btn("📋 Metadane")
        self.metadata_btn.clicked.connect(self.show_metadata)
        layout.addWidget(self.metadata_btn)
        
        layout.addStretch()
        return panel

    def create_side_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(35)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding-left: 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #313244;
                color: #89b4fa;
            }
        """)
        return btn

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #313244; max-height: 1px;")
        line.setFixedHeight(1)
        return line

    # ========================================================================
    # PANEL MINIATUR
    # ========================================================================
    def create_thumbnail_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(120)
        panel.setStyleSheet("background-color: #181825;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        title = QLabel("📑 STRONY")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; color: #89b4fa; padding: 8px; background-color: #1e1e2e;")
        title.setFixedHeight(35)
        layout.addWidget(title)
        
        self.thumb = ThumbnailPanel()
        self.thumb.page_selected.connect(self.go_to_page)
        layout.addWidget(self.thumb)
        
        return panel

    # ========================================================================
    # PANEL GŁÓWNY
    # ========================================================================
    def create_main_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addSpacing(25)

        self.tools_tab = QTabWidget()
        self.tools_tab.setFixedHeight(110)
        self.tools_tab.setStyleSheet("""
            QTabWidget::pane { background-color: #1e1e2e; border: none; border-top: 1px solid #313244; }
            QTabBar::tab { background-color: #1e1e2e; color: #cdd6f4; padding: 10px 25px; margin-right: 3px; font-size: 13px; }
            QTabBar::tab:selected { background-color: #313244; color: #89b4fa; border-bottom: 2px solid #89b4fa; }
        """)
        
        self.tools_tab.addTab(self.create_page_tab(), "📄 Strona")
        self.tools_tab.addTab(self.create_edit_tab(), "✏️ Edytuj")
        self.tools_tab.addTab(self.create_security_tab(), "🛡️ Zabezpiecz")
        self.tools_tab.addTab(self.create_tools_tab(), "🔧 Narzędzia")
        self.tools_tab.addTab(self.create_settings_tab(), "⚙️ Ustawienia")
        
        layout.addWidget(self.tools_tab)

        nav_bar = QWidget()
        nav_bar.setStyleSheet("background-color: #1e1e2e; border-bottom: 1px solid #313244;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.setSpacing(8)
        
        self.prev_btn = self.create_tool_btn("◀")
        self.prev_btn.clicked.connect(self.prev_page)
        self.page_label = QLabel("Strona: 0/0")
        self.page_label.setStyleSheet("color: #cdd6f4; padding: 0 10px;")
        self.next_btn = self.create_tool_btn("▶")
        self.next_btn.clicked.connect(self.next_page)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #cdd6f4; padding: 0 10px;")
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addWidget(self.zoom_label)
        nav_layout.addStretch()
        
        layout.addWidget(nav_bar)

        self.viewer = PdfViewer()
        self.viewer.text_selected.connect(self.on_text_selected)
        layout.addWidget(self.viewer)

        return panel

    # ========================================================================
    # ZAKŁADKI NARZĘDZI
    # ========================================================================
    def create_page_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        self.add_page_btn = self.create_tool_btn("➕ Dodaj stronę")
        self.add_page_btn.clicked.connect(self.add_page)
        self.delete_page_btn = self.create_tool_btn("🗑️ Usuń stronę")
        self.delete_page_btn.clicked.connect(self.delete_current_page)
        self.duplicate_page_btn = self.create_tool_btn("📄 Duplikuj stronę")
        self.duplicate_page_btn.clicked.connect(self.duplicate_page)
        self.rotate_btn = self.create_tool_btn("🔄 Obróć")
        self.rotate_btn.clicked.connect(self.rotate_page)
        self.numbering_btn = self.create_tool_btn("🔢 Numeracja")
        self.numbering_btn.clicked.connect(self.add_numbering)
        self.split_page_btn = self.create_tool_btn("✂️ Podziel stronę")
        self.split_page_btn.clicked.connect(self.split_page)
        self.merge_pages_btn = self.create_tool_btn("🔗 Scal strony")
        self.merge_pages_btn.clicked.connect(self.merge_pages)
        self.rotate_all_btn = self.create_tool_btn("🔄 Obróć wszystkie")
        self.rotate_all_btn.clicked.connect(self.rotate_all_pages)
        self.resize_page_btn = self.create_tool_btn("📏 Zmień rozmiar")
        self.resize_page_btn.clicked.connect(self.resize_page)

        for btn in [self.add_page_btn, self.delete_page_btn, self.duplicate_page_btn, self.rotate_btn, self.numbering_btn,
                    self.split_page_btn, self.merge_pages_btn, self.rotate_all_btn, self.resize_page_btn]:
            layout.addWidget(btn)
        layout.addStretch()
        return tab

    def create_edit_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        self.add_text_btn = self.create_tool_btn("📝 Dodaj tekst")
        self.add_text_btn.clicked.connect(self.add_text)
        self.highlight_btn = self.create_tool_btn("🟡 Zaznacz")
        self.highlight_btn.clicked.connect(self.highlight_selection)
        self.comment_btn = self.create_tool_btn("💬 Komentarz")
        self.comment_btn.clicked.connect(self.add_comment)
        self.note_btn = self.create_tool_btn("📌 Notatka")
        self.note_btn.clicked.connect(self.add_note)
        self.signature_btn = self.create_tool_btn("✍️ Podpis")
        self.signature_btn.clicked.connect(self.add_signature)
        self.remove_text_btn = self.create_tool_btn("🗑️ Usuń tekst")
        self.remove_text_btn.clicked.connect(self.remove_text)
        self.add_image_btn = self.create_tool_btn("🖼️ Dodaj obraz")
        self.add_image_btn.clicked.connect(self.add_image)
        self.add_shape_btn = self.create_tool_btn("⬜ Dodaj kształt")
        self.add_shape_btn.clicked.connect(self.add_shape)
        self.change_font_btn = self.create_tool_btn("🔤 Zmień czcionkę")
        self.change_font_btn.clicked.connect(self.change_font)

        for btn in [self.add_text_btn, self.highlight_btn, self.comment_btn, self.note_btn, self.signature_btn,
                    self.remove_text_btn, self.add_image_btn, self.add_shape_btn, self.change_font_btn]:
            layout.addWidget(btn)
        layout.addStretch()
        return tab

    def create_security_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        self.password_btn = self.create_tool_btn("🔒 Dodaj hasło")
        self.password_btn.clicked.connect(self.add_password)
        self.verify_signature_btn = self.create_tool_btn("🔍 Weryfikuj podpis")
        self.verify_signature_btn.clicked.connect(self.verify_signature)
        self.remove_password_btn = self.create_tool_btn("🔓 Usuń hasło")
        self.remove_password_btn.clicked.connect(self.remove_password)
        self.change_password_btn = self.create_tool_btn("🔑 Zmień hasło")
        self.change_password_btn.clicked.connect(self.change_password)
        self.add_watermark_btn = self.create_tool_btn("💧 Dodaj watermark")
        self.add_watermark_btn.clicked.connect(self.add_watermark)
        self.check_permissions_btn = self.create_tool_btn("🔐 Sprawdź uprawnienia")
        self.check_permissions_btn.clicked.connect(self.check_permissions)

        for btn in [self.password_btn, self.verify_signature_btn, self.remove_password_btn,
                    self.change_password_btn, self.add_watermark_btn, self.check_permissions_btn]:
            layout.addWidget(btn)
        layout.addStretch()
        return tab

    def create_tools_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        
        self.ocr_btn = self.create_tool_btn("📄 OCR")
        self.ocr_btn.clicked.connect(self.open_ocr_dialog)
        self.extract_images_btn = self.create_tool_btn("🖼️ Eksportuj obrazy")
        self.extract_images_btn.clicked.connect(self.extract_images)
        self.compress_btn = self.create_tool_btn("🗜️ Kompresuj")
        self.compress_btn.clicked.connect(self.compress_pdf)
        self.compare_btn = self.create_tool_btn("🔍 Porównaj PDF")
        self.compare_btn.clicked.connect(self.compare_pdfs)
        
        for btn in [self.ocr_btn, self.extract_images_btn, self.compress_btn, self.compare_btn]:
            layout.addWidget(btn)
        layout.addStretch()
        return tab

    def create_settings_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        self.zoom_default_btn = self.create_tool_btn("🔍 Domyślny zoom")
        self.zoom_default_btn.clicked.connect(self.set_default_zoom)
        self.theme_btn = self.create_tool_btn("🎨 Motyw")
        self.theme_btn.clicked.connect(self.change_theme)
        self.language_btn = self.create_tool_btn("🌐 Język")
        self.language_btn.clicked.connect(self.set_language)
        self.save_settings_btn = self.create_tool_btn("💾 Zapisz ustawienia")
        self.save_settings_btn.clicked.connect(self.save_settings)

        for btn in [self.zoom_default_btn, self.theme_btn, self.language_btn, self.save_settings_btn]:
            layout.addWidget(btn)
        layout.addStretch()
        return tab

    def create_tool_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(38)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                color: #1a1a2e;
            }
        """)
        return btn

    # ========================================================================
    # FUNKCJE UŻYTKOWE
    # ========================================================================
    def set_status(self, text):
        if self.main_window and hasattr(self.main_window, 'status_label') and self.main_window.status_label:
            self.main_window.status_label.setText(text)

    def set_unsaved(self):
        self.has_unsaved_changes = True
        if self.main_window:
            self.main_window.setWindowTitle("PDF Rider Nex *")

    def clear_unsaved(self):
        self.has_unsaved_changes = False
        if self.main_window:
            self.main_window.setWindowTitle("PDF Rider Nex")

    def on_text_selected(self, rect, text):
        if hasattr(self.viewer, 'pending_text') and self.viewer.pending_text:
            self.viewer.add_text_at_position(self.viewer.current_page, self.viewer.pending_text, QPoint(rect.x(), rect.y()), self.viewer.pending_text_size)
            self.set_status(f"Dodano tekst")
            self.set_unsaved()
            self.viewer.pending_text = None
        elif hasattr(self.viewer, 'pending_remove') and self.viewer.pending_remove:
            if self.edit_tools and self.edit_tools.remove_text(self.viewer.current_page, rect):
                self.viewer.refresh_all_pages()
                self.set_unsaved()
            self.viewer.pending_remove = False
            self.viewer.tool_mode = "select"
        elif hasattr(self.viewer, 'pending_font_change') and self.viewer.pending_font_change:
            # Prosta zmiana czcionki na przykładową
            if self.edit_tools and self.edit_tools.change_font(self.viewer.current_page, rect):
                self.viewer.refresh_all_pages()
                self.set_unsaved()
            self.viewer.pending_font_change = False
            self.viewer.tool_mode = "select"

    # ========================================================================
    # FUNKCJE PDF
    # ========================================================================
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Otwórz PDF", "", "*.pdf")
        if path:
            try:
                self.current_doc = fitz.open(path)
                self.current_file = path
                self.viewer.load_document(self.current_doc)
                self.thumb.load_document(self.current_doc)
                self.edit_tools = PdfEditTools(self.viewer, self.current_doc, self.set_status)
                self.page_tools = PageTools(self.current_doc, self.set_status)
                self.security_tools = SecurityTools(self.current_doc, path, self.set_status)
                self.settings_tools = SettingsTools(self.main_window)
                self.update_ui()
                self.set_status(f"Otwarto: {os.path.basename(path)}")
                self.settings.setValue("last_file", path)
                self.clear_unsaved()
            except Exception as e:
                show_error(self, "Błąd", str(e))

    def merge_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz główny PDF")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF do dołączenia", "", "*.pdf")
        if path:
            try:
                new_doc = fitz.open(path)
                self.current_doc.insert_pdf(new_doc)
                new_doc.close()
                self.viewer.load_document(self.current_doc)
                self.thumb.load_document(self.current_doc)
                self.update_ui()
                self.set_status(f"Dołączono: {os.path.basename(path)}")
                self.set_unsaved()
            except Exception as e:
                show_error(self, "Błąd", str(e))

    def save_pdf(self):
        if self.current_doc and self.current_file:
            try:
                self.current_doc.save(self.current_file, garbage=4, deflate=True, clean=True)
                self.set_status(f"Zapisano: {os.path.basename(self.current_file)}")
                self.clear_unsaved()
            except Exception as e:
                show_error(self, "Błąd zapisu", str(e))

    def save_pdf_as(self):
        if self.current_doc:
            path, _ = QFileDialog.getSaveFileName(self, "Zapisz jako", "", "*.pdf")
            if path:
                try:
                    self.current_doc.save(path, garbage=4, deflate=True, clean=True)
                    self.current_file = path
                    self.set_status(f"Zapisano jako: {os.path.basename(path)}")
                    self.clear_unsaved()
                except Exception as e:
                    show_error(self, "Błąd", str(e))

    def close_pdf(self):
        if self.current_doc:
            if self.has_unsaved_changes:
                reply = show_question(self, "Zapis zmian", "Czy zapisać zmiany przed zamknięciem?")
                if reply == QMessageBox.Yes:
                    self.save_pdf()
                elif reply == QMessageBox.Cancel:
                    return
            self.current_doc.close()
            self.current_doc = None
            self.current_file = None
            self.viewer.load_document(None)
            self.thumb.load_document(None)
            self.viewer.clear()
            self.thumb.clear()
            self.update_ui()
            self.set_status("Zamknięto dokument")
            self.clear_unsaved()

    def print_pdf(self):
        self.set_status("Drukowanie - funkcja w przygotowaniu")

    def undo_action(self):
        self.set_status("Cofnij - funkcja w przygotowaniu")

    def redo_action(self):
        self.set_status("Ponów - funkcja w przygotowaniu")

    def show_properties(self):
        if self.current_doc:
            meta = self.current_doc.metadata
            text = f"Tytuł: {meta.get('title', 'brak')}\nAutor: {meta.get('author', 'brak')}\nStron: {len(self.current_doc)}\n"
            text += f"Data utworzenia: {meta.get('creationDate', 'brak')}\nFormat: PDF {self.current_doc.pdf_version}"
            show_info(self, "Właściwości", text)
        else:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")

    def show_metadata(self):
        if self.current_doc:
            meta = self.current_doc.metadata
            text = "\n".join([f"{k}: {v}" for k, v in meta.items() if v])
            show_info(self, "Metadane", text if text else "Brak metadanych")
        else:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")

    def add_page(self):
        """Dodaje stronę (pustą lub z PDF) z wyborem pozycji"""
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
            
        dialog = AddPageDialog(self, self.viewer.current_page, self.current_doc.page_count)
        if dialog.exec_():
            insert_pos = dialog.get_insert_position()
            target_page = self.viewer.current_page
            
            if insert_pos == 0:
                insert_index = self.current_doc.page_count
            elif insert_pos == 1:
                insert_index = target_page
            elif insert_pos == 2:
                insert_index = target_page + 1
            else:
                insert_index = 0
                
            if dialog.is_blank_page():
                self.current_doc.new_page(width=595, height=842, insert=insert_index)
                self.set_status("Dodano nową pustą stronę")
            else:
                pdf_path = dialog.get_pdf_path()
                page_num = dialog.get_page_number()
                
                if not pdf_path or not os.path.exists(pdf_path):
                    show_warning(self, "Uwaga", "Nie wybrano pliku PDF")
                    return
                    
                try:
                    source_doc = fitz.open(pdf_path)
                    if page_num < len(source_doc):
                        self.current_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num, start_at=insert_index)
                        self.set_status(f"Dodano stronę {page_num + 1} z pliku {os.path.basename(pdf_path)}")
                    else:
                        show_warning(self, "Uwaga", f"Plik ma tylko {len(source_doc)} stron")
                        source_doc.close()
                        return
                    source_doc.close()
                except Exception as e:
                    show_error(self, "Błąd", str(e))
                    return
                    
            self.viewer.load_document(self.current_doc)
            self.thumb.load_document(self.current_doc)
            self.update_ui()
            self.set_unsaved()

    def delete_current_page(self):
        if not self.current_doc:
            return
        if self.current_doc.page_count <= 1:
            show_warning(self, "Uwaga", "Nie można usunąć jedynej strony")
            return
        page_num = self.viewer.current_page
        self.current_doc.delete_page(page_num)
        self.viewer.load_document(self.current_doc)
        self.thumb.load_document(self.current_doc)
        self.update_ui()
        self.set_status(f"Usunięto stronę {page_num + 1}")
        self.set_unsaved()

    def duplicate_page(self):
        if not self.current_doc:
            return
        page_num = self.viewer.current_page
        try:
            temp_doc = fitz.open()
            temp_doc.insert_pdf(self.current_doc, from_page=page_num, to_page=page_num)
            self.current_doc.insert_pdf(temp_doc, start_at=page_num + 1)
            temp_doc.close()
            self.viewer.load_document(self.current_doc)
            self.thumb.load_document(self.current_doc)
            self.update_ui()
            self.set_status(f"Duplikowano stronę {page_num + 1}")
            self.set_unsaved()
        except Exception as e:
            show_error(self, "Błąd", str(e))

    def rotate_page(self):
        if not self.current_doc:
            return
        page = self.current_doc[self.viewer.current_page]
        page.set_rotation((page.get_rotation() + 90) % 360)
        self.viewer.refresh_all_pages()
        self.set_status("Strona obrócona o 90°")
        self.set_unsaved()

    def add_numbering(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = NumberingDialog(self)
        if dialog.exec_():
            start = dialog.get_start()
            positions = [(400, 30), (50, 30), (750, 30), (400, 800)]
            pos_idx = dialog.get_position()
            for i, page in enumerate(self.current_doc):
                page.insert_text(positions[pos_idx], f"{start + i}", fontsize=10)
            self.viewer.refresh_all_pages()
            self.set_status(f"Dodano numerację od {start}")
            self.set_unsaved()

    def add_text(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = TextInputDialog(self)
        if dialog.exec_():
            text = dialog.get_text()
            if text:
                self.viewer.pending_text = text
                self.viewer.pending_text_size = dialog.get_font_size()
                self.viewer.set_tool_mode("text")
                self.set_status("Kliknij na stronie, aby dodać tekst")

    def highlight_selection(self):
        if not self.current_doc:
            return
        self.viewer.set_tool_mode("select")
        self.set_status("Zaznacz obszar tekstu, który chcesz podświetlić")

    def add_comment(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        text, ok = QInputDialog.getMultiLineText(self, "Dodaj komentarz", "Treść komentarza:")
        if ok and text:
            self.viewer.pending_comment = text
            self.viewer.set_tool_mode("comment")
            self.set_status("Kliknij na stronie, aby dodać komentarz")

    def add_note(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        text, ok = QInputDialog.getMultiLineText(self, "Dodaj notatkę", "Treść notatki:")
        if ok and text:
            self.viewer.pending_note = text
            self.viewer.set_tool_mode("note")
            self.set_status("Kliknij na stronie, aby dodać notatkę")

    def add_signature(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz podpisu", "", "Obrazy (*.png *.jpg *.jpeg)")
        if path:
            self.viewer.pending_signature = path
            self.viewer.set_tool_mode("signature")
            self.set_status("Kliknij na stronie, aby dodać podpis")

    def add_password(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = PasswordDialog(self)
        if dialog.exec_():
            pwd = dialog.get_password()
            confirm = dialog.get_confirm()
            if pwd != confirm:
                show_warning(self, "Błąd", "Hasła nie są identyczne")
                return
            if pwd:
                try:
                    if dialog.overwrite_original():
                        self.current_doc.save(self.current_file, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=pwd, user_pw=pwd)
                        self.set_status("PDF zabezpieczony hasłem (zastąpiono oryginał)")
                    else:
                        path, _ = QFileDialog.getSaveFileName(self, "Zapisz zabezpieczony PDF", "", "*.pdf")
                        if path:
                            self.current_doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=pwd, user_pw=pwd)
                            self.current_file = path
                            self.set_status(f"PDF zabezpieczony hasłem i zapisany jako: {os.path.basename(path)}")
                    self.clear_unsaved()
                except Exception as e:
                    show_error(self, "Błąd", str(e))
            else:
                show_warning(self, "Błąd", "Hasło nie może być puste")

    def verify_signature(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = SignatureVerificationDialog(self, self.current_doc, self.current_file)
        dialog.exec_()

    def extract_images(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = ExtractImagesDialog(self, self.current_doc)
        dialog.exec_()

    def compress_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = CompressDialog(self, self.current_doc, self.current_file)
        if dialog.exec_():
            self.viewer.load_document(self.current_doc)
            self.thumb.load_document(self.current_doc)
            self.update_ui()
            self.clear_unsaved()

    def compare_pdfs(self):
        dialog = CompareDialog(self)
        dialog.exec_()

    def open_ocr_dialog(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = OcrDialog(self.current_doc, self)
        dialog.exec_()

    def zoom_in(self):
        self.viewer.set_zoom(self.viewer.zoom * 1.1)
        self.zoom_label.setText(f"{int(self.viewer.zoom * 100)}%")

    def zoom_out(self):
        self.viewer.set_zoom(self.viewer.zoom / 1.1)
        self.zoom_label.setText(f"{int(self.viewer.zoom * 100)}%")

    def go_to_page(self, page):
        self.viewer.go_to_page(page)
        self.update_ui()

    def prev_page(self):
        self.viewer.prev_page()
        self.update_ui()

    def next_page(self):
        """Przechodzi do następnej strony"""
        if self.current_doc and self.viewer.current_page + 1 < self.current_doc.page_count:
            self.viewer.current_page += 1
            self.viewer.ensureWidgetVisible(self.viewer.pages_labels[self.viewer.current_page])
            self.update_ui()
            self.set_status(f"Strona {self.viewer.current_page + 1} z {self.current_doc.page_count}")
        else:
            self.set_status("To jest ostatnia strona")

    def update_ui(self):
        if self.current_doc:
            self.page_label.setText(f"Strona: {self.viewer.current_page + 1}/{self.current_doc.page_count}")
            self.thumb.highlight_page(self.viewer.current_page)

    # ========================================================================
    # NOWE FUNKCJE NARZĘDZI STRONY
    # ========================================================================
    def split_page(self):
        if not self.page_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        # Proste dzielenie pionowe dla bieżącej strony
        if self.page_tools.split_page(self.viewer.current_page, "vertical"):
            self.viewer.refresh_all_pages()
            self.thumb.load_document(self.current_doc)
            self.set_unsaved()

    def merge_pages(self):
        if not self.page_tools or not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        # Scal bieżącą stronę z następną
        if self.viewer.current_page + 1 < len(self.current_doc):
            page_indices = [self.viewer.current_page, self.viewer.current_page + 1]
            if self.page_tools.merge_pages(page_indices):
                self.viewer.load_document(self.current_doc)
                self.thumb.load_document(self.current_doc)
                self.update_ui()
                self.set_unsaved()

    def rotate_all_pages(self):
        if not self.page_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        angle, ok = QInputDialog.getInt(self, "Obróć wszystkie strony", "Kąt obrotu (w stopniach):", 90, -360, 360, 90)
        if ok and self.page_tools.rotate_all_pages(angle):
            self.viewer.refresh_all_pages()
            self.set_unsaved()

    def resize_page(self):
        if not self.page_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        width, ok1 = QInputDialog.getInt(self, "Zmień rozmiar strony", "Szerokość (punkty):", 595, 100, 2000)
        if ok1:
            height, ok2 = QInputDialog.getInt(self, "Zmień rozmiar strony", "Wysokość (punkty):", 842, 100, 2000)
            if ok2 and self.page_tools.resize_page(self.viewer.current_page, width, height):
                self.viewer.refresh_all_pages()
                self.set_unsaved()

    # ========================================================================
    # NOWE FUNKCJE NARZĘDZI EDYCJI
    # ========================================================================
    def remove_text(self):
        if not self.edit_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        self.viewer.pending_remove = True
        self.viewer.set_tool_mode("remove")
        self.set_status("Zaznacz obszar tekstu do usunięcia")

    def add_image(self):
        if not self.edit_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz", "", "Obrazy (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.viewer.pending_image = path
            self.viewer.set_tool_mode("image")
            self.set_status("Kliknij na stronie, aby dodać obraz")

    def add_shape(self):
        if not self.edit_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        shape, ok = QInputDialog.getItem(self, "Dodaj kształt", "Wybierz kształt:", ["rectangle", "circle"], 0, False)
        if ok:
            self.viewer.pending_shape = shape
            self.viewer.set_tool_mode("shape")
            self.set_status(f"Kliknij na stronie, aby dodać {shape}")

    def change_font(self):
        if not self.edit_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        self.viewer.pending_font_change = True
        self.viewer.set_tool_mode("font")
        self.set_status("Zaznacz tekst do zmiany czcionki")

    # ========================================================================
    # NOWE FUNKCJE NARZĘDZI ZABEZPIECZEŃ
    # ========================================================================
    def remove_password(self):
        if not self.security_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        password, ok = QInputDialog.getText(self, "Usuń hasło", "Wprowadź hasło:", QLineEdit.Password)
        if ok and self.security_tools.remove_password(password):
            self.clear_unsaved()

    def change_password(self):
        if not self.security_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        old_pass, ok1 = QInputDialog.getText(self, "Zmień hasło", "Stare hasło:", QLineEdit.Password)
        if ok1:
            new_pass, ok2 = QInputDialog.getText(self, "Zmień hasło", "Nowe hasło:", QLineEdit.Password)
            if ok2 and self.security_tools.change_password(old_pass, new_pass):
                self.clear_unsaved()

    def add_watermark(self):
        if not self.security_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        text, ok = QInputDialog.getText(self, "Dodaj watermark", "Tekst watermark:")
        if ok and self.security_tools.add_watermark(text):
            self.viewer.refresh_all_pages()
            self.set_unsaved()

    def check_permissions(self):
        if not self.security_tools:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        perms = self.security_tools.check_permissions()
        show_info(self, "Uprawnienia", perms)

    # ========================================================================
    # NOWE FUNKCJE USTAWIEŃ
    # ========================================================================
    def set_default_zoom(self):
        if not self.settings_tools:
            return
        zoom, ok = QInputDialog.getInt(self, "Domyślny zoom", "Poziom zoomu (%):", 100, 30, 300)
        if ok:
            self.settings_tools.set_default_zoom(zoom)

    def change_theme(self):
        if not self.settings_tools:
            return
        theme, ok = QInputDialog.getItem(self, "Zmień motyw", "Wybierz motyw:", ["dark", "light"], 0, False)
        if ok:
            self.settings_tools.change_theme(theme)

    def set_language(self):
        if not self.settings_tools:
            return
        lang, ok = QInputDialog.getItem(self, "Zmień język", "Wybierz język:", ["pl", "en"], 0, False)
        if ok:
            self.settings_tools.set_language(lang)

    def save_settings(self):
        if not self.settings_tools:
            return
        self.settings_tools.save_settings()