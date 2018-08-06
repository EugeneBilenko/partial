from dal import autocomplete
from django.db.models import F
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from dal_select2_queryset_sequence.views import Select2QuerySetSequenceView
from queryset_sequence import QuerySetSequence

from analysis.models import Symptom
from chemical.models import Chemical, HealthEffect
from experiment.models import Identification
from genome.models import Gene, DiseaseTrait, Snp


class SymptomAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Symptom.objects.none()

        qs = Symptom.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class SymptomsForeignAutocompleteView(Select2QuerySetSequenceView):
    paginate_by = 60

    def get_queryset(self):
        genes = Gene.objects.all()
        chemicals = Chemical.objects.exclude(categories__id=51).all()
        diseases = DiseaseTrait.objects.all()
        snps = Snp.objects.all()
        healtheffects = HealthEffect.objects.all()
        experiments = Identification.objects.all()

        if self.q:
            genes = genes.filter(name__icontains=self.q)
            chemicals = chemicals.filter(name__icontains=self.q)
            diseases = diseases.filter(name__icontains=self.q)
            snps = snps.filter(rsid__icontains=self.q)
            healtheffects = healtheffects.filter(name__icontains=self.q)
            experiments = experiments.filter(name__icontains=self.q)

        qs = QuerySetSequence(genes, chemicals, diseases, snps, healtheffects, experiments)
        qs = self.mixup_querysets(qs)
        return qs


@require_GET
def symptoms_list_api(request):
    if request.GET.get('data[q]', ''):
        query = request.GET.get('data[q]')
        symptoms = Symptom.objects.filter(name__icontains=query).annotate(text=F('name')).values('id', 'text')
    else:
        symptoms = []
        query = ''
    result = {
        'q': query,
        'results': [{'id': item['id'], 'text': item['text'].title()} for item in list(symptoms)]
    }
    return JsonResponse(result, safe=False)
