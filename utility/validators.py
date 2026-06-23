import re
from datetime import datetime
from typing import Optional, Tuple


class FormValidators:
    """Валидаторы для форм бота"""

    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """Валидация имени (ФИО)"""
        if not name or len(name.strip()) < 2:
            return False, "Имя должно содержать минимум 2 символа"
        if len(name) > 100:
            return False, "Имя слишком длинное (макс. 100 символов)"

        # Проверка на наличие недопустимых символов
        if re.search(r'[0-9@#$%^&*()_+=<>?/\\|]', name):
            return False, "Имя содержит недопустимые символы"
        return True, ""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Валидация email"""
        if not email:
            return False, "Email не может быть пустым"
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Некорректный формат email"
        return True, ""

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Валидация телефона"""
        if not phone:
            return False, "Телефон не может быть пустым"
        # Убираем все кроме цифр
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10:
            return False, "Номер телефона слишком короткий"
        if len(digits) > 15:
            return False, "Номер телефона слишком длинный"
        return True, ""

    @staticmethod
    def validate_dates(date_str: str) -> Tuple[bool, str]:
        """Валидация дат (формат: DD.MM.YYYY - DD.MM.YYYY)"""
        try:
            dates = date_str.split('-')
            if len(dates) != 2:
                return False, "Неверный формат дат. Используйте: ДД.ММ.ГГГГ - ДД.ММ.ГГГГ"

            start_date = datetime.strptime(dates[0].strip(), '%d.%m.%Y')
            end_date = datetime.strptime(dates[1].strip(), '%d.%m.%Y')

            if end_date < start_date:
                return False, "Дата окончания не может быть раньше даты начала"

            return True, ""
        except ValueError:
            return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ"

    @staticmethod
    def validate_passport(passport: str) -> Tuple[bool, str]:
        """Валидация паспортных данных"""
        if not passport or len(passport.strip()) < 5:
            return False, "Паспортные данные слишком короткие"
        if len(passport) > 50:
            return False, "Паспортные данные слишком длинные"
        return True, ""

    @staticmethod
    def validate_question(text: str, max_length: int = 500) -> Tuple[bool, str]:
        """Валидация вопроса"""
        if not text or len(text.strip()) < 5:
            return False, "Вопрос должен содержать минимум 5 символов"
        if len(text) > max_length:
            return False, f"Вопрос слишком длинный (макс. {max_length} символов)"
        return True, ""

    @staticmethod
    def validate_iban(iban: str) -> Tuple[bool, str]:
        """Валидация IBAN"""
        if not iban:
            return False, "IBAN не может быть пустым"

        # Базовая проверка формата
        iban_clean = iban.replace(' ', '').upper()
        if len(iban_clean) < 15 or len(iban_clean) > 34:
            return False, "Неверная длина IBAN"
        if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$', iban_clean):
            return False, "Неверный формат IBAN"
        return True, ""

    @staticmethod
    def validate_card_number(card: str) -> Tuple[bool, str]:
        """Валидация номера карты"""
        if not card:
            return False, "Номер карты не может быть пустым"
        digits = re.sub(r'\D', '', card)
        if len(digits) < 16 or len(digits) > 19:
            return False, "Неверная длина номера карты"


        def luhn_check(card_num):
            sum = 0
            num_digits = len(card_num)
            parity = num_digits % 2
            for i in range(num_digits):
                digit = int(card_num[i])
                if i % 2 == parity:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                sum += digit
            return sum % 10 == 0

        if not luhn_check(digits):
            return False, "Неверный номер карты"
        return True, ""


validators = FormValidators()