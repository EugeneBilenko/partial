from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template import Context
from django.template.loader import get_template
from chemical.models import *
from chemical.views import _chemical_disease_interaction_data
from decodify.aggregators import ArrayAgg
from genome.helpers import get_gene_scores, get_potentially_problematic_genes, badges_for_gene


def chemical_disease_ajax(request, chemical):
    query_set = get_object_or_404(Chemical, slug=chemical)
    per_page = 20

    chemical_disease_interactions = _chemical_disease_interaction_data(request, query_set)

    page = request.GET.get("page")
    paginator = Paginator(chemical_disease_interactions, per_page)
    try:
        current_page = paginator.page(page)
    except PageNotAnInteger:
        current_page = paginator.page(2)
    except EmptyPage:
        current_page = paginator.page(paginator.num_pages)
    template = get_template('chemical/partials/table_bodies/chemical_disease.html')
    if current_page.has_next():
        has_next = True
        next_page_number = current_page.next_page_number()
    else:
        next_page_number = current_page.paginator.num_pages
        has_next = False
    context = Context({
        "disease_interactions": current_page.object_list
    })
    return JsonResponse({
        'paginator': {
            'has_next': has_next,
            'next_page_number': next_page_number,
        },
        'data': template.render(context)
    })


# NOT USED
# def chemical_gene_ajax(request, chemical):
#     query_set = get_object_or_404(Chemical, slug=chemical)
#     interactions = query_set.chemicalgeneinteraction_set.all().annotate(
#         total=Count('actions') + F('amount') - 1,
#         action=ArrayAgg('actions__action')
#     ).order_by('-total').prefetch_related(
#         "actions", "actions__interaction_type"
#     ).select_related("gene")
#
#     page = request.GET.get("page")
#     paginator = Paginator(interactions, 20)
#     try:
#         current_page = paginator.page(page)
#     except PageNotAnInteger:
#         current_page = paginator.page(1)
#     except EmptyPage:
#         current_page = paginator.page(paginator.num_pages)
#
#     interactions = current_page.object_list
#
#     all_interact_genes = {interaction.gene.id for interaction in interactions}
#     bad_genes = []
#     contains_risk_allele = []
#     gene_scores = []
#     if request.user.is_authenticated():
#         contains_risk_allele, bad_genes = badges_for_gene(request.user, all_interact_genes)
#
#     template = get_template('chemical/partials/table_bodies/chemical_gene.html')
#     if current_page.has_next():
#         has_next = True
#         next_page_number = current_page.next_page_number()
#     else:
#         next_page_number = current_page.paginator.num_pages
#         has_next = False
#     context = Context({
#         "interactions": interactions,
#         "bad_genes": bad_genes,
#         "contains_risk_allele": contains_risk_allele,
#         "gene_scores": gene_scores,
#     })
#
#     return JsonResponse({
#         'paginator': {
#             'has_next': has_next,
#             'next_page_number': next_page_number,
#         },
#         'data': template.render(context)
#     })


# NOT USED
# def chemical_pathway_ajax(request, chemical):
#     query_set = get_object_or_404(Chemical, slug=chemical)
#     interactions = query_set.chemicalpathway_set.all()
#
#     page = request.GET.get("page")
#     paginator = Paginator(interactions, 20)
#     try:
#         current_page = paginator.page(page)
#     except PageNotAnInteger:
#         current_page = paginator.page(1)
#     except EmptyPage:
#         current_page = paginator.page(paginator.num_pages)
#
#     interactions = current_page.object_list
#
#     template = get_template('chemical/partials/table_bodies/chemical_pathway.html')
#     if current_page.has_next():
#         has_next = True
#         next_page_number = current_page.next_page_number()
#     else:
#         next_page_number = current_page.paginator.num_pages
#         has_next = False
#     context = Context({
#         "pathway_list": interactions,
#     })
#
#     return JsonResponse({
#         'paginator': {
#             'has_next': has_next,
#             'next_page_number': next_page_number,
#         },
#         'data': template.render(context)
#     })
