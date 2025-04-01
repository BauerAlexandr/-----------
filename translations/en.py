"""
Script for creating English translation
"""

# Basic translation dictionary
translations = {
    "СуперПуперМегаУльтраПриложение": "SuperDuperMegaUltraApplication",
    "Файл": "File",
    "Правка": "Edit",
    "Текст": "Text",
    "Пуск": "Run",
    "Справка": "Help",
    "Язык": "Language",
    "Создать": "New",
    "Сохранить как": "Save As",
    "Открыть": "Open",
    "Сохранить": "Save",
    "Выход": "Exit",
    "Удалить": "Delete",
    "Выделить все": "Select All",
    "Отменить": "Undo",
    "Повторить": "Redo",
    "Вырезать": "Cut",
    "Копировать": "Copy",
    "Вставить": "Paste",
    "Вызов справки": "Help Contents",
    "О программе": "About",
    "Постановка задачи": "Task Statement",
    "Грамматика": "Grammar",
    "Классификация грамматики": "Grammar Classification",
    "Метод анализа": "Analysis Method",
    "Диагностика и нейтрализация ошибок": "Error Diagnostics",
    "Тестовый пример": "Test Example",
    "Список литературы": "References",
    "Исходный код программы": "Program Source Code",
    "Увеличить шрифт": "Increase Font Size",
    "Уменьшить шрифт": "Decrease Font Size",
    "Новый документ": "New Document",
    "Строка: ": "Line: ",
    "Столбец: ": "Column: ",
    "Готов": "Ready",
    "Сохранение": "Save",
    "Документ имеет несохраненные изменения. Сохранить?": 
        "Document has unsaved changes. Save?",
    "Ошибка": "Error",
    "Не удалось открыть файл:": "Failed to open file:",
    "Язык интерфейса изменен на": "Interface language changed to",
    "Размер шрифта:": "Font size:",
    "Раздел:": "Section:",
    "Функционал в разработке": "Functionality in development",
    "Текстовый редактор v2.0": "Text Editor v2.0",
    "Русский": "Russian",
    "English": "English",
    "Консоль": "Console",
    "Ошибки": "Errors",
    "Результаты анализа": "Analysis Results",
    "Строка": "Line",
    "Позиция": "Position",
    "Тип": "Type",
    "Сообщение": "Message",
    "Файл {} открыт": "File {} opened",
    "Панель инструментов": "Toolbar",
    "Не удалось изменить язык:": "Failed to change language:",
}

# Function for generating the translation file
def generate_qm_file(output_file):
    """
    Generates a .qm file with translations in a simple text format
    """
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# English translation\n")
            for source, translation in translations.items():
                f.write(f"{source}={translation}\n")
        
        print(f"Translation successfully saved to file: {output_file}")
        
    except Exception as e:
        print(f"Error creating translation file: {e}")

if __name__ == "__main__":
    generate_qm_file("en.qm") 