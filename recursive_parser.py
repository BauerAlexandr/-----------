from scanner import JSScanner, Token

class RecursiveSyntaxError(Exception):
    def __init__(self, message, line, column):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


class RecursiveDescentParser:
    def __init__(self):
        self.tokens = []
        self.current = 0
        self.call_stack = []  # Лог вызова процедур
        self.errors = []
        self.logs = []

    def parse(self, text):
        scanner = JSScanner()
        self.tokens = [t for t in scanner.tokenize(text) if t.type != 'WHITESPACE']
        self.current = 0
        self.call_stack = []
        self.errors = []
        self.logs = []

        try:
            self.log("== НАЧАЛО РАЗБОРА ==")
            self.parse_expr()
            if self.current < len(self.tokens):
                raise RecursiveSyntaxError("Лишние токены после конца выражения", self.tokens[self.current].line, self.tokens[self.current].column)
            self.log("== РАЗБОР ЗАВЕРШЕН УСПЕШНО ==")
        except RecursiveSyntaxError as e:
            self.errors.append({'message': e.message, 'line': e.line, 'column': e.column})
            self.log(f"ОШИБКА: {e.message} на строке {e.line}, позиции {e.column}")

        return self.call_stack, self.errors, self.logs

    def match(self, *expected_values):
        if self.current < len(self.tokens) and self.tokens[self.current].value in expected_values:
            self.log(f"match: {self.tokens[self.current].value}")
            self.current += 1
            return True
        return False

    def expect(self, expected_type):
        if self.current >= len(self.tokens):
            raise RecursiveSyntaxError(f"Ожидался {expected_type}, но достигнут конец ввода", -1, -1)

        token = self.tokens[self.current]
        if token.type != expected_type:
            raise RecursiveSyntaxError(f"Ожидался {expected_type}, найдено '{token.value}'", token.line, token.column)
        self.current += 1
        return token

    def log(self, message):
        self.logs.append(message)

    def parse_expr(self):
        self.call_stack.append("parse_expr")
        self.log("Вызов parse_expr")
        self.parse_expr_add_sub()
        while self.match("*", "/", "%"):
            self.parse_expr_add_sub()

    def parse_expr_add_sub(self):
        self.call_stack.append("parse_expr_add_sub")
        self.log("Вызов parse_expr_add_sub")
        self.parse_term()
        while self.match("+", "-"):
            self.parse_term()

    def parse_term(self):
        self.call_stack.append("parse_term")
        self.log("Вызов parse_term")
        if self.match("("):
            self.parse_expr()
            if not self.match(")"):
                token = self.tokens[self.current - 1] if self.current > 0 else Token("", "", 1, 1)
                raise RecursiveSyntaxError("Ожидалась закрывающая скобка ')'", token.line, token.column)
        else:
            self.parse_integer()

    def parse_integer(self):
        self.call_stack.append("parse_integer")
        self.log("Вызов parse_integer")
        if self.current >= len(self.tokens):
            raise RecursiveSyntaxError("Ожидалось целое число, но достигнут конец ввода", -1, -1)
        token = self.tokens[self.current]
        if token.type == "число":
            self.log(f"распознано число: {token.value}")
            self.current += 1
        else:
            raise RecursiveSyntaxError("Ожидалось целое число", token.line, token.column)
