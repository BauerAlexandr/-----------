import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox, 
                            QToolBar, QTextEdit, QWidget, QVBoxLayout)
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPalette
from PyQt6.QtCore import Qt
from ui_interf import Ui_MainWindow

class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.font_size = 12
        self.min_font_size = 6
        self.max_font_size = 32
        self.current_file_paths = {}
        self.unsaved_changes = {}
        
        self.setup_connections()
        self.setup_toolbar()
        self.setup_shortcuts()
        self.setup_text_menu()
        self.update_font_size()
        
        # Инициализация вкладок
        self.ui.tabWidget.tabCloseRequested.connect(self.close_tab)

    def is_dark_theme(self):
        # Проверяем, является ли системная тема темной
        bg_color = self.palette().color(QPalette.ColorRole.Window)
        return bg_color.lightness() < 128

    def get_icon_path(self, base_name):
        # Выбираем папку с иконками в зависимости от темы
        theme_folder = "light_icons" if self.is_dark_theme() else "dark_icons"
        return f"{theme_folder}/{base_name}"

    def setup_connections(self):
        # Меню Файл
        self.ui.action_New.triggered.connect(lambda: self.add_new_tab())
        self.ui.action_Open.triggered.connect(self.open_file)
        self.ui.action_Save.triggered.connect(self.save_file)
        self.ui.action_SaveAs.triggered.connect(self.save_as)
        self.ui.action_Exit.triggered.connect(self.close)
        
        # Меню Правка
        self.ui.action_Undo.triggered.connect(self.undo)
        self.ui.action_Redo.triggered.connect(self.redo)
        self.ui.action_Cut.triggered.connect(self.cut)
        self.ui.action_Copy.triggered.connect(self.copy)
        self.ui.action_Paste.triggered.connect(self.paste)
        self.ui.action_Delete.triggered.connect(self.delete_text)
        self.ui.action_SelectAll.triggered.connect(self.select_all)
        self.ui.action_ZoomIn.triggered.connect(self.increase_font_size)
        self.ui.action_ZoomOut.triggered.connect(self.decrease_font_size)
        
        # Меню Справка
        self.ui.action_Help.triggered.connect(self.show_help)
        self.ui.action_About.triggered.connect(self.show_about)

    def setup_toolbar(self):
        toolbar = QToolBar("Панель инструментов")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        actions = [
            ("Создать", "add-file.png", lambda: self.add_new_tab()),
            ("Открыть", "open-document.png", self.open_file),
            ("Сохранить", "save--v1.png", self.save_file),
            ("Отмена", "undo.png", self.undo),
            ("Повтор", "redo.png", self.redo),
            ("Вырезать", "cut.png", self.cut),
            ("Копировать", "copy.png", self.copy),
            ("Вставить", "paste.png", self.paste),
            ("Запуск анализатора", "play--v1.png", lambda: None),
            ("Справка", "help.png", self.show_help),
            ("О программе", "info--v1.png", self.show_about),
            ("Увеличить шрифт", "increase-font.png", self.increase_font_size),
            ("Уменьшить шрифт", "decrease-font.png", self.decrease_font_size),
        ]

        for text, icon_file, handler in actions:
            icon_path = self.get_icon_path(icon_file)
            action = QAction(QIcon(icon_path), text, self)
            action.triggered.connect(handler)
            toolbar.addAction(action)

    def setup_shortcuts(self):
        shortcuts = {
            'action_New': QKeySequence.StandardKey.New,
            'action_Open': QKeySequence.StandardKey.Open,
            'action_Save': QKeySequence.StandardKey.Save,
            'action_SaveAs': QKeySequence.StandardKey.SaveAs,
            'action_Exit': QKeySequence("Ctrl+Q"),
            'action_Undo': QKeySequence.StandardKey.Undo,
            'action_Redo': QKeySequence.StandardKey.Redo,
            'action_Cut': QKeySequence.StandardKey.Cut,
            'action_Copy': QKeySequence.StandardKey.Copy,
            'action_Paste': QKeySequence.StandardKey.Paste,
            'action_SelectAll': QKeySequence.StandardKey.SelectAll,
            'action_Delete': QKeySequence("Del"),
            'action_ZoomIn': QKeySequence.StandardKey.ZoomIn,
            'action_ZoomOut': QKeySequence.StandardKey.ZoomOut,
             # Горячие клавиши для меню "Справка"
            'action_Help':QKeySequence.StandardKey.HelpContents,  # F1
            'action_About':QKeySequence("Ctrl+I"),              # Ctrl+I
        }
        
        for action_name, shortcut in shortcuts.items():
            action = getattr(self.ui, action_name)
            action.setShortcut(shortcut)

    # Методы работы с вкладками
    def add_new_tab(self, title="Новый документ", content="", file_path=None):
        new_editor = QTextEdit()
        new_editor.setFontPointSize(self.font_size)
        new_editor.setText(content)
        new_editor.document().contentsChanged.connect(self.update_unsaved_status)
        
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(new_editor)
        container.setLayout(layout)
        
        index = self.ui.tabWidget.addTab(container, title)
        self.ui.tabWidget.setCurrentIndex(index)
        self.current_file_paths[index] = file_path
        self.unsaved_changes[index] = False
        return new_editor

    def get_current_editor(self):
        current_widget = self.ui.tabWidget.currentWidget()
        return current_widget.findChild(QTextEdit) if current_widget else None

    def close_tab(self, index):
        if self.check_unsaved_changes(index):
            # Удаляем данные вкладки
            if index in self.current_file_paths:
                del self.current_file_paths[index]
            if index in self.unsaved_changes:
                del self.unsaved_changes[index]
            
            # Удаляем саму вкладку
            self.ui.tabWidget.removeTab(index)
            
            # Если это была последняя вкладка, создаем новую
            if self.ui.tabWidget.count() == 0:
                self.add_new_tab("Новый документ")

    def update_unsaved_status(self):
        index = self.ui.tabWidget.currentIndex()
        editor = self.get_current_editor()
        if editor:
            self.unsaved_changes[index] = editor.document().isModified()
            title = self.ui.tabWidget.tabText(index).replace('*', '')
            if self.unsaved_changes[index]:
                self.ui.tabWidget.setTabText(index, f"*{title}")
            else:
                self.ui.tabWidget.setTabText(index, title)

    def check_unsaved_changes(self, index):
        if self.unsaved_changes.get(index, False):
            reply = QMessageBox.question(
                self, 'Сохранение',
                'Документ имеет несохраненные изменения. Сохранить?',
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                return self.save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
        return True

    # Методы редактирования текста
    def undo(self):
        editor = self.get_current_editor()
        if editor: editor.undo()

    def redo(self):
        editor = self.get_current_editor()
        if editor: editor.redo()

    def cut(self):
        editor = self.get_current_editor()
        if editor: editor.cut()

    def copy(self):
        editor = self.get_current_editor()
        if editor: editor.copy()

    def paste(self):
        editor = self.get_current_editor()
        if editor: editor.paste()

    def delete_text(self):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.removeSelectedText()

    def select_all(self):
        editor = self.get_current_editor()
        if editor: editor.selectAll()

    # Методы работы с файлами
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if file_name:
            with open(file_name, "r", encoding="utf-8") as file:
                content = file.read()
                editor = self.add_new_tab(file_name.split('/')[-1], content, file_name)
                editor.document().setModified(False)
                self.update_unsaved_status()

    def save_file(self):
        index = self.ui.tabWidget.currentIndex()
        file_path = self.current_file_paths.get(index)
        
        if file_path:
            with open(file_path, "w", encoding="utf-8") as file:
                editor = self.get_current_editor()
                file.write(editor.toPlainText())
                editor.document().setModified(False)
                self.unsaved_changes[index] = False
                self.update_unsaved_status()
            return True
        else:
            return self.save_as()

    def save_as(self):
        index = self.ui.tabWidget.currentIndex()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if file_name:
            with open(file_name, "w", encoding="utf-8") as file:
                editor = self.get_current_editor()
                file.write(editor.toPlainText())
                self.current_file_paths[index] = file_name
                self.ui.tabWidget.setTabText(index, file_name.split('/')[-1])
                editor.document().setModified(False)
                self.unsaved_changes[index] = False
                self.update_unsaved_status()
            return True
        return False

    # Методы работы со шрифтом
    def increase_font_size(self):
        if self.font_size < self.max_font_size:
            self.font_size += 1
            self.update_font_size()

    def decrease_font_size(self):
        if self.font_size > self.min_font_size:
            self.font_size -= 1
            self.update_font_size()

    def update_font_size(self):
        font = self.ui.textEdit.font()
        font.setPointSize(self.font_size)
        self.ui.statusbar.showMessage(f"Размер шрифта: {self.font_size} pt")
        
        # Применяем к обоим текстовым полям
        for i in range(self.ui.tabWidget.count()):
            editor = self.ui.tabWidget.widget(i).findChild(QTextEdit)
            if editor:
                editor.setFont(font)
                
        self.ui.resultArea.setFont(font)
        

    # Методы меню Текст
    def setup_text_menu(self):
        text_actions = {
            "action_Task": "Постановка задачи",
            "action_Grammar": "Грамматика",
            "action_Classification": "Классификация грамматики",
            "action_Method": "Метод анализа",
            "action_Errors": "Диагностика ошибок",
            "action_Test": "Тестовый пример",
            "action_References": "Список литературы",
            "action_SourceCode": "Исходный код",
        }
        for action_name, title in text_actions.items():
            action = getattr(self.ui, action_name)
            action.triggered.connect(lambda _, t=title: self.show_text_info(t))

    def show_text_info(self, title):
        QMessageBox.information(self, title, f"Раздел: {title}\n(Функционал в разработке)")

    # Методы справки
    def show_help(self):
        help_text = ("""
         ## Основные функции

    - **Многодокументный интерфейс**: Работа с несколькими вкладками одновременно.
    - **Нумерация строк**: Отображение номеров строк в области редактирования.
    - **Изменение размера шрифта**: Увеличение и уменьшение размера шрифта с помощью горячих клавиш или кнопок.
    - **Редактирование текста**: Поддержка стандартных операций (вырезать, копировать, вставить, отменить, повторить).
    - **Сохранение и открытие файлов**: Работа с текстовыми файлами (`.txt`).
    - **Проверка несохраненных изменений**: Предупреждение о несохраненных изменениях при закрытии вкладки или приложения.
    - **Горячие клавиши**: Удобные сочетания клавиш для быстрого доступа к функциям.

    ## Использование

    ### Основные команды

    - **Создать новый документ**: `Ctrl+N` или через меню "Файл" -> "Создать".
    - **Открыть файл**: `Ctrl+O` или через меню "Файл" -> "Открыть".
    - **Сохранить файл**: `Ctrl+S` или через меню "Файл" -> "Сохранить".
    - **Сохранить как**: `Ctrl+Shift+S` или через меню "Файл" -> "Сохранить как".
    - **Закрыть вкладку**: Нажмите на кнопку закрытия вкладки или используйте контекстное меню.
    - **Увеличить шрифт**: `Ctrl++` или через кнопку на панели инструментов.
    - **Уменьшить шрифт**: `Ctrl+-` или через кнопку на панели инструментов.
    - **Нумерация строк**: Включена по умолчанию в области редактирования.
    """)
        QMessageBox.information(self, "Справка", help_text)

    def show_about(self):
        QMessageBox.about(self, "О программе", "Текстовый редактор v2.0\n(c) 2023")

    def closeEvent(self, event):
        for i in range(self.ui.tabWidget.count()):
            if not self.check_unsaved_changes(i):
                event.ignore()
                return
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = TextEditor()
    editor.show()
    sys.exit(app.exec())