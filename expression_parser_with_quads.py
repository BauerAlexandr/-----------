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
    def __init__(self):
        self.scanner = JSScanner()
        self.tokens = []
        self.current = 0
        self.temp_counter = 1
        self.quads = []
        self.errors = []

    def parse(self, text):
        self.tokens = [t for t in self.scanner.tokenize(text) if t.type != "WHITESPACE"]
        self.current = 0
        self.temp_counter = 1
        self.quads = []
        self.errors = []

        try:
            result = self.E()
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
