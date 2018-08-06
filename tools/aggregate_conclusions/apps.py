from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AggregateConclusionsConfig(AppConfig):
    name = 'tools.aggregate_conclusions'
    verbose_name = _('Trait Aggregation Score')
