import os.path

import json
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q, F
from django.http import HttpResponse, JsonResponse, HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from django.views.generic import View

from decodify.decorators import disallow_demouser
from fileapi import tasks
from fileapi.models import UploadAttempt, ReportsFiles
from fileapi.constants import REPORT_TYPES
from genome.decorators import subscription_required, uploaded_file_required
from genome.models import File, GeneticReports
from genome.repositories import UserRepository
from payment.helpers import get_addon_price
from payment.models import Subscription, Plan
from fileapi.api23andme import Api23AndMe
from genome.helpers import get_report_pagination
from django.contrib.auth.models import User

from celery.result import AsyncResult



@login_required
@disallow_demouser
@subscription_required(redirect_url="/checkout")
def uploader(request):
    subscription = Subscription.get_active(request.user)
    user_plan = None
    extra_price = None
    extra_files_count = None
    plans_qs = Plan.objects.order_by("price")
    if subscription:
        user_plan = subscription.plan
        extra_price = get_addon_price(user_plan) / 100
        extra_files_count = subscription.plan.max_file_uploads
        plans_qs = plans_qs.exclude(pk=user_plan.pk)

    return render(request, "genome/uploader.html", {
        'X23ANDME_CLIENT_ID': settings.X23ANDME_CLIENT_ID,
        'user_plan': user_plan,
        'extra_price': extra_price,
        'extra_files_count': extra_files_count,
        'plans': plans_qs.all(),
        "STRIPE_API_KEY": settings.STRIPE_PUBLIC_KEY,
    })


@require_POST
@login_required
@disallow_demouser
def change_active_file(request):
    file = get_object_or_404(File, user=request.user, pk=request.POST.get("file_id"))
    request.user.user_profile.active_file = file
    request.user.user_profile.save()
    return redirect("%s#section-my-files" % reverse("dashboard"))


@require_POST
@login_required
@disallow_demouser
def rescan_file(request):
    file = get_object_or_404(
        File,
        Q(status=File.FILE_STATUS_COMPLETED) | Q(status=File.FILE_STATUS_UPLOADED) | Q(status=File.FILE_STATUS_ERROR),
        user=request.user,
        pk=request.POST.get("file_id"),
        rescan_available=True
    )
    file.progress = 0
    file.status = File.FILE_STATUS_QUEUED
    file.status_message = None
    file.agg_data_available = 0
    file.last_rescan_at = timezone.now()
    file.save()

    dashboard_uri = request.build_absolute_uri("/dashboard")

    if file.provider == File.PROVIDER_DIRECT_UPLOAD:
        tasks.process_genome_file.delay(request.user.pk, dashboard_uri, file.pk, is_rescan=True)
    elif file.provider == File.PROVIDER_23ANDME_API:
        tasks.upload_23andme.delay(request.user.pk, code=None, file_pk=file.pk, is_rescan=True)

    return redirect("%s#section-my-files" % reverse("dashboard"))


class Sse(View):
    def get_status(self):
        user = self.request.user

        if self.request.GET.getlist('files[]'):
            qs = user.file_set.filter(pk__in=self.request.GET.getlist('files[]'))
        else:
            qs = user.file_set.filter(Q(status=File.FILE_STATUS_PROCESSING) | Q(status=File.FILE_STATUS_QUEUED))
        processed_files = qs.all()
        files_ids = [o.pk for o in processed_files]
        files = user.file_set.filter(
            Q(status=File.FILE_STATUS_PROCESSING)
            | Q(status=File.FILE_STATUS_QUEUED)
            | Q(status=File.FILE_STATUS_COMPLETED)
            | Q(status=File.FILE_STATUS_ERROR)
        ).filter(pk__in=files_ids)

        return self.send_message("file-progress", [
            {
                "file_id": file.pk,
                "progress": "%.0f" % file.progress,
                "status": file.status,
                "status_display": file.get_status_display(),
            } for file in files
        ])

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        response = HttpResponse(self.get_status())
        return response

    def send_message(self, event, data):
        if isinstance(data, (dict, list,)):
            data = json.dumps(data)
        return """{"event": "%s", "data": %s}""" % (event, data,)


