import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SearchResult:
    """Класс для хранения результатов поиска"""
    pattern: str
    match: str
    start: int
    end: int
    line: int
    column: int

class RegexSearcher:
    """Класс для поиска по регулярным выражениям"""
    
    # Регулярные выражения для поиска
    PATTERNS = {
        'snils': r'\b\d{3}-\d{3}-\d{3}\s\d{2}\b',  # СНИЛС: XXX-XXX-XXX XX
        'mir_card': r'\b220[0-4]\d{12}\b',  # Номер карты Мир: начинается с 2200-2204
        'chemical_element': r'\b(?:H|He|Li|Be|B|C|N|O|F|Ne|Na|Mg|Al|Si|P|S|Cl|Ar|K|Ca|Sc|Ti|V|Cr|Mn|Fe|Co|Ni|Cu|Zn|Ga|Ge|As|Se|Br|Kr|Rb|Sr|Y|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|Cd|In|Sn|Sb|Te|I|Xe|Cs|Ba|La|Ce|Pr|Nd|Pm|Sm|Eu|Gd|Tb|Dy|Ho|Er|Tm|Yb|Lu|Hf|Ta|W|Re|Os|Ir|Pt|Au|Hg|Tl|Pb|Bi|Po|At|Rn|Fr|Ra|Ac|Th|Pa|U|Np|Pu|Am|Cm|Bk|Cf|Es|Fm|Md|No|Lr|Rf|Db|Sg|Bh|Hs|Mt|Ds|Rg|Cn|Nh|Fl|Mc|Lv|Ts|Og)\b'
    }
    
    @staticmethod
    def find_all_matches(text: str, pattern_type: str) -> List[SearchResult]:
        """
        Поиск всех совпадений в тексте для заданного типа шаблона
        
        Args:
            text: Исходный текст для поиска
            pattern_type: Тип шаблона ('snils', 'mir_card', 'chemical_element')
            
        Returns:
            Список объектов SearchResult с найденными совпадениями
        """
        if pattern_type not in RegexSearcher.PATTERNS:
            raise ValueError(f"Неизвестный тип шаблона: {pattern_type}")
        
        pattern = RegexSearcher.PATTERNS[pattern_type]
        results = []
        
        # Разбиваем текст на строки для определения позиции
        lines = text.split('\n')
        current_pos = 0
        
        for line_num, line in enumerate(lines, 1):
            for match in re.finditer(pattern, line):
                start = match.start()
                end = match.end()
                results.append(SearchResult(
                    pattern=pattern_type,
                    match=match.group(),
                    start=current_pos + start,
                    end=current_pos + end,
                    line=line_num,
                    column=start + 1  # +1 для отображения с 1, а не с 0
                ))
            current_pos += len(line) + 1  # +1 для учета символа новой строки
        
        return results
    
    @staticmethod
    def get_pattern_description(pattern_type: str) -> str:
        """Возвращает описание шаблона для отображения пользователю"""
        descriptions = {
            'snils': 'СНИЛС (формат: XXX-XXX-XXX XX)',
            'mir_card': 'Номер карты Мир (начинается с 2200-2204)',
            'chemical_element': 'Химический элемент из таблицы Менделеева'
        }
        return descriptions.get(pattern_type, 'Неизвестный шаблон')
    
    @staticmethod
    def validate_snils(snils: str) -> bool:
        """Проверка контрольной суммы СНИЛС"""
        if not re.match(RegexSearcher.PATTERNS['snils'], snils):
            return False
        
        # Убираем дефисы и пробел
        numbers = snils.replace('-', '').replace(' ', '')
        
        # Проверяем контрольную сумму
        if len(numbers) != 11:
            return False
            
        # Вычисляем контрольную сумму
        checksum = 0
        for i in range(9):
            checksum += int(numbers[i]) * (9 - i)
            
        checksum = checksum % 101
        if checksum == 100:
            checksum = 0
            
        return checksum == int(numbers[-2:])
    
    @staticmethod
    def validate_mir_card(card_number: str) -> bool:
        """Проверка номера карты Мир по алгоритму Луна"""
        if not re.match(RegexSearcher.PATTERNS['mir_card'], card_number):
            return False
            
        # Алгоритм Луна
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
            
        return checksum % 10 == 0 