import os
import subprocess
from PyQt6.QtCore import QTranslator

def compile_translations():
    """Компилирует файлы переводов из .ts в .qm"""
    translations_dir = "translations"
    
    # Создаем директорию, если она не существует
    if not os.path.exists(translations_dir):
        os.makedirs(translations_dir)
    
    # Компилируем каждый файл перевода
    for ts_file in os.listdir(translations_dir):
        if ts_file.endswith('.ts'):
            qm_file = os.path.join(translations_dir, ts_file.replace('.ts', '.qm'))
            
            # Создаем переводчик
            translator = QTranslator()
            
            # Загружаем файл .ts
            if translator.load(ts_file, translations_dir):
                # Сохраняем как .qm
                translator.save(qm_file)
                print(f"Скомпилирован файл: {qm_file}")
            else:
                print(f"Ошибка при компиляции: {ts_file}")

if __name__ == "__main__":
    compile_translations() 