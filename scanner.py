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
        "ERROR": 13,         # Ошибка - недопустимый символ
        "LPAREN": 14,        # Открывающая (
        "RPAREN": 15,        # Закрывающая )
    }
    
    # Ключевые слова JavaScript
    KEYWORDS = ["let", "var", "const", "function", "return", "true", "false", "null", "undefined"]
    
    def __init__(self):
        # Регулярные выражения для распознавания лексем
        self.token_specs = [
            ('KEYWORD', r'\b(?:' + '|'.join(self.KEYWORDS) + r')\b'),
            ('STRING', r'"[^"\n]*"|\'[^\'\n]*\''),  # Строки без экранированных кавычек
            ('INVALID_STRING_DOUBLE', r'"[^"\n]*\n|"[^"]*$'),  # Незакрытые двойные кавычки
            ('INVALID_STRING_SINGLE', r'\'[^\'\n]*\n|\'[^\']*$'),  # Незакрытые одинарные кавычки
            ('NUMBER', r'\d+(\.\d*)?'),
            ('INVALID_IDENTIFIER', r'\d+[a-zA-Z_][a-zA-Z0-9_]*'),  # Идентификатор, начинающийся с цифры
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('OPERATOR', r'[\+\-\*/]'),
            ('INVALID_OPERATOR', r'\+\+\d'),  # Неправильное использование ++
            ('ASSIGNMENT', r'='),
            ('LBRACE', r'\{'),
            ('RBRACE', r'\}'),
            ('LPAREN', r'\('),  # Открывающая круглая скобка
            ('RPAREN', r'\)'),  # Закрывающая круглая скобка
            ('LBRACKET', r'\['),  # Открывающая квадратная скобка
            ('RBRACKET', r'\]'),  # Закрывающая квадратная скобка
            ('COLON', r':'),
            ('COMMA', r','),
            ('SEMICOLON', r';'),
            ('WHITESPACE', r'\s+'),
            ('ERROR', r'[^\s\w\{\}\[\]\(\)\"\'=\+\-\*/,:;]'),  # Недопустимые символы
        ]
        
        # Компилируем регулярные выражения для более быстрого поиска
        self.token_regex = '|'.join('(?P<%s>%s)' % pair for pair in self.token_specs)
        self.regex = re.compile(self.token_regex)
        
        # Для проверки баланса скобок
        self.brackets = []
    
    def tokenize(self, text):
        """Разбивает текст на лексемы"""
        tokens = []
        line = 1
        line_start = 0
        
        # Для хранения информации о скобках (тип, позиция, строка)
        opening_brackets = []
        
        # Перебираем все совпадения с регулярными выражениями
        for match in self.regex.finditer(text):
            # Группа, которая соответствует лексеме
            token_type = match.lastgroup
            token_value = match.group()
            start_pos = match.start()
            
            # Вычисляем позицию в строке
            col = start_pos - line_start + 1
            
            # Проверяем на переносы строк в пробельных символах
            if token_type == 'WHITESPACE':
                newlines = token_value.count('\n')
                if newlines > 0:
                    line += newlines
                    line_start = start_pos + token_value.rindex('\n') + 1
                continue  # Пропускаем пробельные символы
            
            # Отслеживаем открывающие и закрывающие скобки
            if token_type in ['LBRACE', 'LPAREN', 'LBRACKET']:
                opening_brackets.append((token_type, col, line))
            elif token_type in ['RBRACE', 'RPAREN', 'RBRACKET']:
                if opening_brackets:
                    # Проверяем соответствие типов скобок
                    opening_type, _, _ = opening_brackets.pop()
                    expected_closing = {
                        'LBRACE': 'RBRACE',
                        'LPAREN': 'RPAREN',
                        'LBRACKET': 'RBRACKET'
                    }.get(opening_type)
                    
                    if expected_closing != token_type:
                        # Неправильная закрывающая скобка
                        token = Token(
                            type="ERROR",
                            value=token_value,
                            line=line,
                            column=col,
                            code=self.TOKEN_TYPES['ERROR']
                        )
                        tokens.append(token)
                        continue
            
            # Обработка ошибок
            if token_type == 'INVALID_STRING_DOUBLE':
                token_type = 'ERROR'
                error_message = "Незакрытая двойная кавычка"
                token = Token(
                    type=token_type,
                    value=token_value,
                    line=line,
                    column=col,
                    code=self.TOKEN_TYPES['ERROR']
                )
            elif token_type == 'INVALID_STRING_SINGLE':
                token_type = 'ERROR'
                error_message = "Незакрытая одинарная кавычка"
                token = Token(
                    type=token_type,
                    value=token_value,
                    line=line,
                    column=col,
                    code=self.TOKEN_TYPES['ERROR']
                )
            elif token_type in ['INVALID_IDENTIFIER', 'INVALID_OPERATOR', 'ERROR']:
                token_type = 'ERROR'
                error_message = self._get_error_message(token_type, token_value)
                token = Token(
                    type=token_type,
                    value=token_value,
                    line=line,
                    column=col,
                    code=self.TOKEN_TYPES['ERROR']
                )
            else:
                # Создаем объект Token для правильных лексем
                token = Token(
                    type=self._get_token_description(token_type, token_value),
                    value=token_value,
                    line=line,
                    column=col,
                    code=self._get_token_code(token_type, token_value)
                )
            
            tokens.append(token)
            
            # Обновляем номер строки для многострочных токенов
            newlines = token_value.count('\n')
            if newlines > 0:
                line += newlines
                line_start = start_pos + token_value.rindex('\n') + 1
        
        # После обработки всех токенов проверяем, остались ли открытые скобки
        for bracket_type, pos, line_num in opening_brackets:
            bracket_char = {
                'LBRACE': '{',
                'LPAREN': '(',
                'LBRACKET': '['
            }.get(bracket_type)
            
            # Создаем токен ошибки для каждой незакрытой скобки
            token = Token(
                type="ERROR",
                value=bracket_char,
                line=line_num,
                column=pos,
                code=self.TOKEN_TYPES['ERROR']
            )
            tokens.append(token)
        
        return tokens
    
    def _get_error_message(self, token_type, token_value):
        """Возвращает сообщение об ошибке в зависимости от типа ошибки"""
        if token_type == 'INVALID_STRING_DOUBLE':
            return "Незакрытая двойная кавычка"
        elif token_type == 'INVALID_STRING_SINGLE':
            return "Незакрытая одинарная кавычка"
        elif token_type == 'INVALID_IDENTIFIER':
            return "Идентификатор не может начинаться с цифры"
        elif token_type == 'INVALID_OPERATOR':
            return "Неправильное использование оператора"
        else:
            return f"Недопустимый символ: {token_value}"
    
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
        elif token_type == 'LPAREN':
            return 14
        elif token_type == 'RPAREN':
            return 15
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
        elif token_type == 'LPAREN':
            return "открывающая круглая скобка"
        elif token_type == 'RPAREN':
            return "закрывающая круглая скобка"

        else:
            return "недопустимый символ" 