@login_required
@require_POST
@disallow_demouser
@csrf_exempt
def upload_attempt(request):
    useragent = request.META.get("HTTP_USER_AGENT")
    error_message = request.POST.get("error_message")
    action = request.POST.get("action")
    filename = request.POST.get("filename")
    message = request.POST.get("message")

    data = ""
    if useragent:
        data += "UserAgent: %s\n" % useragent
    if error_message:
        data += "ErrorMessage: %s\n" % error_message
    if action:
        data += "ActionButton: %s\n" % action
    if filename:
        data += "Filename: %s\n" % filename
    if message:
        data += "Message: %s\n" % message

    UploadAttempt.objects.create(
        user=request.user,
        message=data
    )
    return HttpResponse()


@login_required
@disallow_demouser
def uploader_23andme(request):
    if request.user.user_profile.is_file_uploads_quota_exceeded:
        raise PermissionError("File upload quota exceeded")
    code = request.GET.get("code")
    file = File.objects.create(
        file_name="23andMe_Connect_" + str(request.user.email),
        user=request.user,
        status=File.FILE_STATUS_QUEUED,
        provider=File.PROVIDER_23ANDME_API,
        service=File.SERVICE_23ANDME,
        rescan_available=True
    )
    if code:
        tasks.upload_23andme.delay(request.user.id, code, file.pk)
    else:
        tasks.upload_23andme.delay(request.user.pk, code=None, file_pk=file.pk)
    return redirect("%s#section-my-files" % reverse("dashboard"))


def _create_file(request):
    file = File.objects.filter(
        status=File.FILE_STATUS_QUEUED,
        file_name=request.GET["file_name"],
        user=request.user
    ).first()
    if file is None:
        full_name = request.GET["file_name"]
        filename, extension = os.path.splitext(full_name)
        file = File.objects.create(
            file_name=filename,
            original_name=full_name,
            hashed_name=full_name,
            user=request.user,
            status=File.FILE_STATUS_QUEUED,
            provider=File.PROVIDER_DIRECT_UPLOAD,
            rescan_available=True
        )
    request.user.user_profile.active_file = file
    request.user.user_profile.save()
    return file


@login_required
@disallow_demouser
@subscription_required()
@csrf_exempt
def process_uploaded_file(request):
    if request.user.user_profile.is_file_uploads_quota_exceeded:
        raise PermissionError("File upload quota exceeded")
    dashboard_uri = request.build_absolute_uri(reverse("dashboard"))
    file = _create_file(request)

    tasks.process_genome_file.delay(request.user.id, dashboard_uri, file.pk)

    return redirect("%s#section-my-files" % reverse("dashboard"))


@login_required
@disallow_demouser
def remove_file(request):
    file = get_object_or_404(File, user=request.user, pk=request.POST.get("file_id"))
    file.deleted_at = timezone.now()
    file.save()

    tasks.delete_uploaded_file.delay(request.user.pk, file.pk)

    return redirect("%s#section-my-files" % reverse("dashboard"))


static_dir = 'static/'


def test_file_write(request):
    filename = 'test.txt'
    context = "this is test contest for file"
    f = open(static_dir + filename, "w")
    f.write(context)
    f.close()
    return HttpResponse({"success": True})


def test_file_delete(request):
    filename = 'test.txt'
    os.remove(static_dir + filename)
    return HttpResponse({"success": True})


@login_required
@disallow_demouser
def get_23andme_file(request):
    api = Api23AndMe()
    access_token = request.GET.get('access_token')
    profile_id = request.GET.get('profile_id')
    filename = request.GET.get('filename', '23_andme_data')
    response = HttpResponse(content_type='application/octet-stream')
    response['Content-Disposition'] = 'filename="{}.txt"'.format(filename)
    if profile_id and access_token:
        genome = api.get_genomes(access_token, profile_id)
        response.write(genome.get('genome'))
    else:
        response.write('')
    return response


@login_required
@disallow_demouser
def remove_all_users_files(request, user_id: int):
    print('Starting to delete all files...')
    user = get_object_or_404(User, pk=user_id)
    user_repository = UserRepository(user)
    all_files = user_repository.get_all_files()

    for file in all_files:
        file.deleted_at = timezone.now()
        file.save()
        tasks.delete_uploaded_file.delay(user_id, file.pk)
    print('All files of user {} scheduled to be deleted  ...'.format(user.username))
    return redirect(reverse('admin:auth_user_changelist'))


