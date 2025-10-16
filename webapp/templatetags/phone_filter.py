import re
from django import template

register = template.Library()

@register.filter
def format_phone(value: str) -> str:
    if not value:
        return "Не указан"

    digits = re.sub(r'\D', '', value)

    if len(digits) != 11:
        return value

    return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"