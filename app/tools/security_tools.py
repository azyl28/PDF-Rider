"""
Narzędzia do zabezpieczania PDF
"""

import fitz
import os


class SecurityTools:
    def __init__(self, doc, doc_path, status_callback=None):
        self.doc = doc
        self.doc_path = doc_path
        self.status_callback = status_callback or (lambda x: None)

    def remove_password(self, password):
        """Usuń hasło z PDF"""
        if not self.doc:
            return False

        try:
            if self.doc.is_encrypted:
                self.doc.authenticate(password)
                # Zapisz bez hasła
                temp_path = self.doc_path + ".temp"
                self.doc.save(temp_path, encryption=fitz.PDF_ENCRYPT_NONE)
                os.replace(temp_path, self.doc_path)
                self.status_callback("Hasło zostało usunięte")
                return True
            else:
                self.status_callback("Dokument nie jest zabezpieczony hasłem")
                return False
        except Exception as e:
            self.status_callback(f"Błąd usuwania hasła: {str(e)}")
            return False

    def change_password(self, old_password, new_password):
        """Zmień hasło PDF"""
        if not self.doc:
            return False

        try:
            if self.doc.is_encrypted:
                if not self.doc.authenticate(old_password):
                    self.status_callback("Nieprawidłowe stare hasło")
                    return False

            self.doc.save(self.doc_path, encryption=fitz.PDF_ENCRYPT_AES_256,
                         owner_pw=new_password, user_pw=new_password)
            self.status_callback("Hasło zostało zmienione")
            return True
        except Exception as e:
            self.status_callback(f"Błąd zmiany hasła: {str(e)}")
            return False

    def add_watermark(self, text, opacity=0.3, font_size=50):
        """Dodaj znak wodny do wszystkich stron"""
        if not self.doc:
            return False

        try:
            for page in self.doc:
                rect = page.rect
                center = (rect.width / 2, rect.height / 2)

                # Obróć tekst dla znaku wodnego
                page.insert_text(center, text, fontsize=font_size, color=(0, 0, 0),
                               rotate=45, opacity=opacity)

            self.status_callback(f"Dodano znak wodny: {text}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania znaku wodnego: {str(e)}")
            return False

    def add_image_watermark(self, image_path, opacity=0.3):
        """Dodaj obraz jako znak wodny"""
        if not self.doc:
            return False

        try:
            for page in self.doc:
                rect = page.rect
                center = (rect.width / 2, rect.height / 2)
                size = 200
                watermark_rect = fitz.Rect(center[0] - size/2, center[1] - size/2,
                                         center[0] + size/2, center[1] + size/2)

                page.insert_image(watermark_rect, filename=image_path, opacity=opacity)

            self.status_callback("Dodano obraz jako znak wodny")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania znaku wodnego: {str(e)}")
            return False

    def check_permissions(self):
        """Sprawdź uprawnienia dokumentu"""
        if not self.doc:
            return "Brak otwartego dokumentu"

        try:
            perms = self.doc.permissions
            result = "Uprawnienia dokumentu:\n"
            result += f"Drukowanie: {'Tak' if perms & fitz.PDF_PERM_PRINT else 'Nie'}\n"
            result += f"Kopiowanie: {'Tak' if perms & fitz.PDF_PERM_COPY else 'Nie'}\n"
            result += f"Modyfikacja: {'Tak' if perms & fitz.PDF_PERM_MODIFY else 'Nie'}\n"
            result += f"Adnotacje: {'Tak' if perms & fitz.PDF_PERM_ANNOTATE else 'Nie'}\n"
            return result
        except Exception as e:
            return f"Błąd sprawdzania uprawnień: {str(e)}"