import re
from scanner import JSScanner, Token

class SyntaxError:
    """Класс для представления синтаксической ошибки"""
    
    def __init__(self, message, line, column, token_value=None):
        self.message = message
        self.line = line
        self.column = column
        self.value = token_value

class JSParser:
    """Синтаксический анализатор для JavaScript на основе конечного автомата
    
    Реализует анализ объявления ассоциативного массива по грамматике:
    1. ‹Assoc› → 'let'›‹E1›
    2. ‹E1› → 'Letter'‹ID›
    3. ‹ID› → 'Letter'‹ID›
    4. ‹ID› → 'Digit'‹ID›
    5. ‹ID› → '='‹E2›
    6. ‹E2› → '{'‹E3›
    7. ‹E3› → ' " '‹S›
    8. ‹E3› → '}'‹End›
    9. ‹S› → ' symbols '‹S1›
    10. ‹S1› → ' symbols '‹S1›
    11. ‹S1› → ' " '‹K›
    12. ‹K› → ' : '‹V›
    13. ‹V› → ' digit '‹I›
    14. ‹I› → ' digit '‹I›
    15. ‹I› → ' , '‹E3›
    16. ‹I› → ' } '‹End›
    17. ‹End› → ‹;›
    """
    
    # Состояния конечного автомата
    STATES = {
        'START': 0,      # Начальное состояние
        'KEYWORD': 1,    # Ключевое слово let
        'ID_START': 2,   # Начало идентификатора
        'ID': 3,         # Идентификатор
        'ASSIGN': 4,     # Оператор присваивания =
        'LBRACE': 5,     # Открывающая фигурная скобка {
        'KEY_START': 6,  # Начало ключа (открывающая кавычка)
        'KEY': 7,        # Ключ (строка в кавычках)
        'KEY_END': 8,    # Конец ключа (закрывающая кавычка)
        'COLON': 9,      # Двоеточие :
        'VALUE': 10,     # Числовое значение
        'COMMA': 11,     # Запятая ,
        'RBRACE': 12,    # Закрывающая фигурная скобка }
        'SEMICOLON': 13, # Точка с запятой ;
        'END': 14,       # Конечное состояние (успешное)
        'ERROR': 15      # Ошибка
    }
    
    # Словарь для получения имени состояния по его коду
    STATE_NAMES = {v: k for k, v in STATES.items()}
    
    def __init__(self):
        self.scanner = JSScanner()
        self.tokens = []
        self.current_token_index = 0
        self.syntax_errors = []  # Изменено с errors на syntax_errors для ясности
        self.current_state = self.STATES['START']
        self.recovery_mode = False  # Флаг режима восстановления для метода Айронса
        self.expected_tokens = []   # Список ожидаемых токенов для текущего состояния
        self.recovery_logs = []     # Журнал восстановления после ошибок
        self.debug_mode = True      # Режим отладки для логирования
    
    def parse(self, text):
        """Анализирует JavaScript код и возвращает результат"""
        # Инициализация сканера для получения токенов
        self.scanner = JSScanner()
        self.tokens = self.scanner.tokenize(text)
        self.errors = []  # Инициализируем список для лексических ошибок
        
        # Сбрасываем синтаксические ошибки и журнал восстановления перед анализом
        self.syntax_errors = []
        self.recovery_logs = []
        
        # Проверяем на лексические ошибки из токенов
        for token in self.tokens:
            if token.type == "ERROR":
                self.errors.append({
                    'message': f"Лексическая ошибка: {token.value}",
                    'line': token.line,
                    'column': token.column
                })
                self.add_error(f"Лексическая ошибка: {token.value}", token.line, token.column)
        
        # Анализируем токены на наличие объявлений ассоциативных массивов
        if self.tokens:
            # Анализируем все токены как один непрерывный поток
            self.analyze_assoc_array(self.tokens)
        
        # Возвращаем результаты анализа - два значения для распаковки
        return self.tokens, self.syntax_errors
    
    def analyze_assoc_array(self, tokens):
        """Анализирует объявление ассоциативного массива как конечный автомат
        с применением метода Айронса для нейтрализации ошибок"""
        self.current_state = self.STATES['START']
        self.current_token_index = 0
        
        while self.current_token_index < len(tokens):
            current_token = tokens[self.current_token_index]
            
            # Определяем ожидаемые токены для текущего состояния
            self.set_expected_tokens()
            
            # Логируем текущее состояние для отладки
            if self.debug_mode:
                self.log_state(current_token)
            
            if self.current_state == self.STATES['START']:
                # Ожидаем ключевое слово 'let'
                if current_token.type == "ключевое слово" and current_token.value == "let":
                    self.current_state = self.STATES['KEYWORD']
                else:
                    # Обрабатываем случай, когда вместо ключевого слова 'let' идет идентификатор или другое
                    if current_token.type == "идентификатор" and current_token.value.lower().startswith("let"):
                        # Ошибка в ключевом слове, например "letS" вместо "let"
                        self.add_error(f"Ошибка: '{current_token.value}' не является ключевым словом 'let'", 
                                    current_token.line, current_token.column, current_token.value)
                        # Применение метода Айронса: считаем это ключевым словом 'let' и продолжаем
                        self.log_recovery(f"Принято '{current_token.value}' как ключевое слово 'let'")
                        self.current_state = self.STATES['KEYWORD']
                    else:
                        # Не начинает строку с ключевого слова 'let' или подобного идентификатора
                        self.add_error("Ожидалось ключевое слово 'let'", 
                                    current_token.line, current_token.column, current_token.value)
                        # Применение метода Айронса: пропускаем токен, ищем ближайшее 'let'
                        if not self.recover_from_error("ключевое слово", "let"):
                            self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['KEYWORD']:
                # После 'let' ожидаем идентификатор, начинающийся с буквы
                if current_token.type == "идентификатор":
                    # Проверяем, что идентификатор начинается с буквы
                    if re.match(r'^[a-zA-Z]', current_token.value):
                        self.current_state = self.STATES['ID']
                    else:
                        self.add_error("Идентификатор должен начинаться с буквы", 
                                     current_token.line, current_token.column, current_token.value)
                        # Применение метода Айронса: все равно принимаем идентификатор
                        self.log_recovery(f"Принят идентификатор '{current_token.value}', хотя он начинается неправильно")
                        self.current_state = self.STATES['ID']
                else:
                    # Проверяем особый случай, когда символ @ встроен в идентификатор
                    if current_token.type == "ERROR" and "@" in current_token.value:
                        self.add_error("Недопустимый символ '@' в идентификаторе", 
                                    current_token.line, current_token.column, current_token.value)
                        # Применение метода Айронса: пропускаем и продолжаем
                        self.log_recovery(f"Пропускаем недопустимый идентификатор '{current_token.value}'")
                        self.current_token_index += 1
                        continue
                    elif current_token.type == "оператор присваивания":
                        # Отсутствует идентификатор между 'let' и '='
                        self.add_error("Отсутствует идентификатор между 'let' и '='", 
                                     current_token.line, current_token.column, current_token.value)
                        # Применение метода Айронса: вставляем воображаемый идентификатор и продолжаем
                        self.log_recovery("Вставлен воображаемый идентификатор перед оператором присваивания")
                        self.current_state = self.STATES['ASSIGN']
                    else:
                        self.add_error("Ожидался идентификатор после 'let'", 
                                     current_token.line, current_token.column, current_token.value)
                        # Применение метода Айронса: ищем следующий токен присваивания или идентификатор
                        if not self.recover_to_state(self.STATES['ID']):
                            self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['ID']:
                # После идентификатора ожидаем оператор присваивания '='
                if current_token.type == "оператор присваивания":
                    self.current_state = self.STATES['ASSIGN']
                else:
                    self.add_error("Ожидался оператор присваивания '='", 
                                 current_token.line, current_token.column, current_token.value)
                    if current_token.type == "открывающая фигурная скобка":
                        # Пропущен оператор присваивания, но есть открывающая скобка
                        # Применение метода Айронса: вставляем воображаемый оператор '='
                        self.log_recovery("Вставлен воображаемый оператор присваивания '='")
                        self.current_state = self.STATES['LBRACE']
                    else:
                        # Применение метода Айронса: ищем следующую открывающую скобку
                        if not self.recover_to_state(self.STATES['ASSIGN']):
                            self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['ASSIGN']:
                # После '=' ожидаем открывающую фигурную скобку '{'
                if current_token.type == "открывающая фигурная скобка":
                    self.current_state = self.STATES['LBRACE']
                else:
                    self.add_error("Ожидалась открывающая фигурная скобка '{'", 
                                 current_token.line, current_token.column, current_token.value)
                    # Применение метода Айронса: ищем открывающую скобку или восстанавливаемся
                    if not self.recover_to_state(self.STATES['LBRACE']):
                        self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['LBRACE']:
                # После '{' ожидаем либо строку (открывающую кавычку), либо закрывающую скобку '}'
                if current_token.type == "строка":
                    self.current_state = self.STATES['KEY']
                elif current_token.type == "закрывающая фигурная скобка":
                    self.current_state = self.STATES['RBRACE']
                else:
                    self.add_error("Ожидалась строка в кавычках или закрывающая фигурная скобка '}'", 
                                 current_token.line, current_token.column, current_token.value)
                    # Применение метода Айронса: ищем строку или закрывающую скобку
                    if not self.recover_to_next_key_or_brace():
                        self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['KEY']:
                # После ключа ожидаем двоеточие ':'
                if current_token.type == "двоеточие":
                    self.current_state = self.STATES['COLON']
                else:
                    self.add_error("Ожидалось двоеточие ':'", 
                                 current_token.line, current_token.column, current_token.value)
                    if current_token.type == "число":
                        # Пропущено двоеточие, но есть числовое значение
                        # Применение метода Айронса: вставляем воображаемое двоеточие
                        self.log_recovery("Вставлено воображаемое двоеточие ':'")
                        self.current_state = self.STATES['VALUE']
                    else:
                        # Применение метода Айронса: ищем числовое значение
                        if not self.recover_to_state(self.STATES['COLON']):
                            self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['COLON']:
                # После ':' ожидаем числовое значение
                if current_token.type == "число":
                    self.current_state = self.STATES['VALUE']
                else:
                    self.add_error("Ожидалось числовое значение", 
                                 current_token.line, current_token.column, current_token.value)
                    if current_token.type == "запятая":
                        # Пропущено значение, но есть запятая
                        # Применение метода Айронса: вставляем воображаемое числовое значение
                        self.log_recovery("Вставлено воображаемое числовое значение")
                        self.current_state = self.STATES['COMMA']
                    elif current_token.type == "закрывающая фигурная скобка":
                        # Пропущено значение, но есть закрывающая скобка
                        self.log_recovery("Вставлено воображаемое числовое значение перед закрывающей скобкой")
                        self.current_state = self.STATES['RBRACE']
                    else:
                        # Применение метода Айронса: ищем запятую или закрывающую скобку
                        if not self.recover_to_state(self.STATES['VALUE']):
                            self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['VALUE']:
                # После значения ожидаем либо запятую ',', либо закрывающую скобку '}'
                if current_token.type == "запятая":
                    self.current_state = self.STATES['COMMA']
                elif current_token.type == "закрывающая фигурная скобка":
                    self.current_state = self.STATES['RBRACE']
                else:
                    self.add_error("Ожидалась запятая ',' или закрывающая фигурная скобка '}'", 
                                 current_token.line, current_token.column, current_token.value)
                    # Применение метода Айронса: ищем запятую или закрывающую скобку
                    if not self.recover_to_comma_or_brace():
                        self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['COMMA']:
                # После ',' ожидаем новую строку (начало ключа)
                if current_token.type == "строка":
                    self.current_state = self.STATES['KEY']
                elif current_token.type == "закрывающая фигурная скобка":
                    # Запятая после последнего элемента допустима
                    self.current_state = self.STATES['RBRACE']
                else:
                    self.add_error("Ожидалась строка в кавычках (ключ)", 
                                 current_token.line, current_token.column, current_token.value)
                    # Применение метода Айронса: ищем строку или закрывающую скобку
                    if not self.recover_to_next_key_or_brace():
                        self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['RBRACE']:
                # После '}' ожидаем точку с запятой ';'
                if current_token.type == "точка с запятой":
                    self.current_state = self.STATES['SEMICOLON']
                    # После точки с запятой готовы к новому объявлению
                    self.current_state = self.STATES['START']
                else:
                    self.add_error("Ожидалась точка с запятой ';'", 
                                 current_token.line, current_token.column, current_token.value)
                    if current_token.type == "ключевое слово" and current_token.value == "let":
                        # Отсутствует точка с запятой, но начинается новое объявление
                        # Применение метода Айронса: вставляем воображаемую точку с запятой
                        self.log_recovery("Вставлена воображаемая точка с запятой ';'")
                        self.current_state = self.STATES['START']
                        continue  # Повторно обработаем current_token как начало нового объявления
                    else:
                        # Применение метода Айронса: продолжаем поиск следующего объявления
                        self.current_state = self.STATES['ERROR']
            
            elif self.current_state == self.STATES['ERROR']:
                # В состоянии ошибки пытаемся восстановиться и начать анализ заново
                if current_token.type == "точка с запятой":
                    self.log_recovery("Восстановление: найдена точка с запятой")
                    self.current_state = self.STATES['START']  # Возвращаемся в начальное состояние
                elif current_token.type == "ключевое слово" and current_token.value == "let":
                    # Нашли новое ключевое слово 'let', начинаем заново
                    self.log_recovery("Восстановление: найдено новое ключевое слово 'let'")
                    self.current_state = self.STATES['START']
                    continue  # Повторно обработаем current_token как начало нового объявления
                elif current_token.type == "закрывающая фигурная скобка":
                    # Нашли закрывающую скобку, переходим к ожиданию точки с запятой
                    self.log_recovery("Восстановление: найдена закрывающая фигурная скобка")
                    self.current_state = self.STATES['RBRACE']
            
            # Переходим к следующему токену
            self.current_token_index += 1
            
        # Проверяем, что достигли конечного состояния или остались в состоянии ошибки
        if self.current_state != self.STATES['START']:
            last_token = tokens[-1] if tokens else None
            line = last_token.line if last_token else 1
            column = last_token.column + len(last_token.value) + 1 if last_token else 1
            
            # Добавляем ошибку о незавершенном объявлении в зависимости от состояния
            if self.current_state == self.STATES['KEYWORD']:
                self.add_error("Незавершенное объявление: отсутствует идентификатор после 'let'", line, column)
            elif self.current_state == self.STATES['ID']:
                self.add_error("Незавершенное объявление: отсутствует оператор присваивания '='", line, column)
            elif self.current_state == self.STATES['ASSIGN']:
                self.add_error("Незавершенное объявление: отсутствует открывающая фигурная скобка '{'", line, column)
            elif self.current_state == self.STATES['LBRACE']:
                self.add_error("Незавершенный объект: отсутствует содержимое или закрывающая скобка '}'", line, column)
            elif self.current_state == self.STATES['KEY']:
                self.add_error("Незавершенное свойство: отсутствует двоеточие после ключа", line, column)
            elif self.current_state == self.STATES['COLON']:
                self.add_error("Незавершенное свойство: отсутствует значение после двоеточия", line, column)
            elif self.current_state == self.STATES['VALUE'] or self.current_state == self.STATES['COMMA']:
                self.add_error("Незавершенный объект: отсутствует запятая или закрывающая скобка '}'", line, column)
            elif self.current_state == self.STATES['RBRACE']:
                self.add_error("Незавершенное объявление: отсутствует точка с запятой ';'", line, column)
            elif self.current_state != self.STATES['ERROR']:
                self.add_error("Неожиданный конец ввода", line, column)
    
    def log_state(self, token):
        """Записывает текущее состояние в журнал для отладки"""
        state_name = self.STATE_NAMES.get(self.current_state, "НЕИЗВЕСТНО")
        self.recovery_logs.append(f"Состояние: {state_name}, Токен: {token.type} '{token.value}' на {token.line}:{token.column}")
    
    def log_recovery(self, message):
        """Записывает информацию о восстановлении после ошибки"""
        if self.debug_mode:
            self.recovery_logs.append(f"[Восстановление] {message}")
    
    def get_recovery_logs(self):
        """Возвращает журнал восстановления"""
        return self.recovery_logs
    
    def set_expected_tokens(self):
        """Устанавливает список ожидаемых токенов для текущего состояния
        Это необходимо для метода Айронса при восстановлении после ошибок"""
        if self.current_state == self.STATES['START']:
            self.expected_tokens = [("ключевое слово", "let")]
        elif self.current_state == self.STATES['KEYWORD']:
            self.expected_tokens = [("идентификатор", None)]
        elif self.current_state == self.STATES['ID']:
            self.expected_tokens = [("оператор присваивания", "=")]
        elif self.current_state == self.STATES['ASSIGN']:
            self.expected_tokens = [("открывающая фигурная скобка", "{")]
        elif self.current_state == self.STATES['LBRACE']:
            self.expected_tokens = [("строка", None), ("закрывающая фигурная скобка", "}")]
        elif self.current_state == self.STATES['KEY']:
            self.expected_tokens = [("двоеточие", ":")]
        elif self.current_state == self.STATES['COLON']:
            self.expected_tokens = [("число", None)]
        elif self.current_state == self.STATES['VALUE']:
            self.expected_tokens = [("запятая", ","), ("закрывающая фигурная скобка", "}")]
        elif self.current_state == self.STATES['COMMA']:
            self.expected_tokens = [("строка", None), ("закрывающая фигурная скобка", "}")]
        elif self.current_state == self.STATES['RBRACE']:
            self.expected_tokens = [("точка с запятой", ";")]
    
    def recover_from_error(self, expected_type, expected_value=None):
        """Метод Айронса: восстанавливается после ошибки, пропуская токены
        до тех пор, пока не найдет токен указанного типа и значения"""
        original_index = self.current_token_index
        self.current_token_index += 1  # Пропускаем текущий токен
        
        self.log_recovery(f"Поиск токена типа {expected_type}" + 
                         (f" со значением {expected_value}" if expected_value else ""))
        
        # Ищем следующий токен указанного типа
        while self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            if token.type == expected_type and (expected_value is None or token.value == expected_value):
                # Нашли подходящий токен
                self.log_recovery(f"Успешное восстановление: найден токен типа {expected_type}" + 
                                 (f" со значением {expected_value}" if expected_value else ""))
                return True
            self.current_token_index += 1
        
        # Не нашли подходящий токен, возвращаемся на позицию ошибки
        self.log_recovery("Восстановление не удалось: не найден ожидаемый токен")
        self.current_token_index = original_index
        return False
    
    def recover_to_state(self, target_state):
        """Метод Айронса: восстанавливается после ошибки, пытаясь перейти
        в указанное состояние путем пропуска токенов"""
        # Сохраняем исходную позицию
        original_index = self.current_token_index
        original_state = self.current_state
        
        target_state_name = self.STATE_NAMES.get(target_state, "НЕИЗВЕСТНО")
        self.log_recovery(f"Попытка восстановления до состояния {target_state_name}")
        
        # Помечаем, что мы в режиме восстановления
        self.recovery_mode = True
        
        # Восстанавливаемся в зависимости от целевого состояния
        if target_state == self.STATES['ID']:
            # Ищем идентификатор или следующее 'let'
            found = self.recover_from_error("идентификатор")
            if found:
                self.current_state = self.STATES['ID']
                self.recovery_mode = False
                return True
        
        elif target_state == self.STATES['ASSIGN']:
            # Ищем оператор присваивания или открывающую скобку
            found = self.recover_from_error("оператор присваивания")
            if found:
                self.current_state = self.STATES['ASSIGN']
                self.recovery_mode = False
                return True
                
            # Или ищем открывающую скобку
            self.current_token_index = original_index
            found = self.recover_from_error("открывающая фигурная скобка")
            if found:
                self.current_state = self.STATES['LBRACE']
                self.recovery_mode = False
                return True
        
        elif target_state == self.STATES['LBRACE']:
            # Ищем открывающую скобку
            found = self.recover_from_error("открывающая фигурная скобка")
            if found:
                self.current_state = self.STATES['LBRACE']
                self.recovery_mode = False
                return True
        
        elif target_state == self.STATES['COLON']:
            # Ищем двоеточие или числовое значение
            found = self.recover_from_error("двоеточие")
            if found:
                self.current_state = self.STATES['COLON']
                self.recovery_mode = False
                return True
                
            # Или ищем числовое значение
            self.current_token_index = original_index
            found = self.recover_from_error("число")
            if found:
                self.current_state = self.STATES['VALUE']
                self.recovery_mode = False
                return True
        
        elif target_state == self.STATES['VALUE']:
            # Ищем числовое значение, запятую или закрывающую скобку
            found = self.recover_from_error("число")
            if found:
                self.current_state = self.STATES['VALUE']
                self.recovery_mode = False
                return True
                
            # Или ищем запятую
            self.current_token_index = original_index
            found = self.recover_from_error("запятая")
            if found:
                self.current_state = self.STATES['COMMA']
                self.recovery_mode = False
                return True
                
            # Или ищем закрывающую скобку
            self.current_token_index = original_index
            found = self.recover_from_error("закрывающая фигурная скобка")
            if found:
                self.current_state = self.STATES['RBRACE']
                self.recovery_mode = False
                return True
        
        # Не смогли восстановиться, возвращаемся в исходное состояние
        self.log_recovery(f"Восстановление до состояния {target_state_name} не удалось")
        self.current_token_index = original_index
        self.current_state = original_state
        self.recovery_mode = False
        return False
    
    def recover_to_next_key_or_brace(self):
        """Метод Айронса: восстанавливается, ища следующий ключ (строку) или закрывающую скобку"""
        original_index = self.current_token_index
        self.current_token_index += 1  # Пропускаем текущий токен
        
        self.log_recovery("Поиск следующего ключа (строки) или закрывающей скобки")
        
        while self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            if token.type == "строка":
                self.log_recovery(f"Найдена строка '{token.value}', переходим в состояние KEY")
                self.current_state = self.STATES['KEY']
                return True
            elif token.type == "закрывающая фигурная скобка":
                self.log_recovery("Найдена закрывающая скобка, переходим в состояние RBRACE")
                self.current_state = self.STATES['RBRACE']
                return True
            self.current_token_index += 1
        
        # Не нашли ни строку, ни закрывающую скобку
        self.log_recovery("Не найдено ни строки, ни закрывающей скобки")
        self.current_token_index = original_index
        return False
    
    def recover_to_comma_or_brace(self):
        """Метод Айронса: восстанавливается, ища запятую или закрывающую скобку"""
        original_index = self.current_token_index
        self.current_token_index += 1  # Пропускаем текущий токен
        
        self.log_recovery("Поиск запятой или закрывающей скобки")
        
        while self.current_token_index < len(self.tokens):
            token = self.tokens[self.current_token_index]
            if token.type == "запятая":
                self.log_recovery("Найдена запятая, переходим в состояние COMMA")
                self.current_state = self.STATES['COMMA']
                return True
            elif token.type == "закрывающая фигурная скобка":
                self.log_recovery("Найдена закрывающая скобка, переходим в состояние RBRACE")
                self.current_state = self.STATES['RBRACE']
                return True
            self.current_token_index += 1
        
        # Не нашли ни запятую, ни закрывающую скобку
        self.log_recovery("Не найдено ни запятой, ни закрывающей скобки")
        self.current_token_index = original_index
        return False
    
    def add_error(self, message, line, column, token_value=None):
        """Добавляет ошибку в список ошибок"""
        error = SyntaxError(message, line, column, token_value)
        self.syntax_errors.append(error)
        
        # Логируем ошибку
        if self.debug_mode:
            self.log_recovery(f"Ошибка: {message} на {line}:{column}" + 
                             (f" ('{token_value}')" if token_value else "")) 