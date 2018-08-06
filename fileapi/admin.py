import boto3
import os

from botocore.exceptions import ClientError
from django.contrib import admin

# Register your models here.
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import csrf_protect_m
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction, router
from django.http import Http404
from django.template.defaultfilters import filesizeformat
from django.utils.encoding import force_text
from django.utils.html import escape

from decodify import settings
from fileapi.api23andme import Api23AndMe
from fileapi.forms import FileFormAdmin
from fileapi.models import UploadAttempt, ReportsFiles
from genome.models import File
from django.utils.safestring import mark_safe
from django.utils.translation import string_concat, ugettext as _, ungettext


@admin.register(UploadAttempt)
class UploadAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "uploaded",)
    search_fields = ("user__email", "user__username",)
    readonly_fields = ("user", "created_at", "message",)
    fields = ("user", "message", "created_at",)
    ordering = ("-created_at",)

    def uploaded(self, inst):
        return inst.created_at.strftime("%c %Z")

    def has_add_permission(self, request):
        return False


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    form = FileFormAdmin
    list_display = ('id', 'file_name', 'original_name', 'provider', 'service', 'rescan_available', 'user_email', 'status', 'progress_c', 'created_at')
    list_filter = ("status", 'provider', 'service', 'rescan_available',)
    readonly_fields = ('id', 'download_link', 'get_file_size')
    search_fields = ('user__email',)
    actions = ['delete_model']
    delete_confirmation_template = 'fileapi/delete_confirmation.html'
    delete_confirmation_template = 'fileapi/delete_confirmation.html'
    delete_selected_confirmation_template = 'fileapi/delete_confirmation.html'

    def user_email(self, inst):
        return inst.user.email

    def progress_c(self, inst):
        return "%.2f%%" % inst.progress

    def _init_credentials(self):
        os.environ['S3_USE_SIGV4'] = 's3v4'
        os.environ["AWS_ACCESS_KEY_ID"] = settings.AWS_ACCESS_KEY_ID
        os.environ["AWS_SECRET_ACCESS_KEY"] = settings.AWS_SECRET_ACCESS_KEY

    def download_link(self, inst):
        link = '-'
        if inst.provider == File.PROVIDER_DIRECT_UPLOAD:
            self._init_credentials()
            s3_client = boto3.client('s3')
            response = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.S3_BUCKET, 'Key': str(inst.original_name)},
                ExpiresIn=100
            )
            link = '<a href="{}">Download file</a>'.format(response)
        elif inst.provider == File.PROVIDER_23ANDME_API:
            api = Api23AndMe()
            user_23andme_api = api.get_user(inst.user.user_profile.access_token)
            try:
                user_23andme_profile_id = user_23andme_api.get('profiles')[0].get('id')
                link = '<a href="{}?access_token={}&profile_id={}&filename={}">Download file</a>'.format(
                    reverse("fileapi:get_23andme_file"),
                    inst.user.user_profile.access_token,
                    user_23andme_profile_id,
                    inst.file_name
                )
            except:
                link = '-'
        return mark_safe(link)

    def get_file_size(self, inst):
        result = '-'
        if inst.provider == File.PROVIDER_DIRECT_UPLOAD:
            self._init_credentials()
            s3_client = boto3.resource('s3')
            obj = s3_client.ObjectSummary(settings.S3_BUCKET, str(inst.original_name))
            try:
                size = obj.size
                result = filesizeformat(size)
            except ClientError:
                result = '-'
        elif inst.provider == File.PROVIDER_23ANDME_API:
            result = '2.3MB'
        return result

    def delete_model(self, request, inst):
        file_uploads = inst.user.user_profile.file_uploads_count
        if file_uploads > 0:
            inst.user.user_profile.file_uploads_count = file_uploads - 1
            inst.user.user_profile.save()
        inst.delete()

    @csrf_protect_m
    @transaction.atomic
    def delete_view(self, request, object_id, extra_context=None):
        "The 'delete' admin view for this model."
        IS_POPUP_VAR = '_popup'
        opts = self.model._meta
        app_label = opts.app_label

        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)

        obj = self.get_object(request, unquote(object_id), to_field)

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(
                _('%(name)s object with primary key %(key)r does not exist.') %
                {'name': force_text(opts.verbose_name), 'key': escape(object_id)}
            )

        using = router.db_for_write(self.model)

        if request.POST:  # The user has already confirmed the deletion.
            if False:
                raise PermissionDenied
            obj_display = force_text(obj)
            attr = str(to_field) if to_field else opts.pk.attname
            obj_id = obj.serializable_value(attr)
            self.log_deletion(request, obj, obj_display)
            self.delete_model(request, obj)

            return self.response_delete(request, obj_display, obj_id)

        object_name = force_text(opts.verbose_name)

        title = _("Are you sure?")

        context = dict(
            self.admin_site.each_context(request),
            title=title,
            object_name=object_name,
            object=obj,
            opts=opts,
            app_label=app_label,
            preserved_filters=self.get_preserved_filters(request),
            is_popup=(IS_POPUP_VAR in request.POST or
                      IS_POPUP_VAR in request.GET),
            to_field=to_field,
        )
        context.update(extra_context or {})

        return self.render_delete_form(request, context)

    progress_c.short_description = "Progress"
    download_link.short_description = "Download Link"
    get_file_size.short_description = "File Size"
    delete_model.short_description = ""


@admin.register(ReportsFiles)
class ReportsFilesAdmin(admin.ModelAdmin):
    list_display = ("user", "report_url", "status")
