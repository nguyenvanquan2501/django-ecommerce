from django import template

register = template.Library()

@register.filter
def index(lst, i):
    try:
        return lst[i-1]
    except:
        return None 