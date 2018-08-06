from itertools import chain

from django.contrib.auth.models import User

from analysis.models import System
from analysis.templatetags.analysis_filters import is_system_threshold_reached

from chemical.models import SubstanceCategory
from recommendation.helpers import _get_chemicals_by_gene_direction


def get_recomendations_for_system(system):
    beneficial_cat = SubstanceCategory.objects.filter(slug="beneficial-substances").first()

    chemicals_for_genes, chem_dict = _get_chemicals_by_gene_direction(
        tuple(system.genes.all().values_list('id', flat=True))
    )
    system_chemicals = list(system.chemicals.all())
    if len(system_chemicals) >= 5:
        recommendations = system_chemicals
    else:
        recommendations = list(chain(system_chemicals, chemicals_for_genes.exclude(
            recommendation_status='disallow_everywhere'
        ).filter(
            categories__in=beneficial_cat.get_family().values_list('id', flat=True)
        )))[:5]

    for obj in recommendations:
        setattr(obj, "cnt", chem_dict.get(obj.pk, 0))

    return recommendations


def get_systems_queryset(request):
    if request.GET.get('show_user_systems'):
        users = User.objects.all()
    else:
        users = User.objects.filter(is_staff=True)
    return [item for item in System.objects.filter(user__in=users) if is_system_threshold_reached(item, request.user)]
