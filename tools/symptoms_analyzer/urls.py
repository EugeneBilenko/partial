from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^symptoms-condition-analyzer/$', views.index, name="main"),
    url(r'^api/update-search-data-files/$', views.update_search_data, name="update_search_data"),
    url(r'^api/sca-search/$', views.SCAViewSet.as_view({'get': 'list'}))
]
