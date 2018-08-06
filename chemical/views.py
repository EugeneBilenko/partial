import string


from dal import autocomplete
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Max
from django.db.models import F
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET
from chemical.models import *
from decodify.aggregators import ArrayAgg, JsonAgg, ArrayaAggDelimited
from decodify.helpers import get_geo_location
from .serializers import ChemicalInteractsGenesSerializer
# Create your views here.
from chemical.serializers import ChemicalInteractsDiseaseSerializer


class OrganismAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Organism.objects.none()

        qs = Organism.objects.all()

        if self.q:
            qs = qs.filter(Q(english_name__istartswith=self.q) | Q(latin_name__istartswith=self.q))

        return qs


class PreparationAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Preparations.objects.none()

        qs = Preparations.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class CategoryAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return SubstanceCategory.objects.none()

        qs = SubstanceCategory.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class GeneAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Gene.objects.none()

        qs = Gene.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class ChemicalAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Chemical.objects.none()

        qs = Chemical.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class InteractionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return ChemicalGeneInteraction.objects.none()

        qs = ChemicalGeneInteraction.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class InteractionTypeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return ChemicalGeneInteractionType.objects.none()

        qs = ChemicalGeneInteractionType.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class HealthEffectAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return HealthEffect.objects.none()

        qs = HealthEffect.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


def _chemical_gene_interaction_data(request, query_set):
    interactions = query_set.chemicalgeneinteraction_set.all().annotate(
        total=Count('actions') + F('amount') - 1).order_by('-total').prefetch_related(
        "actions", "actions__interaction_type"
    ).select_related("gene")
    return interactions


def _chemical_disease_interaction_data(request, query_set):
    interactions = ChemicalDiseaseInteraction.objects.filter(chemical=query_set).prefetch_related(
        "disease"
    ).values(
        "disease__slug", "disease__name"
    ).annotate(
        chemicals=ArrayAgg("chemical__pk"),
        max_inference_score=Max("inference_score"),
        genes=JsonAgg("inference_gene__name", 'inference_gene__slug', distinct=True),
        pubmed_ids=ArrayaAggDelimited("pub_med_ids", delimiter="|", distinct=True)
    ).order_by("-inference_score")
    return interactions


def chemical(request, chemical):
    query_set = get_object_or_404(Chemical.objects.prefetch_related("relation"), slug=chemical)

    location = get_geo_location(request)

    per_page = 20

    substance_gene_interaction = query_set.chemicalgeneinteraction_set.none()

    interactions = query_set.chemicalgeneinteraction_set.all().annotate(
        total=Count('actions') + F('amount') -1,
        action=ArrayAgg('actions__action')
    ).order_by('-total').prefetch_related(
        "actions", "actions__interaction_type"
    ).select_related("gene")
    chemical_disease_interactions = _chemical_disease_interaction_data(request, query_set)

    organisms = query_set.concentrations.values("organism__english_name", "organism__slug", "conc_unit", "unified_concentration").filter(rel_type="organism", unified_concentration__gte=0.0).order_by("-unified_concentration").all()[:20]

    t3db_data = query_set.t3db_data.first()
    top_interactions = interactions.values('gene__name', 'gene__slug', 'interaction', 'total', 'action',
                                           'gene__exception_status', 'gene__description_simple', 'gene__function', 'pub_med_ids')[:10]

    bad_genes = []
    contains_risk_allele = []
    if request.is_ajax():
        page = request.GET.get('page')
        if page == '1':
            page = 2
        page_type = request.GET.get('page_type')

        if page_type == 'problematic-gene':
            page_type = substance_gene_interaction
        elif page_type == 'disease-interaction':
            page_type = chemical_disease_interactions
        else:
            page_type = interactions

        paginator = Paginator(page_type, per_page)

        try:
            current_page = paginator.page(page)
        except PageNotAnInteger:
            current_page = paginator.page(2)
        except EmptyPage:
            current_page = paginator.page(paginator.num_pages)

        if request.GET.get('page_type') == 'disease-interaction':
            return JsonResponse(current_page, encoder=ChemicalInteractsDiseaseSerializer, safe=False)
        else:
            return JsonResponse(current_page, encoder=ChemicalInteractsGenesSerializer, safe=False)

    return render(request, "chemical/chemical.html", {
        "location": location,
        "query_set": query_set,
        "t3db_data": t3db_data,
        "top_interactions": top_interactions,
        "substance_gene_interaction": substance_gene_interaction[:per_page],
        "substance_gene_interaction_has_page": substance_gene_interaction.count() > per_page,
        "disease_interactions": chemical_disease_interactions[:per_page],
        "bad_genes": bad_genes,
        "contains_risk_allele": contains_risk_allele,
        "organisms": organisms,
    })


def health_effect_redirect(request, pk):
    query_set = get_object_or_404(HealthEffect.objects.prefetch_related("chemicals"), pk=pk)
    return redirect(reverse("chemical:health-effect", kwargs={"slug": query_set.slug}))


def health_effect(request, slug):
    query_set = get_object_or_404(HealthEffect.objects.prefetch_related("chemicals"), slug=slug)
    # paginator = Paginator(query_set.chemicalgeneinteraction_set.all(), per_page=25)
    # page = paginator.page(request.GET.get('page', 1))
    # top_interactions = query_set.chemicalgeneinteraction_set.all().annotate(
    #     total=Count('actions') + F('amount') -1).order_by('-total').values('gene__name', 'interaction', 'total')[:10]
    return render(request, "chemical/health_effect.html", {
        "query_set": query_set,
        # "page": page,
        # "top_interactions": top_interactions
    })


def organism(request, slug):
    query_set = get_object_or_404(Organism, slug=slug)
    chemicals = query_set.chemicalconcentration_set.filter(conc__gte=0.0, chemical__isnull=False).values("chemical__name", "chemical__slug", "conc_unit").annotate(max_conc=Max("conc")).order_by("-max_conc").all()
    return render(request, "chemical/organism.html", {"query_set": query_set, "chemicals": chemicals})


def preparation(request, slug):
    # query_set = get_object_or_404(Preparations, )
    return render(request, "chemical/preparation.html")


@require_GET
def chemicals_list_api(request):
    cat = SubstanceCategory.objects.filter(slug='obscure_chemicals')
    if request.GET.get('data[q]', ''):
        query = request.GET.get('data[q]')
        chemicals = Chemical.objects.filter(
            chemicalgeneinteraction__isnull=False,
            name__icontains=query
        ).exclude(categories=cat).annotate(text=F('name'), cnt=Count('id')).values('id', 'text')
    else:
        chemicals = Chemical.objects.all(
            chemicalgeneinteraction__isnull=False
        ).annotate(
            text=F('name'),
            cnt=Count('id')
        ).exclude(categories=cat).values('id', 'text')
        query = ''
    result = {
        'q': query,
        'results': [{'id': item['id'], 'text': item['text'].title()} for item in list(chemicals)]
    }
    return JsonResponse(result, safe=False)
