"""
Narzędzia do zarządzania stronami PDF
"""

import fitz
from PyQt5.QtWidgets import QMessageBox


class PageTools:
    def __init__(self, doc, status_callback=None):
        self.doc = doc
        self.status_callback = status_callback or (lambda x: None)

    def split_page(self, page_index, split_type="vertical"):
        """Podziel stronę na dwie części"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            rect = page.rect
            mid = rect.width / 2 if split_type == "vertical" else rect.height / 2

            # Utwórz nową stronę
            new_page = self.doc.new_page(width=rect.width, height=rect.height, insert=page_index + 1)

            if split_type == "vertical":
                # Lewa część na oryginalnej stronie
                page.set_cropbox(fitz.Rect(0, 0, mid, rect.height))
                # Prawa część na nowej stronie
                new_page.set_cropbox(fitz.Rect(mid, 0, rect.width, rect.height))
            else:
                # Górna część na oryginalnej stronie
                page.set_cropbox(fitz.Rect(0, 0, rect.width, mid))
                # Dolna część na nowej stronie
                new_page.set_cropbox(fitz.Rect(0, mid, rect.width, rect.height))

            self.status_callback(f"Podzielono stronę {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dzielenia strony: {str(e)}")
            return False

    def merge_pages(self, page_indices):
        """Scal wybrane strony w jedną"""
        if not self.doc or len(page_indices) < 2:
            return False

        try:
            # Sortuj indeksy
            page_indices.sort(reverse=True)

            # Pobierz pierwszą stronę jako bazową
            base_page = self.doc[page_indices[-1]]
            base_rect = base_page.rect

            # Dodaj zawartość pozostałych stron
            for idx in page_indices[:-1]:
                if idx < len(self.doc):
                    page = self.doc[idx]
                    # Tutaj prosta implementacja - kopiuj zawartość
                    # W rzeczywistości może wymagać bardziej złożonej logiki
                    base_page.show_pdf_page(base_rect, self.doc, idx)
                    self.doc.delete_page(idx)

            self.status_callback(f"Scalono {len(page_indices)} stron")
            return True
        except Exception as e:
            self.status_callback(f"Błąd scalania stron: {str(e)}")
            return False

    def rotate_all_pages(self, angle):
        """Obróć wszystkie strony o podany kąt"""
        if not self.doc:
            return False

        try:
            for page in self.doc:
                current_rotation = page.get_rotation()
                page.set_rotation((current_rotation + angle) % 360)

            self.status_callback(f"Obrocono wszystkie strony o {angle}°")
            return True
        except Exception as e:
            self.status_callback(f"Błąd obracania stron: {str(e)}")
            return False

    def resize_page(self, page_index, new_width, new_height):
        """Zmień rozmiar strony"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            page.set_cropbox(fitz.Rect(0, 0, new_width, new_height))
            self.status_callback(f"Zmieniono rozmiar strony {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd zmiany rozmiaru: {str(e)}")
            return False

    def reorder_pages(self, new_order):
        """Zmień kolejność stron"""
        if not self.doc or len(new_order) != len(self.doc):
            return False

        try:
            # Utwórz nowy dokument z stronami w nowej kolejności
            new_doc = fitz.open()
            for idx in new_order:
                if 0 <= idx < len(self.doc):
                    new_doc.insert_pdf(self.doc, from_page=idx, to_page=idx)

            # Zamień dokument
            self.doc.delete_pages()  # Usuń wszystkie strony
            self.doc.insert_pdf(new_doc)  # Dodaj nowe strony
            new_doc.close()

            self.status_callback("Zmieniono kolejność stron")
            return True
        except Exception as e:
            self.status_callback(f"Błąd zmiany kolejności: {str(e)}")
            return False