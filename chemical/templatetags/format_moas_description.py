from django import template
import re

from django.utils.safestring import mark_safe

register = template.Library()
pattern = re.compile(r".*\(([\d]{3,})\).*")
pattern_href = re.compile(r".*\((http://.*)\).*")


@register.filter
def format_moas_description(references):
    pubmed_urls = []
    result = ""

    for reference in references:
        parts = reference.description.split("\n")
        for part in parts:
            if pattern.search(part):
                pubmed_urls.append(pattern.sub('<a href="https://www.ncbi.nlm.nih.gov/pubmed/\g<1>">\g<1></a><br/>', part))
            elif pattern_href.search(part):
                pubmed_urls.append(pattern_href.sub('<a href="\g<1>"><i class="fa fa-info-circle"></i></a><br/>', part))
            else:
                result += "<br/>%s" % part
    result += "".join(set(pubmed_urls))

    return mark_safe(result)


