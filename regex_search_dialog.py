from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from regex_search import RegexSearcher, SearchResult

class RegexSearchDialog(QDialog):
    """Диалоговое окно для поиска по регулярным выражениям"""
    
    # Сигнал для выделения найденного текста
    highlight_match = pyqtSignal(int, int)  # start, end
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Поиск по регулярным выражениям")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        # Создаем основной layout
        layout = QVBoxLayout(self)
        
        # Создаем элементы управления
        controls_layout = QHBoxLayout()
        
        # Выпадающий список с типами шаблонов
        self.pattern_combo = QComboBox()
        for pattern_type in RegexSearcher.PATTERNS.keys():
            self.pattern_combo.addItem(
                RegexSearcher.get_pattern_description(pattern_type),
                pattern_type
            )
        controls_layout.addWidget(QLabel("Шаблон:"))
        controls_layout.addWidget(self.pattern_combo)
        
        # Кнопка поиска
        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.search)
        controls_layout.addWidget(self.search_button)
        
        # Кнопка очистки
        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.clear_results)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
        
        # Таблица результатов
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Найденное значение", "Строка", "Позиция", "Тип"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.cellDoubleClicked.connect(self.on_result_selected)
        layout.addWidget(self.results_table)
        
        # Статусная строка
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        self.current_text = ""
        self.current_results = []
    
    def set_text(self, text: str):
        """Устанавливает текст для поиска"""
        self.current_text = text
    
    def search(self):
        """Выполняет поиск по выбранному шаблону"""
        if not self.current_text:
            QMessageBox.warning(self, "Предупреждение", "Нет текста для поиска")
            return
        
        pattern_type = self.pattern_combo.currentData()
        try:
            self.current_results = RegexSearcher.find_all_matches(
                self.current_text, pattern_type
            )
            self.update_results_table()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
    
    def update_results_table(self):
        """Обновляет таблицу результатов"""
        self.results_table.setRowCount(0)
        
        for result in self.current_results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # Добавляем данные в таблицу
            self.results_table.setItem(row, 0, QTableWidgetItem(result.match))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(result.line)))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(result.column)))
            self.results_table.setItem(row, 3, QTableWidgetItem(
                RegexSearcher.get_pattern_description(result.pattern)
            ))
        
        # Обновляем статус
        self.status_label.setText(
            f"Найдено совпадений: {len(self.current_results)}"
        )
    
    def clear_results(self):
        """Очищает результаты поиска"""
        self.results_table.setRowCount(0)
        self.current_results = []
        self.status_label.setText("")
    
    def on_result_selected(self, row: int, column: int):
        """Обработчик двойного клика по результату"""
        if 0 <= row < len(self.current_results):
            result = self.current_results[row]
            self.highlight_match.emit(result.start, result.end)
            self.accept()  # Закрываем диалог после выбора 