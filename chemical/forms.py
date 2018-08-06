from django import forms
from dal import autocomplete
from chemical.models import *


class ChemicalGeneInteractionForm(forms.ModelForm):
    class Meta:
        model = ChemicalGeneInteraction
        fields = ('__all__')
        exclude = ("pub_med_ids",)
        widgets = {
            'gene': autocomplete.ModelSelect2(url='chemical:gene-autocomplete'),
            'chemical': autocomplete.ModelSelect2(url='chemical:chemical-autocomplete'),
            'organism': autocomplete.ModelSelect2(url='chemical:organism-autocomplete'),
        }


class ChemicalGeneInteractionActionForm(forms.ModelForm):
    class Meta:
        model = ChemicalGeneInteractionAction
        fields = ('__all__')
        widgets = {
            'interaction': autocomplete.ModelSelect2(url='chemical:interaction-autocomplete'),
            'interaction_type': autocomplete.ModelSelect2(url='chemical:interaction-type-autocomplete'),
            'action': autocomplete.Select2()
        }


class ChemicalForm(forms.ModelForm):
    class Meta:
        model = Chemical
        fields = ('__all__')
        widgets = {
            # 'categories': autocomplete.ModelSelect2Multiple(url='chemical:category-autocomplete'),
            'health_effects': autocomplete.ModelSelect2Multiple(url='chemical:health-effect-autocomplete'),
            'drug_bank_ids': forms.TextInput(attrs={'class': 'vTextField'}),
            'hmdb_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'pubchem_Compound_ID': forms.TextInput(attrs={'class': 'vTextField'}),
            'chembl_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'chem_spider_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'kegg_compound_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'uni_prot_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'omim_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'chebi_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'bio_cyc_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'ctd_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'stitch_di': forms.TextInput(attrs={'class': 'vTextField'}),
            'pdb_id': forms.TextInput(attrs={'class': 'vTextField'}),
            'actor_id': forms.TextInput(attrs={'class': 'vTextField'}),
        }


class ChemicalTargetMechanismForm(forms.ModelForm):
    class Meta:
        model = ChemicalTargetMechanism
        fields = ("__all__")


class ChemicalConcentrationAdminForm(forms.ModelForm):
    class Meta:
        model = ChemicalConcentration
        fields = "__all__"
        exclude = ("chemical",)
        widgets = {
            'preparation': autocomplete.ModelSelect2(url='chemical:preparation-autocomplete'),
            # 'chemical': autocomplete.ModelSelect2Multiple(url='chemical:chemical-autocomplete'),
            'organism': autocomplete.ModelSelect2(url='chemical:organism-autocomplete'),
        }


class ChemicalPathwayForm(forms.ModelForm):
    class Meta:
        model = ChemicalConcentration
        fields = "__all__"
        widgets = {
            'chemical': autocomplete.ModelSelect2(url='chemical:chemical-autocomplete'),
            'related_pathway': autocomplete.ModelSelect2(url='pathway_autocomplete'),
        }