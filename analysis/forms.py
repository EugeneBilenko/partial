from dal import autocomplete
from django import forms

from analysis.models import System, Symptom, CustomUserSymptom
from chemical.models import Chemical, HealthEffect
from experiment.models import Identification
from genome.models import Gene, Snp, DiseaseTrait


class SystemAdminForm(forms.ModelForm):
    class Meta:
        model = System
        fields = '__all__'
        widgets = {
            "genes": autocomplete.ModelSelect2Multiple(url="genome_gene_autocomplete"),
            'chemicals': autocomplete.ModelSelect2Multiple(url='chemical:chemical-autocomplete'),
            'threshold_symptoms': autocomplete.ModelSelect2Multiple(url='analysis:autocomplete-symptoms'),
        }


class SymptomAdminInlineForm(forms.ModelForm):
    class Meta:
        model = Symptom
        fields = '__all__'
        widgets = {
            'symptom': autocomplete.Select2(),
        }


class ForeignObjectForm(autocomplete.FutureModelForm):
    related_objects = autocomplete.GenericM2MQuerySetSequenceField(
        queryset=autocomplete.QuerySetSequence(
            Gene.objects.all(),
            Chemical.objects.exclude(categories__id=51).all(),
            DiseaseTrait.objects.all(),
            Snp.objects.all(),
            HealthEffect.objects.all(),
            Identification.objects.all(),
        ),
        required=False,
        widget=autocomplete.QuerySetSequenceSelect2Multiple(
            url='analysis:autocomplete-symptoms-foreign',
        ),
    )

    class Meta:
        model = Symptom
        fields = ('name', 'related_objects', 'selfhacked_link')


class CreateSystemForm(forms.ModelForm):

    class Meta:
        model = System
        fields = [
            'name',
            'short_name',
            'threshold',
            'description',
            'threshold_description',
            'genes',
            'chemicals',
        ]
