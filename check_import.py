import sys
print("Проверка импортов:")

try:
    print("Импортирую PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
    print("OK")
except Exception as e:
    print(f"Ошибка: {e}")

try:
    print("Импортирую PyQt6.QtGui")
    from PyQt6.QtGui import QAction, QIcon, QPalette
    print("OK")
except Exception as e:
    print(f"Ошибка: {e}")

try:
    print("Импортирую QActionGroup")
    from PyQt6.QtGui import QActionGroup
    print("OK")
except Exception as e:
    print(f"Ошибка: {e}")

try:
    print("Импортирую QPainter, QRect")
    from PyQt6.QtGui import QPainter, QRect
    print("OK")
except Exception as e:
    print(f"Ошибка: {e}")

try:
    print("Импортирую PyQt6.QtCore")
    from PyQt6.QtCore import Qt, QTranslator
    print("OK")
except Exception as e:
    print(f"Ошибка: {e}")

print("Проверка завершена") 