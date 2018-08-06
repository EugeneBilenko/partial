from api import views
from django.conf.urls import url

from rest_framework import routers


router = routers.SimpleRouter()

router.register(r'chemical', views.ChemicalView, "chemical")
router.register(r'gene', views.GeneView, "gene")
router.register(r'report', views.PdfGenerateView, "report")

urlpatterns = router.urls

urlpatterns += [
    url(r'^userprofilesymptoms/$', views.UserProfileSymptomView.as_view(), name='userprofilesymptoms-update'),
    url(r'^userprofileconditions/$', views.UserProfileConditionView.as_view(), name='userprofileconditions-update'),
    url(r'^customsymptoms/$', views.CustomSymptomSeverityView.as_view(), name='customsymptoms-update'),
    url(r'^customconditions/$', views.CustomConditionSeverityView.as_view(), name='customconditions-update'),
    url(r'^userprofile/$', views.UserProfileView.as_view(), name='userprofile'),
]

# print(urlpatterns)
