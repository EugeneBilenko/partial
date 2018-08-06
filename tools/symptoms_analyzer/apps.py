from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SymptomsAnalyzerConfig(AppConfig):
    name = 'tools.symptoms_analyzer'
    verbose_name = _('Symptoms and Conditions Analyzer')
