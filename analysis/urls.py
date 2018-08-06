from django.conf.urls import url

from analysis.views import (
    personalized_health_report,
    personalized_health_pdf_report,
    create_system,
    delete_system,
    edit_system,
)
from .autocomplete_views import SymptomAutocomplete, SymptomsForeignAutocompleteView, symptoms_list_api

urlpatterns = [
    url('^personalized-health-report/$', personalized_health_report, name="personalized-health-report"),
    url('^personalized-health-pdf-report/$', personalized_health_pdf_report, name="personalized-health-pdf-report"),
    url('^create-system/$', create_system, name="create-system"),
    url('^delete-system/(?P<id>\d+)/$', delete_system, name="delete-system"),
    url('^edit-system/(?P<id>\d+)/$', edit_system, name="edit-system"),

    url(r'^autocomplete/symptoms/$', SymptomAutocomplete.as_view(), name="autocomplete-symptoms"),
    url(r'^symptoms-foreign-autocomplete/$', SymptomsForeignAutocompleteView.as_view(), name="autocomplete-symptoms-foreign"),
    url(r'^symptoms-list-api/$', symptoms_list_api, name="symptoms-list-api"),
]
