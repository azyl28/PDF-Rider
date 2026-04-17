"""
Narzędzia do ustawień aplikacji
"""

from PyQt5.QtWidgets import QColorDialog, QFontDialog, QMessageBox
from PyQt5.QtCore import QSettings


class SettingsTools:
    def __init__(self, main_window=None):
        self.main_window = main_window
        self.settings = QSettings("PDFRiderNex", "Settings")

    def set_default_zoom(self, zoom_level):
        """Ustaw domyślny poziom zoomu"""
        self.settings.setValue("default_zoom", zoom_level)
        self.status_callback(f"Domyślny zoom ustawiony na {zoom_level}%")

    def change_theme(self, theme_name):
        """Zmień motyw aplikacji"""
        # To wymagałoby implementacji motywów w aplikacji
        self.settings.setValue("theme", theme_name)
        self.status_callback(f"Motyw zmieniony na: {theme_name}")

    def set_language(self, language_code):
        """Zmień język aplikacji"""
        self.settings.setValue("language", language_code)
        self.status_callback(f"Język zmieniony na: {language_code}")

    def save_settings(self):
        """Zapisz ustawienia"""
        self.settings.sync()
        self.status_callback("Ustawienia zapisane")

    def load_settings(self):
        """Załaduj ustawienia"""
        return {
            "default_zoom": self.settings.value("default_zoom", 100),
            "theme": self.settings.value("theme", "dark"),
            "language": self.settings.value("language", "pl"),
            "last_file": self.settings.value("last_file", ""),
        }

    def reset_settings(self):
        """Resetuj ustawienia do domyślnych"""
        self.settings.clear()
        self.status_callback("Ustawienia zresetowane do domyślnych")

    def status_callback(self, message):
        """Wywołaj callback statusu"""
        if self.main_window and hasattr(self.main_window, 'status_label'):
            self.main_window.status_label.setText(message)