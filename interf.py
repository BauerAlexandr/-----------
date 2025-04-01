import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QTextEdit,
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QTabWidget, QLabel,
    QPlainTextEdit,
)
from PyQt6.QtGui import (
    QAction, QIcon, QKeySequence, QPalette, 
    QColor, QDropEvent, QDragEnterEvent, QPainter,
    QActionGroup, QFont,
)
from PyQt6.QtCore import Qt, QTranslator, QRect
from ui_interf import Ui_MainWindow
from simple_text_edit import CodeEditor
from scanner import JSScanner
import re


class LineNumberTextEdit(QPlainTextEdit):
    """Текстовый редактор с нумерацией строк"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = QWidget(self)
        self.line_number_area.setMinimumWidth(30)
        self.line_number_area.installEventFilter(self)
        
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.update_line_number_area)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        self.paint_line_numbers()
    
    def eventFilter(self, obj, event):
        if obj is self.line_number_area and event.type() == event.Type.Paint:
            self.paint_line_numbers()
            return True
        return super().eventFilter(obj, event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        line_number_area_rect = QRect(cr.left(), cr.top(), 
                                     self.line_number_area_width(), cr.height())
        self.line_number_area.setGeometry(line_number_area_rect)
    
    def line_number_area_width(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits
    
    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect=None, dy=None):
        if dy:
            self.line_number_area.scroll(0, dy)
        elif rect:
            self.line_number_area.update(0, rect.y(), 
                                        self.line_number_area.width(), rect.height())
        else:
            self.line_number_area.update()
        
        if rect and rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()
    
    def paint_line_numbers(self):
        painter = QPainter(self.line_number_area)
        painter.fillRect(self.line_number_area.rect(), 
                         self.palette().color(QPalette.ColorRole.Base))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= self.line_number_area.rect().bottom():
            if block.isVisible() and bottom >= self.line_number_area.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#808080"))
                
                # Создаем прямоугольник для отрисовки текста
                rect = QRect(0, int(top), self.line_number_area.width() - 5, 
                           self.fontMetrics().height())
                painter.drawText(rect, Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка перетаскивания файлов в окно редактора"""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Обработка бросания файла в окно редактора"""
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            url = mime_data.urls()[0]
            if url.isLocalFile():
                # Получаем путь к локальному файлу
                file_path = url.toLocalFile()
                try:
                    # Попытка открыть файл
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        # Открываем файл в новой вкладке
                        self.window().open_file_from_path(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл: {str(e)}")
            event.acceptProposedAction()


class ResultTabWidget(QTabWidget):
    """Виджет вкладок для вывода результатов с разными модулями"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(False)
        self.addTab(QTextEdit(), "Консоль")
        self.addTab(QTableWidget(), "Ошибки")
        
        # Создаем вкладку с результатами анализа и таблицей токенов
        self.token_table = QTableWidget()
        self.token_table.setColumnCount(4)
        self.token_table.setHorizontalHeaderLabels(
            ["Тип", "Значение", "Строка", "Позиция"]
        )
        self.token_table.horizontalHeader().setStretchLastSection(True)
        
        token_tab = QWidget()
        layout = QVBoxLayout(token_tab)
        layout.addWidget(self.token_table)
        token_tab.setLayout(layout)
        
        self.addTab(token_tab, "Результаты анализа")
    
    def setup_error_table(self):
        """Настройка таблицы ошибок"""
        table = self.widget(1)
        if isinstance(table, QTableWidget):
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Строка", "Позиция", "Тип", "Сообщение"])
            table.horizontalHeader().setStretchLastSection(True)
            
            # Устанавливаем ширину столбцов
            table.setColumnWidth(0, 70)  # Строка
            table.setColumnWidth(1, 70)  # Позиция
            table.setColumnWidth(2, 150) # Тип
            
            # Устанавливаем выравнивание заголовков
            for i in range(table.columnCount()):
                table.horizontalHeaderItem(i).setTextAlignment(Qt.AlignmentFlag.AlignLeft)
            
            # Включаем сортировку
            table.setSortingEnabled(True)
    
    def add_error(self, line, position, error_type, message):
        """Добавление ошибки в таблицу"""
        table = self.widget(1)
        if isinstance(table, QTableWidget):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(line)))
            table.setItem(row, 1, QTableWidgetItem(str(position)))
            table.setItem(row, 2, QTableWidgetItem(error_type))
            table.setItem(row, 3, QTableWidgetItem(message))
    
    def clear_errors(self):
        """Очистка таблицы ошибок"""
        table = self.widget(1)
        if isinstance(table, QTableWidget):
            table.setRowCount(0)
    
    def add_console_message(self, message):
        """Добавление сообщения в консоль"""
        console = self.widget(0)
        if isinstance(console, QTextEdit):
            console.append(message)
    
    def clear_token_table(self):
        """Очистка таблицы токенов"""
        self.token_table.setRowCount(0)
    
    def populate_token_table(self, tokens):
        """Заполнение таблицы токенов результатами анализа"""
        # Очищаем таблицу
        self.clear_token_table()
        
        # Добавляем токены в таблицу
        for token in tokens:
            row = self.token_table.rowCount()
            self.token_table.insertRow(row)
            
            # Заполняем ячейки таблицы
            self.token_table.setItem(row, 0, QTableWidgetItem(token['type']))
            self.token_table.setItem(row, 1, QTableWidgetItem(token['value']))
            self.token_table.setItem(row, 2, QTableWidgetItem(str(token['line'])))
            self.token_table.setItem(row, 3, QTableWidgetItem(str(token['position'])))
        
        # Настраиваем ширину столбцов
        self.token_table.resizeColumnsToContents()
        
        # Переключаемся на вкладку с результатами анализа
        self.setCurrentIndex(2)
    
    # Новые методы для работы с подсветкой ошибок
    def clear_result_table(self):
        """Очистка таблицы результатов анализа"""
        self.clear_token_table()
    
    def clear_error_table(self):
        """Очистка таблицы ошибок"""
        self.clear_errors()
    
    def add_token_to_table(self, line, column, token_type, value):
        """Добавление токена в таблицу результатов"""
        row = self.token_table.rowCount()
        self.token_table.insertRow(row)
        
        # Заполняем ячейки таблицы (без Код и Диапазон)
        self.token_table.setItem(row, 0, QTableWidgetItem(token_type))
        self.token_table.setItem(row, 1, QTableWidgetItem(value))
        self.token_table.setItem(row, 2, QTableWidgetItem(str(line)))
        self.token_table.setItem(row, 3, QTableWidgetItem(str(column)))
    
    def add_error_to_table(self, line, position, value, message):
        """Добавление ошибки в таблицу ошибок"""
        self.add_error(line, position, "Ошибка", message)
    
    def switch_to_results_tab(self):
        """Переключение на вкладку с результатами анализа"""
        self.setCurrentIndex(2)
    
    def switch_to_errors_tab(self):
        """Переключение на вкладку с ошибками"""
        self.setCurrentIndex(1)


