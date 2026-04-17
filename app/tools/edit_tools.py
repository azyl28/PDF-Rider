"""
Narzędzia do edycji zawartości PDF
"""

import fitz
from PyQt5.QtWidgets import QMessageBox, QColorDialog
from PyQt5.QtGui import QPixmap


class PdfEditTools:
    def __init__(self, viewer, doc, status_callback=None):
        self.viewer = viewer
        self.doc = doc
        self.status_callback = status_callback or (lambda x: None)

    def remove_text(self, page_index, rect):
        """Usuń tekst z obszaru"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            # Dodaj biały prostokąt nad tekstem
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            self.status_callback(f"Usunięto tekst ze strony {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd usuwania tekstu: {str(e)}")
            return False

    def add_image(self, page_index, image_path, pos):
        """Dodaj obraz na stronie"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            rect = fitz.Rect(x, y, x + 200, y + 150)  # Domyślny rozmiar
            page.insert_image(rect, filename=image_path)
            self.status_callback(f"Dodano obraz na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania obrazu: {str(e)}")
            return False

    def add_shape(self, page_index, shape_type, pos, size=(100, 100)):
        """Dodaj kształt (prostokąt lub okrąg)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            rect = fitz.Rect(x, y, x + size[0], y + size[1])

            if shape_type == "rectangle":
                page.draw_rect(rect, color=(0, 0, 0), width=2)
            elif shape_type == "circle":
                center = (x + size[0]/2, y + size[1]/2)
                page.draw_circle(center, size[0]/2, color=(0, 0, 0), width=2)

            self.status_callback(f"Dodano kształt na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania kształtu: {str(e)}")
            return False

    def change_font(self, page_index, rect, new_font="helv", new_size=12):
        """Zmień czcionkę tekstu w obszarze (uproszczona implementacja)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            # To jest uproszczona wersja - w rzeczywistości wymagałoby ekstrakcji i ponownego wstawienia tekstu
            # Tutaj tylko przykładowa implementacja
            text = page.get_textbox(rect)
            if text:
                # Usuń stary tekst i dodaj nowy
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                page.insert_text((rect.x0, rect.y0), text, fontsize=new_size, fontname=new_font)
                self.status_callback(f"Zmieniono czcionkę na stronie {page_index + 1}")
                return True
        except Exception as e:
            self.status_callback(f"Błąd zmiany czcionki: {str(e)}")
            return False

    def highlight_text(self, page_index, rect, color=(1, 1, 0)):
        """Podświetl tekst"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            page.add_highlight_annot(rect)
            self.status_callback(f"Podświetlono tekst na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd podświetlania: {str(e)}")
            return False