from django.conf.urls import url
from rest_framework import routers

from . import views

router = routers.SimpleRouter()

urlpatterns = [
    url(r'^aggregate-conclusions/$', views.get_genome_conclusions, name="main"),
    url(r'^api/trait-matches-parent/$', views.TraitMatchesParentViewSet.as_view({'get': 'list'})),
    url(r'^api/check-current-file-tm-state/$', views.check_current_file_state),
    url(r'^api/trait-matches/$', views.TraitMarchesView.as_view({'get': 'list'})),
    url(r'^api/trait-matches/(?P<pk>\d+)/$', views.TraitDetailsView.as_view({'get': 'retrieve'})),
]

urlpatterns += router.urls