class TranslationHelper:
    """Вспомогательный класс для работы с переводами"""
    
    @staticmethod
    def load_translation(app, lang_code):
        """Загружает перевод из файла .qm"""
        # Создаем переводчик
        translator = QTranslator()
        
        # Путь к файлам переводов
        translation_file = f"translations/{lang_code}.qm"
        
        # Если перевод успешно загружен, устанавливаем его в приложение
        if translator.load(translation_file):
            app.installTranslator(translator)
            return translator
        return None
    
    @staticmethod
    def translate_ui(ui, app):
        """Переводит интерфейс после смены языка"""
        # Переводим элементы меню
        ui.retranslateUi(app)
        
    @staticmethod
    def simple_translate(text, translations_dict=None):
        """
        Простой метод перевода текста с использованием словаря переводов
        Используется как запасной вариант для пользовательских строк
        """
        if not translations_dict:
            return text
        
        return translations_dict.get(text, text)
    
    @staticmethod
    def load_translations_dict(lang_code):
        """Загружает словарь переводов из файла .ts"""
        translations_dict = {}
        try:
            # Путь к файлу перевода
            translation_file = f"translations/{lang_code}.ts"
            
            # Проверяем существование файла
            import os
            if not os.path.exists(translation_file):
                print(f"Файл перевода не найден: {translation_file}")
                return {}
            
            # Читаем файл и создаем словарь переводов
            with open(translation_file, "r", encoding="utf-8") as f:
                content = f.read()
                
                # Ищем все блоки с переводами
                import re
                pattern = r'<message>\s*<source>(.*?)</source>\s*<translation>(.*?)</translation>\s*</message>'
                matches = re.finditer(pattern, content)
                
                for match in matches:
                    source = match.group(1)
                    translation = match.group(2)
                    translations_dict[source] = translation
            
            return translations_dict
            
        except Exception as e:
            print(f"Ошибка при загрузке файла перевода: {e}")
            return {}


