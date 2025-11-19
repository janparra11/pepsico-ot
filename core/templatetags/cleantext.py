import unicodedata
from django import template

register = template.Library()

@register.filter
def cleantext(value):
    if not value:
        return value
    try:
        fixed = value.encode("latin1", "ignore").decode("utf-8", "ignore")
        fixed = unicodedata.normalize("NFC", fixed)
        return fixed
    except:
        return value
