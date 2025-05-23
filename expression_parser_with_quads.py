from scanner import JSScanner, Token

class Quad:
    def __init__(self, op, arg1, arg2, result):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def __repr__(self):
        return f"({self.op}, {self.arg1}, {self.arg2}, {self.result})"

class ExpressionParser:
    # Определим допустимые операторы и символы для арифметических выражений
    VALID_OPERATORS = ['+', '-', '*', '/']
    
    def __init__(self):
        self.scanner = JSScanner()
        self.tokens = []
        self.current = 0
        self.temp_counter = 1
        self.quads = []
        self.errors = []

    def parse(self, text):
        # Получаем все токены из сканера
        all_tokens = list(self.scanner.tokenize(text))
        
        # Добавляем отладочный вывод токенов
        print("=== Отладка токенов ===")
        for i, token in enumerate(all_tokens):
            print(f"{i}: Тип={token.type}, Значение='{token.value}', Строка={token.line}, Позиция={token.column}")
        print("======================")
        
        # Проверяем наличие чисел во входной строке - они не поддерживаются в этой грамматике
        has_numbers = False
        for token in all_tokens:
            if token.type == "NUMBER":
                has_numbers = True
                self.errors.append(f"Ошибка в строке {token.line}, позиция {token.column}: Числовые литералы '{token.value}' не поддерживаются в данной грамматике")
        
        # Если найдены числа, сразу возвращаем ошибку
        if has_numbers:
            return [], self.errors
        
        # Фильтруем пробельные символы и валидируем токены
        self.tokens = []
        for token in all_tokens:
            if token.type == "WHITESPACE":
                continue
                
            # Проверка на ошибки и недопустимые символы
            if token.type == "ERROR":
                self.errors.append(f"Ошибка в строке {token.line}, позиция {token.column}: Недопустимый символ '{token.value}'")
                continue
                
            # Проверка на допустимые операторы
            if token.type == "OPERATOR" and token.value not in self.VALID_OPERATORS:
                self.errors.append(f"Ошибка в строке {token.line}, позиция {token.column}: Недопустимый оператор '{token.value}'")
                continue
                
            # Проверка на однобуквенные идентификаторы
            if token.type == "IDENTIFIER" and len(token.value) > 1:
                # Для нашей грамматики разрешены только однобуквенные идентификаторы
                self.errors.append(f"Ошибка в строке {token.line}, позиция {token.column}: Идентификатор '{token.value}' должен быть однобуквенным")
                continue
                
            # Проверка на числовые токены, которые не разрешены в этой грамматике
            if token.type == "NUMBER":
                self.errors.append(f"Ошибка в строке {token.line}, позиция {token.column}: Числовые литералы '{token.value}' не поддерживаются в данной грамматике")
                continue
                
            # Приведем типы токенов к нужным для нашего парсера
            if token.type == "OPERATOR":
                token.type = "оператор"
            elif token.type == "IDENTIFIER":
                token.type = "идентификатор"
                
            self.tokens.append(token)
            
        # Добавляем отладочный вывод обработанных токенов
        print("=== Обработанные токены ===")
        for i, token in enumerate(self.tokens):
            print(f"{i}: Тип={token.type}, Значение='{token.value}'")
        print("=== Ошибки ===")
        for error in self.errors:
            print(error)
        print("========================")
        
        # Если есть ошибки, сразу возвращаем их
        if self.errors:
            return [], self.errors
            
        self.current = 0
        self.temp_counter = 1
        self.quads = []

        try:
            result = self.E()
            
            # Проверяем, что все токены были обработаны
            if not self.is_at_end():
                token = self.peek()
                self.error(f"Неожиданный символ '{token.value}' в конце выражения")
                
            return self.quads, self.errors
        except Exception as e:
            self.errors.append(str(e))
            return [], self.errors

    def E(self):
        t1 = self.T()
        return self.A(t1)

    def A(self, inh):
        if self.match("оператор", "+"):
            t2 = self.T()
            temp = self.new_temp()
            self.emit("+", inh, t2, temp)
            return self.A(temp)
        elif self.match("оператор", "-"):
            t2 = self.T()
            temp = self.new_temp()
            self.emit("-", inh, t2, temp)
            return self.A(temp)
        return inh

    def T(self):
        t1 = self.O()
        return self.B(t1)

    def B(self, inh):
        if self.match("оператор", "*"):
            t2 = self.O()
            temp = self.new_temp()
            self.emit("*", inh, t2, temp)
            return self.B(temp)
        elif self.match("оператор", "/"):
            t2 = self.O()
            temp = self.new_temp()
            self.emit("/", inh, t2, temp)
            return self.B(temp)
        return inh

    def O(self):
        if self.match("оператор", "-"):
            t = self.O()
            temp = self.new_temp()
            self.emit("uminus", t, "_", temp)
            return temp
        elif self.match("идентификатор"):
            return self.previous().value
        elif self.match("LPAREN"):
            temp = self.E()
            if not self.match("RPAREN"):
                self.error("Ожидалась закрывающая скобка ')'")
            return temp
        else:
            self.error("Ожидался идентификатор, унарный минус или скобка")

    def match(self, token_type, value=None):
        if self.check(token_type, value):
            self.advance()
            return True
        return False

    def check(self, token_type, value=None):
        if self.is_at_end():
            return False
        current = self.peek()
        if current.type != token_type:
            return False
        if value is not None and current.value != value:
            return False
        return True

    def advance(self):
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def is_at_end(self):
        return self.current >= len(self.tokens)

    def peek(self):
        return self.tokens[self.current]

    def previous(self):
        return self.tokens[self.current - 1]

    def new_temp(self):
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp

    def emit(self, op, arg1, arg2, result):
        self.quads.append(Quad(op, arg1, arg2, result))

    def error(self, message):
        if self.is_at_end():
            # Если достигнут конец токенов, берем последний токен
            if self.tokens:
                token = self.tokens[-1]
                raise Exception(f"Ошибка в строке {token.line}, позиция {token.column + len(token.value)}: {message}")
            else:
                raise Exception(f"Ошибка: {message}")
        else:
            token = self.peek()
            raise Exception(f"Ошибка в строке {token.line}, позиция {token.column}: {message}")

    @staticmethod
    def populate_quad_table(widget, quads):
        table = widget.token_table
        table.setRowCount(0)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Операция", "Аргумент 1", "Аргумент 2", "Результат"])
        for quad in quads:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(quad.op))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(quad.arg1))
            table.setItem(row, 2, QtWidgets.QTableWidgetItem(quad.arg2))
            table.setItem(row, 3, QtWidgets.QTableWidgetItem(quad.result))

    @staticmethod
    def populate_error_table(widget, errors):
        """Заполняет таблицу ошибок в интерфейсе"""
        # Проверяем наличие метода add_error_to_table в виджете
        if hasattr(widget, 'add_error_to_table'):
            # Очищаем таблицу ошибок
            widget.clear_error_table()
            
            import re
            # Паттерн для извлечения строки и позиции из сообщения об ошибке
            pattern = r"Ошибка в строке (\d+), позиция (\d+): (.+)"
            
            for error in errors:
                match = re.search(pattern, error)
                if match:
                    line = match.group(1)
                    pos = match.group(2)
                    msg = match.group(3)
                    
                    # Добавляем ошибку в таблицу
                    widget.add_error_to_table(line, pos, "Синтаксическая", msg)
                else:
                    # Для ошибок, не соответствующих паттерну
                    widget.add_error_to_table(1, 1, "Общая", error)
        else:
            print("Ошибка: виджет не поддерживает метод add_error_to_table")
