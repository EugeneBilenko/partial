from django.conf.urls import url

import fileapi.views

urlpatterns = [
    url(r'^sse/$', fileapi.views.Sse.as_view(), name="sse"),
    url(r'^file-download-process/(?P<job_id>[\w\-]+)/$', fileapi.views.file_download_process, name="file_download_process"),
    url(r'^upload/attempt/$', fileapi.views.upload_attempt, name="upload_attempt"),
    url(r'^upload/test_file_write/$', fileapi.views.test_file_write, name="test_file_write"),
    url(r'^upload/test_file_delete/$', fileapi.views.test_file_delete, name="test_file_delete"),

    url(r'^change_active_file/', fileapi.views.change_active_file, name="change_active_file"),
    url(r'^remove_file/', fileapi.views.remove_file, name="remove_file"),
    url(r'^rescan_file/', fileapi.views.rescan_file, name="rescan_file"),
    url(r'^download-genetic-reports/', fileapi.views.download_genetic_reports, name="download_genetic_reports"),
    url(r'^download-genetic-reports-count/', fileapi.views.download_genetic_reports_count, name="download_genetic_reports_count"),
    url(r'^process_uploaded_file/', fileapi.views.process_uploaded_file, name="process_uploaded_file"),
    url(r'^get_23andme_file/', fileapi.views.get_23andme_file, name="get_23andme_file"),
    url(r'^remove_all_users_files/(?P<user_id>\d+)/', fileapi.views.remove_all_users_files, name="remove_all_users_files"),
]
