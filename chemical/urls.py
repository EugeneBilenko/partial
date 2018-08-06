from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect

from chemical import ajax_views
from chemical import views
from chemical.views import *

urlpatterns = [
    url(
        r'^admin/organism-autocomplete/$',
        OrganismAutocomplete.as_view(),
        name='organism-autocomplete',
    ),
    url(
        r'^admin/preparation-autocomplete/$',
        PreparationAutocomplete.as_view(),
        name='preparation-autocomplete',
    ),
    url(
        r'^admin/category-autocomplete/$',
        CategoryAutocomplete.as_view(),
        name='category-autocomplete',
    ),
    url(
        r'^admin/gene-autocomplete/$',
        GeneAutocomplete.as_view(),
        name='gene-autocomplete',
    ),
    url(
        r'^admin/chemical-autocomplete/$',
        ChemicalAutocomplete.as_view(),
        name='chemical-autocomplete',
    ),
    url(
        r'^admin/interaction-autocomplete/$',
        InteractionAutocomplete.as_view(),
        name='interaction-autocomplete',
    ),
    url(
        r'^admin/interaction-type-autocomplete/$',
        InteractionTypeAutocomplete.as_view(),
        name='interaction-type-autocomplete',
    ),
    url(
        r'^admin/health-effect-autocomplete/$',
        HealthEffectAutocomplete.as_view(),
        name='health-effect-autocomplete',
    ),
    url(r'^chemical-disease-ajax/(?P<chemical>([A-Za-z0-9_-]+))/',
        ajax_views.chemical_disease_ajax,
        name="chemical-disease-ajax"),
    # url(r'^chemical-gene-ajax/(?P<chemical>([A-Za-z0-9_-]+))/',
    #     ajax_views.chemical_gene_ajax,
    #     name="chemical-gene-ajax"),
    # url(r'^chemical-pathway-ajax/(?P<chemical>([A-Za-z0-9_-]+))/',
    #     ajax_views.chemical_pathway_ajax,
    #     name="chemical-pathway-ajax"),
    url(r'^chemical/(?P<chemical>([A-Za-z0-9_-]+))/',
        views.chemical,
        name="chemical"),
    url(r'^health-effect/(?P<pk>[0-9]+)/$',
            views.health_effect_redirect,
            name="health-effect-redirect"),
    url(r'^health-effect/(?P<slug>[a-zA-Z0-9-_]+)/$',
        views.health_effect,
        name="health-effect"),
    url(r'^organism/(?P<slug>[a-zA-Z0-9-_]+)/$',
        views.organism,
        name="organism"),
    url(r'^preparation/(?P<slug>[a-zA-Z0-9-_]+)/$',
        views.preparation,
        name="preparation"),
    url(r'^chemicals-list-api/$', views.chemicals_list_api, name="chemicals-list-api"),

]
