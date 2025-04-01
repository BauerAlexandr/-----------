from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtCore import QRect, Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QTextFormat, QTextCharFormat, QSyntaxHighlighter, QFont

class ErrorHighlighter(QSyntaxHighlighter):
    """Подсветка ошибок в коде"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Создаем форматы для разных типов текста
        self.formats = {
            'keyword': self.create_format("#569CD6"),  # синий
            'string': self.create_format("#CE9178"),   # коричневый
            'comment': self.create_format("#6A9955"),  # зеленый
            'function': self.create_format("#DCDCAA"), # желтый
            'number': self.create_format("#B5CEA8"),   # светло-зеленый
            'operator': self.create_format("#D4D4D4"), # серый
            'error': self.create_format("#FF0000", underline=True, weight=QFont.Weight.Bold)  # красный с подчеркиванием
        }
        
        # Список правил подсветки в формате (регулярное выражение, формат)
        self.highlighting_rules = []
        
        # Добавление базовых правил для JavaScript
        self.keywords = ["var", "let", "const", "function", "if", "else", "for", "while", 
                          "in", "return", "true", "false", "null", "undefined", "this"]
        
        # Добавление правил подсветки
        # Правило для ключевых слов
        import re
        keyword_format = self.formats['keyword']
        self.highlighting_rules.append((r'\b(?:' + '|'.join(self.keywords) + r')\b', keyword_format))
        
        # Правило для функций
        function_format = self.formats['function']
        self.highlighting_rules.append((r'\b[A-Za-z0-9_]+(?=\()', function_format))
        
        # Правило для строк в одинарных кавычках
        string_format = self.formats['string']
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))
        
        # Правило для строк в двойных кавычках
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        
        # Правило для однострочных комментариев
        self.highlighting_rules.append((r'//[^\n]*', self.formats['comment']))
        
        # Набор ошибок для подсветки
        self.errors = []
    
    def create_format(self, color, underline=False, weight=None):
        """Создает формат текста с указанным цветом и стилем"""
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if underline:
            text_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        if weight:
            text_format.setFontWeight(weight)
        return text_format
    
    def set_errors(self, errors):
        """Устанавливает список ошибок для подсветки"""
        self.errors = errors
        self.rehighlight()  # Перезапускаем подсветку для всего документа
    
    def highlightBlock(self, text):
        """Метод вызывается для подсветки каждого блока текста"""
        import re
        
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)
        
        # Подсветка ошибок
        for error in self.errors:
            # Проверяем, относится ли ошибка к текущему блоку
            if error['line'] == self.currentBlock().blockNumber() + 1:
                pos = error['position'] - 1  # Позиция в строке (с 0)
                if pos >= 0 and pos < len(text):
                    # Подсвечиваем символ ошибки
                    self.setFormat(pos, 1, self.formats['error'])


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.lineNumberArea = LineNumberArea(self)
        
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        
        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()
        
        # Добавляем подсветку синтаксиса и ошибок
        self.highlighter = ErrorHighlighter(self.document())
    
    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value //= 10
            digits += 1
        
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    
    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))
    
    def highlightCurrentLine(self):
        extraSelections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            lineColor = QColor(173, 216, 230, 100)  # Светло-голубой с альфа-каналом 100
            
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        
        self.setExtraSelections(extraSelections)
    
    def set_errors(self, errors):
        """Устанавливает список ошибок для подсветки"""
        if hasattr(self, 'highlighter'):
            self.highlighter.set_errors(errors)
    
    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), self.palette().color(self.backgroundRole()))
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#808080"))
                painter.drawText(0, int(top), self.lineNumberArea.width(), self.fontMetrics().height(),
                                Qt.AlignmentFlag.AlignRight, number)
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1 