@login_required
def get_report_pdf_snps_creator(request):
    if request.method == "POST":
        report_state = request.POST.get("report_state", "snps_to_look_at")
        reports_files = ReportsFiles.objects.create(
            user=request.user,
            status="pending"
        )
        
        job = tasks.gene_report_pdf_creator.delay(report_state, request.get_host(), request.user.id, reports_files.id)
    
        return HttpResponseRedirect(reverse('dashboard') + '?job_id' + '=' + job.id)

    return render(request, "genome/reports/select_reports_state.html", {})


@uploaded_file_required(redirect_url="/uploader")
def get_report_pdf_page(request):
    serialized = {
        'per_page': get_report_pagination(request),
        'pages': int(request.GET.get("pages")),
        'report_state': request.GET.get("report"),
        'disease_name': request.GET.get("disease"),
        'active_file_id': request.user.user_profile.active_file_id,
        'search_object': request.GET.get("search_object"),
        'query': request.GET.get("query"),
        'user_id': request.user.id,
        'sort_by': request.GET.get("sort_by"),
        'has_description': request.GET.get("has_description"),
        'sbmt': request.GET.get("sbmt"),
        'entity_pk': request.GET.get('entity_pk'),
        'page': request.GET.get("page"),
    }

    tasks.prepare_report_file.delay(json.dumps(serialized))

    return JsonResponse({
        'status': 'sent'
    })


@login_required
@csrf_exempt
def get_genetic_reports(request):
    user = request.user
    if request.method == 'POST':
        response = {'status': False}
        file_id = request.POST.get('file_id', '')
        report_type = request.POST.get('report_type', '')
        report_name = request.POST.get('report_name', '')

        if user.user_profile.has_subscription() and \
            user.user_profile.free_reports_available and \
            user.file_set.filter(id=file_id).exists() and \
            report_type in REPORT_TYPES:
            if user.user_genetic_reports.filter(file__id=file_id, report_type=report_type):
                response['is_already_exist'] = True
            else:
                file = File.objects.get(id=file_id)
                genetic_report = GeneticReports.objects.create(
                    file=file,
                    user=user,
                    report_type=report_type
                )
                job = tasks.gene_report_pdf_snps.delay(
                    user.id,
                    file_id,
                    host_path=request.get_host(),
                    report_type=report_type,
                    report_name=report_name,
                    genetic_report_id=genetic_report.id
                )
                response['data'] = {
                    'file_name': file.file_name,
                    'genetic_report_id': genetic_report.id,
                    'created': genetic_report.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    'job_id': job.id,
                    'free_reports_left': user.user_profile.free_reports_available
                }

            response['status'] = True
        return HttpResponse(json.dumps(response), content_type='application/json')

    introductory_reports = user.user_genetic_reports.filter(
        report_type='introductory'
    ).order_by("-created_at")
    cardio_reports = user.user_genetic_reports.filter(
        report_type='cardio'
    ).order_by("-created_at")
    inflammation_reports = user.user_genetic_reports.filter(
        report_type='inflammation'
    ).order_by("-created_at")

    user_files = user.file_set.filter(
        deleted_at__isnull=True
    ).order_by("-created_at")

    context = {
        'user_files': user_files,
        'introductory_reports': introductory_reports,
        'cardio_reports': cardio_reports,
        'inflammation_reports': inflammation_reports
    }

    return render(request, 'genome/genetic_reports.html', context)


@login_required
def download_genetic_reports(request):
    data = {'status': False}
    if request.is_ajax():
        report_type = request.GET.get('report_type', '')
        genetic_reports = request.user.user_genetic_reports.filter(
            report_type=report_type
        ).order_by('-created_at')
        template = render_to_string(
            "fileapi/downloadable_report_files.html",
            {'genetic_reports': genetic_reports, 'report_type': report_type}
        )
        data['get_dwnld_table'] = template
        data['status'] = True

    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required
def file_download_process(request, job_id):
    job = AsyncResult(job_id)
    data = job.result or job.state
    return HttpResponse(json.dumps(data), content_type='application/json')


@login_required
def download_genetic_reports_count(request):
    response = {'status': False}
    genetic_reports_id = request.GET.get('report_id', '')
    if request.user.user_genetic_reports.filter(id=genetic_reports_id).exists():
        request.user.user_genetic_reports.filter(
            id=genetic_reports_id
        ).update(
            file_download_count=F('file_download_count')+1
        )

        response['url'] = request.user.user_genetic_reports.get(
            id=genetic_reports_id
        ).get_signed_url()
        response['status'] = True
    return HttpResponse(json.dumps(response), content_type='application/json')
