from django import template
import re

from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def format_moas_targets(value):
    target_list = value.target.all()
    response_list = []
    for target in target_list:
        if target.gene:
            response_list.append('<a href="/gene/%s">%s</a>' % (target.gene.slug, target.name))
        else:
            response_list.append(target.name)
    return mark_safe("<br/>".join(response_list))


