import re

class Token:
    """Класс, представляющий токен (лексему)"""
    
    def __init__(self, type, value, line, column, code=None):
        self.type = type
        self.value = value
        self.line = line
        self.column = column
        self.code = code

class JSScanner:
    """Лексический анализатор для языка JavaScript с фокусом на ассоциативные массивы"""
    
    # Диаграмма состояний сканера (ASCII-арт)
    STATE_DIAGRAM = """
    Диаграмма состояний лексического анализатора для JavaScript:
    
     ┌─────────┐                    
     │  START  │                    
     └────┬────┘                    
          ▼                        
     ┌────┴────┐  letter   ┌─────────────┐
     │   INIT  ├─────────►│ IDENTIFIER  │
     └───┬┬────┘          └─────────────┘
         ││
         ││ digit    ┌─────────┐
         │└─────────►│ NUMBER  │
         │           └─────────┘
         │
         │ "        ┌─────────┐
         ├─────────►│ STRING  │
         │          └─────────┘
         │
         │ {        ┌─────────┐
         ├─────────►│ L_BRACE │
         │          └─────────┘
         │
         │ }        ┌─────────┐
         ├─────────►│ R_BRACE │
         │          └─────────┘
         │
         │ :        ┌─────────┐
         ├─────────►│ COLON   │
         │          └─────────┘
         │
         │ ,        ┌─────────┐
         ├─────────►│ COMMA   │
         │          └─────────┘
         │
         │ ;        ┌─────────┐
         ├─────────►│ SEMICOL │
         │          └─────────┘
         │
         │ =        ┌─────────┐
         └─────────►│ ASSIGN  │
                    └─────────┘
    """
    
    # Типы лексем и их коды
    TOKEN_TYPES = {
        "KEYWORD": 1,        # Ключевое слово (let, var, const)
        "IDENTIFIER": 2,     # Идентификатор
        "NUMBER": 3,         # Число
        "STRING": 4,         # Строка
        "OPERATOR": 5,       # Оператор (+, -, *, /)
        "LBRACE": 6,         # Открывающая фигурная скобка {
        "RBRACE": 7,         # Закрывающая фигурная скобка }
        "ASSIGNMENT": 8,     # Оператор присваивания (=)
        "WHITESPACE": 9,     # Пробельные символы
        "COLON": 10,         # Двоеточие (:)
        "COMMA": 11,         # Запятая (,)
        "SEMICOLON": 12,     # Точка с запятой (;)
        "ERROR": 13          # Ошибка - недопустимый символ
    }
    
    # Ключевые слова JavaScript
    KEYWORDS = ["let", "var", "const"]
    
    def __init__(self):
        # Регулярные выражения для распознавания лексем
        self.token_specs = [
            ('KEYWORD', r'\b(?:let|var|const)\b'),
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('NUMBER', r'\d+(\.\d*)?'),
            ('STRING', r'"[^"\\]*(\\.[^"\\]*)*"'),
            ('OPERATOR', r'[\+\-\*/]'),
            ('ASSIGNMENT', r'='),
            ('LBRACE', r'\{'),
            ('RBRACE', r'\}'),
            ('COLON', r':'),
            ('COMMA', r','),
            ('SEMICOLON', r';'),
            ('WHITESPACE', r'\s+'),
            ('ERROR', r'.')  # Любой другой символ считается ошибкой
        ]
        
        # Компилируем регулярные выражения для более быстрого поиска
        self.token_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.token_specs)
        self.regex = re.compile(self.token_regex)
    
    def tokenize(self, text):
        """Разбивает текст на лексемы"""
        tokens = []
        line = 1
        line_start = 0
        absolute_position = 1  # Абсолютная позиция в тексте (начиная с 1)
        
        # Перебираем все совпадения с регулярными выражениями
        for match in self.regex.finditer(text):
            # Группа, которая соответствует лексеме
            token_type = match.lastgroup
            token_value = match.group()
            start_pos = match.start()
            end_pos = match.end()
            
            # Вычисляем позицию в строке
            col = start_pos - line_start + 1
            
            # Проверяем на переносы строк в пробельных символах
            if token_type == 'WHITESPACE':
                newlines = token_value.count('\n')
                if newlines > 0:
                    line += newlines
                    line_start = start_pos + token_value.rindex('\n') + 1
                continue  # Пропускаем пробельные символы
            
            # Получаем код и описание лексемы
            token_code = self._get_token_code(token_type, token_value)
            token_description = self._get_token_description(token_type, token_value)
            
            # Создаем объект Token
            token = Token(
                type=token_description,
                value=token_value,
                line=line,
                column=col,
                code=token_code
            )
            
            tokens.append(token)
        
        return tokens
    
    def _get_token_code(self, token_type, token_value):
        """Возвращает код лексемы для вывода"""
        if token_type == 'KEYWORD':
            return 1  # Ключевое слово
        elif token_type == 'IDENTIFIER':
            return 2  # Идентификатор
        elif token_type == 'NUMBER':
            return 3  # Число
        elif token_type == 'STRING':
            return 4  # Строка
        elif token_type == 'OPERATOR':
            return 5  # Оператор
        elif token_type == 'LBRACE':
            return 6  # Открывающая фигурная скобка
        elif token_type == 'RBRACE':
            return 7  # Закрывающая фигурная скобка
        elif token_type == 'ASSIGNMENT':
            return 8  # Оператор присваивания
        elif token_type == 'COLON':
            return 9  # Двоеточие
        elif token_type == 'COMMA':
            return 10  # Запятая
        elif token_type == 'SEMICOLON':
            return 11  # Точка с запятой
        else:
            return 12  # Ошибка - недопустимый символ
    
    def _get_token_description(self, token_type, token_value):
        """Возвращает описание лексемы для вывода"""
        if token_type == 'KEYWORD':
            return "ключевое слово"
        elif token_type == 'IDENTIFIER':
            return "идентификатор"
        elif token_type == 'NUMBER':
            return "число"
        elif token_type == 'STRING':
            return "строка"
        elif token_type == 'OPERATOR':
            return "оператор"
        elif token_type == 'LBRACE':
            return "открывающая фигурная скобка"
        elif token_type == 'RBRACE':
            return "закрывающая фигурная скобка"
        elif token_type == 'ASSIGNMENT':
            return "оператор присваивания"
        elif token_type == 'COLON':
            return "двоеточие"
        elif token_type == 'COMMA':
            return "запятая"
        elif token_type == 'SEMICOLON':
            return "точка с запятой"
        elif token_type == 'ERROR':
            return "ERROR"  # Важно: возвращаем константу ERROR для проверки в коде
        else:
            return "недопустимый символ" 