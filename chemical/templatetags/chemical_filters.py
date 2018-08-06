from django import template

from chemical.models import ChemicalGeneInteraction
from genome.management.commands.uniprot_import import chunks


register = template.Library()


@register.filter
def page_range(page):
    offset = 5
    start_page = page.number - offset
    end_page = page.number + offset
    if start_page <= 1:
        start_page = 1
    if end_page > page.paginator.num_pages:
        end_page = page.paginator.num_pages + 1
    return range(start_page, end_page)


@register.filter
def chunk_queryset(queryset, num_genes_on_page):
    return chunks(queryset, num_genes_on_page // 4)


@register.filter
def split(string, delimiter):
    return string.split(delimiter)


@register.filter
def has_chemical_gene_interactions(id):
    return ChemicalGeneInteraction.objects.filter(chemical_id=id).exists()