class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.font_size = 12
        self.min_font_size = 6
        self.max_font_size = 32
        self.current_file_paths = []
        self.unsaved_changes = []
        
        # Инициализация переводчика для интернационализации
        self.translator = QTranslator()
        self.current_language = "ru"  # По умолчанию русский
        self.translations = {}  # Словарь переводов
        
        # Замена resultArea на ResultTabWidget
        self.remove_old_result_area()
        self.result_tabs = ResultTabWidget(self.ui.splitter)
        self.result_tabs.setup_error_table()
        
        # Настройка иконок для панели инструментов
        self.setup_toolbar_icons()
        self.setup_additional_actions()
        
        self.setup_language_selector()
        self.setup_connections()
        self.setup_shortcuts()
        self.setup_text_menu()
        self.update_font_size()
        
        # Инициализация вкладок редактора
        self.ui.tabWidget.tabCloseRequested.connect(self.close_tab)
        
        # Удаляем начальную вкладку и добавляем новую с CodeEditor
        self.ui.tabWidget.clear()
        # Создаем новую вкладку с переведенным названием
        self.add_new_tab(TranslationHelper.simple_translate("New file", self.translations))
        
        # Обновление строки состояния
        self.cursor_position_label = QLabel("Строка: 1, Столбец: 1")
        self.status_message_label = QLabel("Готов")
        self.ui.statusbar.addPermanentWidget(self.cursor_position_label)
        self.ui.statusbar.addWidget(self.status_message_label, 1)
        
        # Регистрация редактора для Drag & Drop
        self.setAcceptDrops(True)
    
    def remove_old_result_area(self):
        """Удаляем старую область результатов"""
        for i in range(self.ui.splitter.count()):
            widget = self.ui.splitter.widget(i)
            if widget == self.ui.resultArea:
                widget.setParent(None)
                widget.deleteLater()
                break

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
        self.ui.action_New.triggered.connect(lambda: self.add_new_tab(TranslationHelper.simple_translate("New file", self.translations)))
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
    def add_new_tab(self, name=None, content="", file_path=None):
        """Добавляет новую вкладку с редактором"""
        # Если имя не указано, используем перевод "New file" в зависимости от текущего языка
        if name is None:
            name = TranslationHelper.simple_translate("New file", self.translations)
            
        # Создаем новый редактор кода
        new_editor = CodeEditor(self)
        
        # Настраиваем шрифт
        font = QFont("Consolas", 10)
        new_editor.setFont(font)
        
        # Устанавливаем содержимое
        new_editor.setPlainText(content)
        new_editor.document().setModified(False)  # Сбрасываем флаг изменения
        
        # Подключаем сигналы
        # Используем document().contentsChanged вместо textChanged для отслеживания изменений в тексте
        new_editor.document().contentsChanged.connect(lambda: self.update_unsaved_status(new_editor))
        new_editor.cursorPositionChanged.connect(
            lambda: self.update_cursor_position(new_editor))
        
        # Создаем layout для редактора
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(new_editor)
        
        # Создаем контейнер для редактора
        editor_container = QWidget()
        editor_container.setLayout(editor_layout)
        
        # Добавляем вкладку
        tab_index = self.ui.tabWidget.addTab(editor_container, name)
        self.ui.tabWidget.setCurrentIndex(tab_index)
        
        # Обновляем список текущих путей
        if tab_index >= len(self.current_file_paths):
            self.current_file_paths.extend([None] * (tab_index - len(self.current_file_paths) + 1))
        self.current_file_paths[tab_index] = file_path
        
        # Обновляем список флагов несохраненных изменений
        if tab_index >= len(self.unsaved_changes):
            self.unsaved_changes.extend([False] * (tab_index - len(self.unsaved_changes) + 1))
        self.unsaved_changes[tab_index] = False
        
        # Возвращаем созданный редактор
        return new_editor

    def get_current_editor(self):
        current_widget = self.ui.tabWidget.currentWidget()
        return current_widget.findChild(QPlainTextEdit) if current_widget else None

    def close_tab(self, index):
        if self.check_unsaved_changes(index):
            # Удаляем данные вкладки
            if index < len(self.current_file_paths):
                # Для списков мы устанавливаем None вместо удаления элемента
                # чтобы не смещать индексы других вкладок
                self.current_file_paths[index] = None
            if index < len(self.unsaved_changes):
                self.unsaved_changes[index] = False
            
            # Удаляем саму вкладку
            self.ui.tabWidget.removeTab(index)
            
            # Если это была последняя вкладка, создаем новую
            if self.ui.tabWidget.count() == 0:
                # Создаем новую вкладку с переведенным названием
                self.add_new_tab(TranslationHelper.simple_translate("New file", self.translations))

    def update_unsaved_status(self, editor):
        """Обновляет статус несохраненных изменений для текущей вкладки"""
        index = self.ui.tabWidget.currentIndex()
        if index < 0:
            return
            
        # Устанавливаем флаг несохраненных изменений
        self.unsaved_changes[index] = True
        
        # Обновляем заголовок вкладки, добавляя звездочку, если её еще нет
        title = self.ui.tabWidget.tabText(index)
        if not title.startswith('*'):
            self.ui.tabWidget.setTabText(index, f"*{title}")
            
        # Обновляем строку состояния
        self.status_message_label.setText("Несохраненные изменения")
        
    def reset_unsaved_status(self, editor, index):
        """Сбрасывает статус несохраненных изменений для указанной вкладки"""
        if index < 0 or index >= len(self.unsaved_changes):
            return
            
        # Сбрасываем флаг несохраненных изменений
        self.unsaved_changes[index] = False
        editor.document().setModified(False)
        
        # Обновляем заголовок вкладки, убирая звездочку
        title = self.ui.tabWidget.tabText(index)
        if title.startswith('*'):
            self.ui.tabWidget.setTabText(index, title[1:])
            
        # Обновляем строку состояния
        self.status_message_label.setText("Все изменения сохранены")

    def check_unsaved_changes(self, index):
        # Проверяем индекс в списке
        if index < len(self.unsaved_changes) and self.unsaved_changes[index]:
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
            self.open_file_from_path(file_name)

    def save_file(self):
        index = self.ui.tabWidget.currentIndex()
        # Проверяем индекс в списке
        file_path = self.current_file_paths[index] if index < len(self.current_file_paths) else None
        
        if file_path:
            with open(file_path, "w", encoding="utf-8") as file:
                editor = self.get_current_editor()
                file.write(editor.toPlainText())
                # Сбрасываем статус несохраненных изменений
                self.reset_unsaved_status(editor, index)
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
                # Устанавливаем имя файла как заголовок вкладки
                file_title = file_name.split('/')[-1].split('\\')[-1]  # Получаем имя файла из пути
                self.ui.tabWidget.setTabText(index, file_title)
                # Сбрасываем статус несохраненных изменений
                self.reset_unsaved_status(editor, index)
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
            editor = self.ui.tabWidget.widget(i).findChild(QPlainTextEdit)
            if editor:
                editor.setFont(font)
                
        # Применяем к панели результатов, если она существует
        if hasattr(self, 'result_tabs'):
            for i in range(self.result_tabs.count()):
                widget = self.result_tabs.widget(i)
                if isinstance(widget, QTextEdit):
                    widget.setFont(font)

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

    
    ### Основные команды

    - **Создать новый документ**: `Ctrl+N` или через меню "Файл" -> "Создать".
    - **Открыть файл**: `Ctrl+O` или через меню "Файл" -> "Открыть".
    - **Сохранить файл**: `Ctrl+S` или через меню "Файл" -> "Сохранить".
    - **Сохранить как**: `Ctrl+Shift+S` или через меню "Файл" -> "Сохранить как".
    - **Закрыть приложение**: `Ctrl+Q` или через меню "Файл" -> "Выход".

    ### Редактирование текста

    - **Вырезать**: `Ctrl+X` или через меню "Правка" -> "Вырезать".
    - **Копировать**: `Ctrl+C` или через меню "Правка" -> "Копировать".
    - **Вставить**: `Ctrl+V` или через меню "Правка" -> "Вставить".
    - **Отменить**: `Ctrl+Z` или через меню "Правка" -> "Отменить".
    - **Повторить**: `Ctrl+Y` или через меню "Правка" -> "Повторить".
    - **Выделить все**: `Ctrl+A` или через меню "Правка" -> "Выделить все".
    - **Удалить**: `Del` или через меню "Правка" -> "Удалить".

    ### Навигация

    - **Переход к строке**: `Ctrl+G` или через меню "Правка" -> "Перейти к строке".
    - **Переход к следующему слову**: `Ctrl+Right` или `Ctrl+Next`.
    - **Переход к предыдущему слову**: `Ctrl+Left` или `Ctrl+Previous`.

    ### Изменение размера шрифта

    - **Увеличить шрифт**: `Ctrl+Shift+` или через меню "Правка" -> "Увеличить шрифт".
    - **Уменьшить шрифт**: `Ctrl+-` или через меню "Правка" -> "Уменьшить шрифт".

    ### Другие функции

    - **Помощь**: `F1` или через меню "Справка" -> "Помощь".
    - **О программе**: `Ctrl+I` или через меню "Справка" -> "О программе".
    """)
        QMessageBox.information(self, "Справка", help_text)

    def show_about(self):
        about_text = ("""
        ## О программе

        Наша программа - это текстовый редактор со встроенным лексическим анализатором JavaScript. 
        Вот как она работает:
        1. Многодокументный интерфейс: Позволяет работать с несколькими файлами в разных вкладках.
        2. Лексический анализатор: Анализирует JavaScript-код, разбивает его на токены (лексемы) и выявляет ошибки.
        3. Подсветка ошибок: Визуально подсвечивает ошибки прямо в тексте редактора красным цветом с подчеркиванием.
        4. Отображение результатов: Результаты анализа показываются в нижней панели с вкладками "Консоль", "Ошибки" и "Результаты анализа".
        5. Многоязычный интерфейс: Поддерживает переключение между русским и английским языками.
        6. Работа с файлами: Создание, открытие, сохранение файлов с отслеживанием несохраненных изменений.
        7. Редактирование текста: Стандартные функции (копировать, вырезать, вставить, отменить) и работа с шрифтами.
        8. Программа использует PyQt6 для графического интерфейса и имеет модульную структуру, где JSScanner отвечает за анализ кода, а CodeEditor реализует редактор с подсветкой ошибок.
        """)
        QMessageBox.information(self, "О программе", about_text)

    def run_lexical_analysis(self):
        """Выполняет лексический анализ текущего открытого документа"""
        # Получаем текущий редактор
        current_editor = self.get_current_editor()
        if not current_editor:
            return

        # Очистка предыдущих результатов
        self.result_tabs.clear_result_table()
        self.result_tabs.clear_error_table()
        
        # Получаем текст для анализа
        text = current_editor.toPlainText()
        if not text:
            self.add_console_message("Нет текста для анализа")
            return
        
        # Инициализируем сканер и выполняем токенизацию
        scanner = JSScanner()
        tokens = scanner.tokenize(text)
        
        # Разделяем токены на обычные и ошибки
        valid_tokens = []
        errors = []
        
        for token in tokens:
            if token.type == "ERROR":
                # Добавляем информацию об ошибке
                error_info = {
                    'line': token.line,
                    'position': token.column,
                    'value': token.value,
                    'message': f"Недопустимый символ: {token.value}"
                }
                errors.append(error_info)
            else:
                valid_tokens.append(token)
        
        # Заполняем таблицу токенов
        if valid_tokens:
            for token in valid_tokens:
                self.result_tabs.add_token_to_table(
                    token.line, token.column, token.type, token.value
                )

        # Устанавливаем ошибки для подсветки в редакторе
        if hasattr(current_editor, "set_errors"):
            current_editor.set_errors(errors)
        
        # Добавляем информацию в консоль
        if len(errors) == 0:
            self.add_console_message("Лексический анализ завершен успешно. Ошибок не найдено.")
            # Переключаемся на вкладку с результатами
            self.result_tabs.switch_to_results_tab()
        else:
            error_message = f"Лексический анализ завершен с ошибками. Найдено ошибок: {len(errors)}"
            self.add_console_message(error_message)
            
            # Добавляем ошибки в таблицу ошибок
            for error in errors:
                self.result_tabs.add_error_to_table(
                    error['line'], error['position'], error['value'], error['message']
                )
            
            # Переключаемся на вкладку с ошибками
            self.result_tabs.switch_to_errors_tab()
        
        # Примеры найденных лексем
        if valid_tokens:
            self.add_console_message(f"Найдено {len(valid_tokens)} лексем")
            self.add_console_message("Примеры найденных лексем:")
            for i, token in enumerate(valid_tokens[:5]):  # Показываем первые 5 токенов
                self.add_console_message(f"{token.type}: {token.value}")
            if len(valid_tokens) > 5:
                self.add_console_message("...")
        
        return valid_tokens, errors

    def setup_additional_actions(self):
        """Настройка дополнительных действий, например для запуска анализатора"""
        # Кнопка для запуска лексического анализатора
        analyze_button = QAction("Анализ", self)
        analyze_button.setToolTip("Запустить лексический анализатор")
        analyze_button.setIcon(QIcon(self.get_icon_path("play--v1.png")))
        analyze_button.triggered.connect(self.run_lexical_analysis)
        
        # Добавляем кнопку на панель инструментов
        self.ui.toolBar.addSeparator()
        self.ui.toolBar.addAction(analyze_button)
    
    def setup_toolbar_icons(self):
        """Настройка иконок для панели инструментов"""
        # Очищаем панель инструментов
        self.ui.toolBar.clear()
        
        # Словарь соответствия действий и их иконок
        action_icons = {
            self.ui.action_New: "add-file.png",
            self.ui.action_Open: "open-document.png",
            self.ui.action_Save: "save--v1.png",
            self.ui.action_Undo: "undo.png",
            self.ui.action_Redo: "redo.png",
            self.ui.action_Cut: "cut.png",
            self.ui.action_Copy: "copy.png",
            self.ui.action_Paste: "paste.png",
            self.ui.action_Help: "help.png",
            self.ui.action_About: "info--v1.png",
            self.ui.action_ZoomIn: "increase-font.png",
            self.ui.action_ZoomOut: "decrease-font.png",
        }
        
        # Устанавливаем иконки и добавляем действия в панель инструментов
        for action, icon_name in action_icons.items():
            action.setIcon(QIcon(self.get_icon_path(icon_name)))
        
        # Добавляем группы кнопок с разделителями
        # Группа файловых операций
        file_actions = [self.ui.action_New, self.ui.action_Open, self.ui.action_Save]
        for action in file_actions:
            self.ui.toolBar.addAction(action)
        
        self.ui.toolBar.addSeparator()
        
        # Группа операций редактирования
        edit_actions = [self.ui.action_Undo, self.ui.action_Redo, 
                        self.ui.action_Cut, self.ui.action_Copy, self.ui.action_Paste]
        for action in edit_actions:
            self.ui.toolBar.addAction(action)
        
        self.ui.toolBar.addSeparator()
        
        # Группа масштабирования
        zoom_actions = [self.ui.action_ZoomIn, self.ui.action_ZoomOut]
        for action in zoom_actions:
            self.ui.toolBar.addAction(action)
        
        self.ui.toolBar.addSeparator()
        
        # Группа справки
        help_actions = [self.ui.action_Help, self.ui.action_About]
        for action in help_actions:
            self.ui.toolBar.addAction(action)
    
    def setup_language_selector(self):
        """Настройка выбора языка"""
        # Создаем меню для выбора языка
        self.lang_menu = self.ui.menubar.addMenu("Язык")
        
        # Создаем группу действий, чтобы только одно могло быть выбрано
        self.lang_action_group = QActionGroup(self)
        self.lang_action_group.setExclusive(True)
        
        # Создаем действия для каждого языка
        self.ru_action = QAction("Русский", self)
        self.ru_action.setCheckable(True)
        self.ru_action.setData("ru")
        
        self.en_action = QAction("English", self)
        self.en_action.setCheckable(True)
        self.en_action.setData("en")
        
        # Добавляем действия в группу
        self.lang_action_group.addAction(self.ru_action)
        self.lang_action_group.addAction(self.en_action)
        
        # Подключаем обработчики
        self.ru_action.triggered.connect(lambda: self.change_language("ru"))
        self.en_action.triggered.connect(lambda: self.change_language("en"))
        
        # Добавляем действия в меню
        self.lang_menu.addAction(self.ru_action)
        self.lang_menu.addAction(self.en_action)
        
        # Устанавливаем текущий язык и отмечаем соответствующее действие
        self.ru_action.setChecked(True)
        self.change_language("ru")
    
    def change_language(self, lang_code):
        """Изменение языка интерфейса"""
        # Загружаем словарь переводов
        loaded_translations = TranslationHelper.load_translations_dict(lang_code)
        
        # Создаем базовые переводы в зависимости от языка
        base_translations = {
            "New file": "Новый файл",  # Английский -> Русский
            "Новый файл": "New file"   # Русский -> Английский
        }
        
        # Объединяем базовые переводы с загруженными
        self.translations = {**base_translations, **loaded_translations}
        self.current_language = lang_code
        
        # Обновляем галочку выбора языка в меню
        if hasattr(self, 'ru_action') and hasattr(self, 'en_action'):
            self.ru_action.setChecked(lang_code == "ru")
            self.en_action.setChecked(lang_code == "en")
        
        # Обновляем все текстовые элементы интерфейса
        self.update_ui_texts()
        
        # Обновляем статус
        self.ui.statusbar.showMessage(f"Язык интерфейса изменен на {lang_code}")
    
    def update_ui_texts(self):
        """Обновляет все текстовые элементы интерфейса в соответствии с текущим языком"""
        # Обновляем заголовок окна
        self.setWindowTitle(TranslationHelper.simple_translate("Text Editor", self.translations))
        
        # Обновляем меню языка
        self.lang_menu.setTitle(TranslationHelper.simple_translate("Language", self.translations))
        
        # Обновляем меню Файл
        self.ui.menuFile.setTitle(TranslationHelper.simple_translate("File", self.translations))
        self.ui.action_New.setText(TranslationHelper.simple_translate("New", self.translations))
        self.ui.action_Open.setText(TranslationHelper.simple_translate("Open", self.translations))
        self.ui.action_Save.setText(TranslationHelper.simple_translate("Save", self.translations))
        self.ui.action_SaveAs.setText(TranslationHelper.simple_translate("Save As", self.translations))
        self.ui.action_Exit.setText(TranslationHelper.simple_translate("Exit", self.translations))
        
        # Обновляем меню Правка
        self.ui.menuEdit.setTitle(TranslationHelper.simple_translate("Edit", self.translations))
        self.ui.action_Undo.setText(TranslationHelper.simple_translate("Undo", self.translations))
        self.ui.action_Redo.setText(TranslationHelper.simple_translate("Redo", self.translations))
        self.ui.action_Cut.setText(TranslationHelper.simple_translate("Cut", self.translations))
        self.ui.action_Copy.setText(TranslationHelper.simple_translate("Copy", self.translations))
        self.ui.action_Paste.setText(TranslationHelper.simple_translate("Paste", self.translations))
        self.ui.action_Delete.setText(TranslationHelper.simple_translate("Delete", self.translations))
        self.ui.action_SelectAll.setText(TranslationHelper.simple_translate("Select All", self.translations))
        self.ui.action_ZoomIn.setText(TranslationHelper.simple_translate("Zoom In", self.translations))
        self.ui.action_ZoomOut.setText(TranslationHelper.simple_translate("Zoom Out", self.translations))
        
        # Обновляем меню Текст
        self.ui.menuText.setTitle(TranslationHelper.simple_translate("Text", self.translations))
        self.ui.action_Task.setText(TranslationHelper.simple_translate("Task Description", self.translations))
        self.ui.action_Grammar.setText(TranslationHelper.simple_translate("Grammar", self.translations))
        self.ui.action_Classification.setText(TranslationHelper.simple_translate("Grammar Classification", self.translations))
        self.ui.action_Method.setText(TranslationHelper.simple_translate("Analysis Method", self.translations))
        self.ui.action_Errors.setText(TranslationHelper.simple_translate("Error Diagnostics", self.translations))
        self.ui.action_Test.setText(TranslationHelper.simple_translate("Test Example", self.translations))
        self.ui.action_References.setText(TranslationHelper.simple_translate("References", self.translations))
        self.ui.action_SourceCode.setText(TranslationHelper.simple_translate("Source Code", self.translations))
        
        # Обновляем меню Пуск
        self.ui.menuRun.setTitle(TranslationHelper.simple_translate("Run", self.translations))
        
        # Обновляем меню Справка
        self.ui.menuHelp.setTitle(TranslationHelper.simple_translate("Help", self.translations))
        self.ui.action_Help.setText(TranslationHelper.simple_translate("Help", self.translations))
        self.ui.action_About.setText(TranslationHelper.simple_translate("About", self.translations))
        
        # Обновляем заголовки вкладок
        for i in range(self.ui.tabWidget.count()):
            title = self.ui.tabWidget.tabText(i)
            if title == "Новый файл" or title == "New file" or "*" in title:
                clean_title = title.replace("*", "").strip()
                if clean_title == "Новый файл" or clean_title == "New file":
                    new_title = TranslationHelper.simple_translate("New file", self.translations)
                    if "*" in title:
                        new_title = "* " + new_title
                    self.ui.tabWidget.setTabText(i, new_title)
        
        # Обновляем заголовки вкладок результатов
        self.result_tabs.setTabText(0, TranslationHelper.simple_translate("Console", self.translations))
        self.result_tabs.setTabText(1, TranslationHelper.simple_translate("Errors", self.translations))
        self.result_tabs.setTabText(2, TranslationHelper.simple_translate("Analysis Results", self.translations))
        
        # Обновляем заголовки столбцов в таблице токенов
        self.result_tabs.token_table.setHorizontalHeaderLabels([
            TranslationHelper.simple_translate("Type", self.translations),
            TranslationHelper.simple_translate("Value", self.translations),
            TranslationHelper.simple_translate("Line", self.translations),
            TranslationHelper.simple_translate("Position", self.translations)
        ])
        
        # Обновляем заголовки столбцов в таблице ошибок
        error_table = self.result_tabs.widget(1)
        if isinstance(error_table, QTableWidget):
            error_table.setHorizontalHeaderLabels([
                TranslationHelper.simple_translate("Line", self.translations),
                TranslationHelper.simple_translate("Position", self.translations),
                TranslationHelper.simple_translate("Type", self.translations),
                TranslationHelper.simple_translate("Message", self.translations)
            ])

    def open_file_from_path(self, file_path):
        """Открывает файл из указанного пути"""
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Определяем заголовок вкладки из имени файла
                title = file_path.split('/')[-1]
                if '\\' in title:  # для Windows путей
                    title = title.split('\\')[-1]
                
                # Создаем новую вкладку с содержимым файла
                new_editor = self.add_new_tab(title, content, file_path)
                
                # Устанавливаем статус документа как "несохраненный = false"
                index = self.ui.tabWidget.currentIndex()
                self.unsaved_changes[index] = False
                new_editor.document().setModified(False)
            
            # Обновляем строку состояния
            self.ui.statusbar.showMessage(f"Файл открыт: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка открытия файла", 
                                f"Не удалось открыть файл:\n{str(e)}")

    def add_console_message(self, message):
        """Выводит сообщение в консоль результатов"""
        self.result_tabs.add_console_message(message)

    def update_cursor_position(self, editor):
        """Обновляет информацию о позиции курсора в строке состояния"""
        cursor = editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.cursor_position_label.setText(f"Строка: {line}, Столбец: {column}")

    def closeEvent(self, event):
        """Обработка события закрытия приложения"""
        # Проверяем все вкладки на наличие несохраненных изменений
        for i in range(len(self.unsaved_changes)):
            if i < self.ui.tabWidget.count() and self.unsaved_changes[i]:
                # Делаем эту вкладку активной
                self.ui.tabWidget.setCurrentIndex(i)
                
                # Спрашиваем пользователя, хочет ли он сохранить изменения
                reply = QMessageBox.question(
                    self, 'Сохранение изменений',
                    f'В файле {self.ui.tabWidget.tabText(i).replace("*", "")} есть несохраненные изменения. Сохранить?',
                    QMessageBox.StandardButton.Save | 
                    QMessageBox.StandardButton.Discard | 
                    QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Save:
                    # Если пользователь хочет сохранить и сохранение не удалось, отменяем закрытие
                    if not self.save_file():
                        event.ignore()
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    # Если пользователь отменил, отменяем закрытие
                    event.ignore()
                    return
        
        # Если все изменения были сохранены или отклонены, принимаем закрытие
        event.accept()


# Запуск приложения при прямом выполнении модуля
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextEditor()
    window.show()
    sys.exit(app.exec())