from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^api/plant-food-recommendations/(?P<pk>\d+)/$', views.index, name="main")
]
