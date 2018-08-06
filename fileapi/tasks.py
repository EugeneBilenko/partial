import gzip
import traceback
from io import StringIO

import zipfile
import json
import pdfkit
import boto3
import tempfile

import linecache
import magic
import numpy
import pandas as pd
import sys

from datetime import timedelta
from datetime import datetime

import shutil
import vcf
from django.core.mail import send_mail
from django.utils import timezone
from django_pandas.io import read_frame
from django.template.loader import get_template
from itertools import islice
from django.core import serializers
from django.http import FileResponse, HttpRequest
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMessage

from genome.models import Snp, File, UserProfile, Gene, UserRsid, UserGeneReputation, GeneticReports
from fileapi.api23andme import Api23AndMe
from genome.tasks import *
from fileapi.helpers import *
from genome.reports import _snps_has_info, _get_snps_genes
from genome.helpers import ResultObject
from fileapi.models import ReportsFiles

from genome.reports import get_introductory_report_pdf_snps_data, get_cardiovascular_report_pdf_snps_data, \
                            get_inflammatory_report_pdf_snps_data

def get_uncompressed_file_name(file_name):
    return "%s.uncompressed" % file_name


def get_s3_data_to_file(file_name):
    static_dir = 'staticfiles/'
    os.environ['S3_USE_SIGV4'] = S3_USE_SIGV4
    os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
    s3_client = boto3.client('s3')
    s3_client.download_file(settings.S3_BUCKET, str(file_name), static_dir + file_name)
    return static_dir + file_name


def check_genotype_style(genotype, snp):
    genotype = genotype.strip()
    if len(genotype) > 1 and genotype[0] != genotype[1]:
        return "heterozygous"
    elif len(genotype) > 1 and (genotype[0] == genotype[1]) and genotype[0] == snp.minor_allele:
        return "homozygous_minor"
    elif len(genotype) > 1 and (genotype[0] == genotype[1]) and genotype[0] != snp.minor_allele:
        return "homozygous_major"
    elif len(genotype) == 1 and genotype[0] != snp.minor_allele:
        return "hemizygous_major"
    elif len(genotype) == 1 and genotype[0] == snp.minor_allele:
        return "hemizygous_minor"
    elif genotype == 'II':
        return "double_insertion"
    elif genotype == 'DD':
        return "double_deletion"
    elif genotype == 'I':
        return "insertion"
    elif genotype == 'D':
        return "deletion"
    elif genotype == '--' or genotype == '-' or genotype == 'NC' or genotype == "":
        return "unknown"


# Unzip .gz and return io.StringIO object
def unzip_xgz(file_name='', *args, **kwargs):

    with gzip.open(file_name, 'rb') as f_in:
        with open(get_uncompressed_file_name(file_name), 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    return get_uncompressed_file_name(file_name)


def unzip_gz(*args, **kwargs):
    gfile = gzip.GzipFile(*args, **kwargs)
    zipped_buffer = StringIO()

    # Read gzipped file by chuncks until it finished with exception...
    try:
        while True:
            zipped_buffer.write(gfile.read1().decode('utf-8'))
    except OSError:
        pass

    zipped_buffer.seek(0)

    return zipped_buffer


# Unzip zipped file and return archive, unzipped file and name of unzipped file
def unzip_zip(file_name=''):
    archive = zipfile.ZipFile(file_name, 'r')
    name = archive.namelist()[0]
    file = archive.open(name)
    with open(get_uncompressed_file_name(file_name), 'wb') as f_out:
        f_out.write(file.read())
        f_out.close()
    return archive, get_uncompressed_file_name(file_name), name


def unzip_any_file(archive_file_name):
    mime_type = magic.from_file(archive_file_name, mime=True)
    print("Mime type: %s" % mime_type)
    if mime_type == 'application/gzip':
        file = unzip_xgz(file_name=archive_file_name)
        archive = None
        file_name = None
    elif mime_type == 'application/x-gzip':
        file = unzip_xgz(file_name=archive_file_name)
        archive = None
        file_name = None
    elif mime_type == 'application/zip':
        archive, file, file_name = unzip_zip(archive_file_name)
    elif mime_type == 'text/plain':
        file = archive_file_name
        archive = None
        file_name = None
    else:
        raise Exception("Cannot unzip file with mime type: %s" % mime_type)
    return archive, file, file_name


def send_completed_email(dashboard_uri, user, file):
    msg_body = render_to_string('fileapi/file_success_msg.html', {
        'user': user.username,
        'filename': file.file_name,
        'dashboard': dashboard_uri
    })
    send_mail("Your analysis is ready", msg_body, settings.EMAIL_FROM, [user.email], html_message=msg_body)


def handle_errors(file):
    e_t, e_o, tb = sys.exc_info()
    f = tb.tb_frame
    line = linecache.getline(f.f_code.co_filename, tb.tb_lineno, f.f_globals)
    file.status = File.FILE_STATUS_ERROR
    file.status_message = "Error line: %s (%s: %s): '%s'" % (tb.tb_lineno, e_t, e_o, line.strip(),)
    file.save()
    traceback.print_exc()
    print(file.status_message)


def get_results(user_rsid, snp, file):
    zygosities = {
        'heterozygous': ('Heterozygous', '+/-', 'O',),
        'homozygous_major': ('Homozygous Major', '-/-', 'G',),
        'homozygous_minor': ('Homozygous Minor', '+/+', 'B',),
        'hemizygous_major': ('Hemizygous Major', '-', 'G',),
        'hemizygous_minor': ('Hemizygous Minor', '+', 'B',),
        'unknown': ('Unknown', '?/?', 'U',),
        'double_insertion': ('Double Insertion', 'I/I', 'O',),
        'double_deletion': ('Double Deletion', 'D/D', 'O',),
        'insertion': ('Single Insertion', 'I', 'O',),
        'deletion': ('Single Deletion', 'D', 'O',),
    }
    genotype_style_falls = {
        "heterozygous": "heterozygous_color",
        "insertion": "heterozygous_color",
        "deletion": "heterozygous_color",
        "double_insertion": "heterozygous_color",
        "double_deletion": "heterozygous_color",

        "homozygous_minor": "homozygous_minor_color",
        "hemizygous_minor": "homozygous_minor_color",
        "minor": "homozygous_minor_color",

        "homozygous_major": "homozygous_major_color",
        "hemizygous_major": "homozygous_major_color",
        "major": "homozygous_major_color",
    }
    colors = {
        'green': ('G', 'Good', 'success',),
        'yellow': ('O', 'Okay', 'warning',),
        'red': ('B', 'Bad', 'danger',),
        'gray': ('U', 'Unknown', 'default',),
    }
    color_field = genotype_style_falls[user_rsid.genotype_style]
    color = getattr(snp, color_field, "").strip()
    if color:
        reputation = colors.get(color)[0]
    else:
        reputation = zygosities.get(user_rsid.genotype_style)[2]
    return (
        reputation,
        user_rsid.genotype_style,
    )


def calculate_total_reputation(file):
    # MULTIPLIER - If reputation of the genotype is good (G), multiplier is 0,
    # if reputation is slightly bad, multiplier is 0.5, if reputation is bad (R), multiplier is 1
    mul = {
        "G": 0,
        "U": 0,
        "O": 0.5,
        "B": 1,
    }

    # The multipliers for all the different zygosities, i.e.heterozygous (one bad allele)
    # multiplies the score by 1, homozygous minor (two bad alleles) multiplies the score by 1.5
    z_mul = {
        'heterozygous': 1.2,
        'homozygous_major': 1,
        'major': 1,
        'homozygous_minor': 1.5,
        'minor': 1.5,
        'hemizygous_major': 1,
        'hemizygous_minor': 1.3,
        'unknown': 1,
        'double_insertion': 1.3,
        'double_deletion': 1.3,
        'insertion': 1.2,
        'deletion': 1.2,
    }

    # Spread amplifies the score, the higher the spread, the greater the score difference will be
    spread = 1.3

    print("Calculate genes reputation")
    rsids = file.related_rsid.values_list("rsid", flat=True).distinct()
    genes = Gene.objects.filter(snps__rsid__in=rsids).distinct().all()
    genes_count = genes.count()
    file.set_total_points(genes_count, latency=200)
    for gene in genes:
        total_reputation = 0
        for snp in gene.snps.all():
            user_rsid = file.related_rsid.filter(rsid=snp.rsid).first()
            if user_rsid is None:
                continue

            rep, zygosity = get_results(user_rsid, snp, file)

            if not rep or rep == "G" or rep == "U":
                continue

            importance = snp.importance

            weighted_reputation = importance * mul[rep]

            if rep == "B":
                weighted_reputation *= z_mul[zygosity]

            #  Now we apply the spread amplifier, we raise the score to the power of the spread number
            rep_square = pow(spread, weighted_reputation)
            total_reputation += rep_square
        try:
            UserGeneReputation.objects.create(gene=gene, file=file, score=total_reputation)
        except:
            pass
        file.update_progress()


def detect_service(file):
    # line = file.readline().decode()
    mime = magic.from_file(file)
    if mime == 'ASCII text, with very long lines':
        return File.SERVICE_VCF
    else:
        lines = list(islice(open(file), 0, 50))
        line = lines[0]
        if not isinstance(line, str):
            line = line.decode()
        text = " ".join([(l if isinstance(l, str) else l.decode()) for l in lines])

        if "23andMe" in line or "# rsid\tchromosome\tposition\tgenotype" in text:
            return File.SERVICE_23ANDME
        elif "AncestryDNA" in line:
            return File.SERVICE_ANCESTRY
        elif "Courtangen" in line or "rsid\tchromosome\tposition\tgenotype" in text:
            return File.SERVICE_COURTAGEN
        elif "RSID,CHROMOSOME,POSITION,RESULT" in line:
            return File.SERVICE_FAMILY_TREE
        elif "fileformat=VCF" in line:
            return File.SERVICE_VCF
        return File.SERVICE_UNKNOWN


def get_data_to_file(user_id, file_pk):
    user = User.objects.get(id=user_id)
    obj = File.objects.get(pk=file_pk)
    file_name = obj.original_name
    static_dir = 'staticfiles/'

    try:
        print(static_dir + file_name)
        data = get_s3_data_to_file(file_name)
        print("finished writing to file")
        print("Unzipping file...")
        archive, file, name = unzip_any_file(static_dir + file_name)
        print("Successfully unzipped")
        # name = name or file_name

        print("Detecting file service...")
        service = detect_service(file)
        obj.status = File.FILE_STATUS_PROCESSING
        obj.service = service
        obj.save()
        #
        return archive, file, name, user, obj
    except:
        handle_errors(obj)
        return None


def process_rsid_file(df, obj):
    p_total = len(df) + Gene.objects.count()
    obj.set_total_points(p_total, latency=100)
    print("Process file...")
    for index, item in df.iterrows():
        rsid = item[0]
        genotype = item[3]
        snp = Snp.objects.filter(rsid=rsid).first()
        if snp is not None:
            user_rsid = UserRsid.objects.filter(file=obj, rsid=rsid).first()
            if not user_rsid:
                UserRsid.objects.create(
                    rsid=rsid,
                    genotype=genotype,
                    file=obj,
                    genotype_style=check_genotype_style(genotype, snp)
                )
            else:
                user_rsid.genotype_style = check_genotype_style(genotype, snp)
                user_rsid.genotype = genotype
                user_rsid.save()
        obj.update_progress()


@app.task
def process_genome_file(user_id, dashboard_uri, file_pk, is_rescan=False):
    print("Start processing genome file...")
    services = {
        File.SERVICE_23ANDME: {"function": upload, "service": File.SERVICE_23ANDME},
        File.SERVICE_ANCESTRY: {"function": upload_ancestry, "service": File.SERVICE_ANCESTRY},
        File.SERVICE_COURTAGEN: {"function": upload_courtagen, "service": File.SERVICE_COURTAGEN},
        File.SERVICE_FAMILY_TREE: {"function": upload_family_tree, "service": File.SERVICE_FAMILY_TREE},
        File.SERVICE_VCF: {"function": upload_vcf, "service": File.SERVICE_VCF},
    }

    print("Download file from s3...")
    result = get_data_to_file(user_id, file_pk)
    if not result:
        return
    archive, file, name, user, obj = result
    try:
        if obj.service == File.SERVICE_UNKNOWN:
            line = file.readline().decode()
            raise Exception("Could not identify service, first line: %s" % line)
        print("Service detected as: %s" % obj.get_service_display())
        service = services.get(obj.service)
        fn = service.get("function")
        fn(archive, file, name, user, obj, dashboard_uri)

        obj.rescan_available = True
        obj.update_progress(100)
        if not is_rescan:
            user.user_profile.file_uploads_count += 1
            user.user_profile.save()
        send_completed_email(dashboard_uri, user, obj)

        original_file = file[:-13]

        if os.path.isfile(file):
            os.remove(file)
        if os.path.isfile(file):
            os.remove(original_file)

    except Exception:
        handle_errors(obj)


def upload(archive, file, name, user, obj, dashboard_uri):
    print('tasks.upload Start processing file %s' % name)

    df = pd.read_csv(file, nrows=1, header=None)
    try:
        obj.sequenced_at = df.ix[0, 0][df.ix[0, 0].index(":") + 2:]
    except:
        pass

    if archive:
        file = archive.open(name)

    # Slice to first (Header) row
    for row in file:
        row = row.decode()
        if row.startswith('# rsid'):
            break

    df = pd.read_csv(file, header=0, delimiter="\t", dtype={"# rsid": str, "chromosome": str, "position": str, "genotype": str})  # combine the upload with adding headers to speed it up

    df.columns = ["rsid", "chromosome", "position", "genotype"]

    process_rsid_file(df, obj)

    calculate_total_reputation(obj)

    print('tasks.upload Finished processing file %s' % name)


def upload_ancestry(archive, file, name, user, obj, dashboard_uri):
    try:
        print('tasks.upload_ancestry Start processing file %s' % name)

        df = pd.read_csv(file, header=0, comment='#', delimiter="\t", dtype={"rsid": str, "chromosome": str, "position": str, "allele1": str, "allele2": str}) #combine the upload with adding headers to speed it up

        df["genotype"] = df["allele1"] + df["allele2"]
        df = df[["rsid", "chromosome", "position", "genotype"]]

        process_rsid_file(df, obj)

        calculate_total_reputation(obj)

        print('tasks.upload_ancestry Finished processing file %s' % name)
    except Exception:
        handle_errors(obj)


def upload_courtagen(archive, file, name, user, obj, dashboard_uri):
    try:
        print('tasks.upload_courtagen Start processing file %s' % name)

        df = pd.read_csv(file, header=20, delimiter="\t", dtype={"# rsid": str, "chromosome": str, "position": str, "genotype": str})  # combine the upload with adding headers to speed it up
        df.columns = ["rsid", "chromosome", "position", "genotype"]
        df = df[["rsid", "chromosome", "position", "genotype"]]

        process_rsid_file(df, obj)

        calculate_total_reputation(obj)

        obj.update_progress(100)
        send_completed_email(dashboard_uri, user, obj)
        print('tasks.upload_courtagen Finished processing file %s' % name)
    except Exception:
        handle_errors(obj)


def upload_family_tree(archive, file, name, user, obj, dashboard_uri):
    try:
        print('tasks.upload_family_tree Start processing file %s' % name)

        df = pd.read_csv(file, engine='c', header=0, delimiter=',', dtype={"RSID": str, "CHROMOSOME": str, "POSITION": str, "RESULT": str})
        df.columns = ["rsid", "chromosome", "position", "genotype"]

        process_rsid_file(df, obj)

        calculate_total_reputation(obj)

        print('tasks.upload_family_tree Finished processing file %s' % name)
    except Exception:
        handle_errors(obj)


@app.task
def upload_23andme(user_id, code, file_pk, is_rescan=False):
    print("tasks.uploade_23andme api Start processing...")
    user = User.objects.get(id=user_id)
    obj = File.objects.get(pk=file_pk)
    try:
        user_profile_instance = UserProfile.objects.get(user=user)
        user_profile_instance.active_file = obj
        user_profile_instance.save()

        api = Api23AndMe()
        # Refresh token every 12 hours
        if user.user_profile.refresh_token \
                and user.user_profile.token_refresh_date <= timezone.now() - timedelta(hours=12):
            print("Refresh api token")
            access = api.get_refresh_token(user.user_profile.refresh_token)
        elif not user.user_profile.refresh_token:
            access = api.get_access_token(code)
            user.user_profile.token_refresh_date = timezone.now()
        else:
            access = {
                "access_token": user.user_profile.access_token,
                "refresh_token": user.user_profile.refresh_token,
            }
        access_token = access.get("access_token")
        refresh_token = access.get("refresh_token")
        api_user = api.get_user(access_token)
        print("Get User genomes...")
        genomes = api.get_genomes(access_token, api_user.get("profiles")[0].get("id"))

        user.user_profile.access_token = access_token
        user.user_profile.refresh_token = refresh_token
        user.user_profile.save()

        n = 2
        pair_list = [genomes.get("genome")[i:i+n] for i in range(0, len(genomes.get("genome")), n)]
        df = pd.DataFrame({"genotype": pair_list})
        del pair_list
        print("Get snps list")
        snps_res = api.get_snps_resources()

        df2 = pd.read_csv(snps_res, header=3, delimiter="\t")
        del snps_res
        df3 = df2.join(df)
        df3 = df3[["snp", "chromosome", "chromosome_position", "genotype"]] #filter this in order to decrease iterations and to decrease rows in memory
        df3 = df3[numpy.invert(df3["genotype"].str.contains("__"))]

        obj.status = File.FILE_STATUS_PROCESSING
        obj.save()

        process_rsid_file(df3, obj)
        del df3

        calculate_total_reputation(obj)

        if not is_rescan:
            user.user_profile.file_uploads_count += 1
            user.user_profile.save()

        obj.update_progress(100)
        print("Done processing 23AndMe Connect api")
    except:
        handle_errors(obj)


@app.task
def delete_uploaded_file(user_id, file_id):
    file = File.objects.get(user_id=user_id, pk=file_id, deleted_at__isnull=False)
    print('Removing file %s for user %s' % (file_id, user_id,))

    file.genes_to_look_at.clear()
    UserRsid.objects.filter(file=file).delete()

    file.delete()
    print('File fully removed')


def s3_file_dwnld_url_utility(key_name, out_path):
    os.environ['S3_USE_SIGV4'] = S3_USE_SIGV4
    os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY
    s3 = boto3.client('s3')

    try:
        if boto3.resource('s3').Object(settings.S3_BUCKET, key_name).load():
            s3.delete_object(
                Bucket=settings.S3_BUCKET,
                Key=key_name
            )
    except:
        pass

    s3.upload_file(out_path, settings.S3_BUCKET, key_name)
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': settings.S3_BUCKET,
            'Key': key_name
        }
    )

    return url


@app.task
def gene_report_pdf_snps(user_id, file_id, host_path="127.0.0.1:8000", report_type='introductory',
                            report_name=None, genetic_report_id=None):
    # TODO: pdf genrate
    user = User.objects.get(id=user_id)
    if not file_id:
        file = user.user_profile.active_file
    else:
        file = File.objects.get(id=file_id)

    if report_type == 'cardio':
        report_pdf_snps_data = get_cardiovascular_report_pdf_snps_data(user, file.id)
        template = get_template('genome/reports/cardiovascular_pdf_report_generate.html')
    elif report_type == 'inflammation':
        report_pdf_snps_data = get_inflammatory_report_pdf_snps_data(user, file.id)

        template = get_template('genome/reports/inflammatory_pdf_report.html')
    else:
        report_pdf_snps_data = get_introductory_report_pdf_snps_data(user, file.id)
        #~ template = get_template('genome/reports/snp_pdf_report_generate.html')
        template = get_template('genome/reports/new_snp_pdf_report_generate.html')

    context = {
        'host_path': 'http://%s/' % host_path,
        'report_pdf_snps_data': report_pdf_snps_data,
        'user': user,
        'counter': 0
    }

    html = template.render(context=context, request=None)
    date = datetime.now().strftime('%Y%m%d')
    
    if report_name:
        out_file = '%s.pdf' % report_name
        key_name = 'reports/%s.pdf' % report_name
    else:
        key_name = 'reports/%s_%s_%s.pdf' % (date, report_type, file.file_name)
        out_file = '%s_%s_%s.pdf' % (date, report_type, file.file_name)

    options = {
        'page-size': 'A4',
        'encoding': "UTF-8",
        'margin-top': '0in',
        'margin-right': '0in',
        'margin-bottom': '0in',
        'margin-left': '0in',
        'zoom': 1
    }
    
    tmp_file = tempfile.NamedTemporaryFile(mode='wb', prefix=out_file, suffix=".pdf", delete="False")
    tmp_file.close()
    pdfkit.from_string(html, tmp_file.name, options=options)

    # email_title = 'My %s Report' % report_type.title()
    # email_content = render_to_string('genome/reports/pdf_report_email.html', {'user': user})

    # msg = EmailMessage(email_title, email_content, to=[user.email])
    # msg.attach_file(tmp_file.name)
    # msg.content_subtype = "html"
    # msg.send()

    url = s3_file_dwnld_url_utility(key_name, tmp_file.name)

    genetic_report = GeneticReports.objects.get(id=genetic_report_id)
    genetic_report.file_download_path = url
    genetic_report.save()
    user.user_profile.free_reports_available -= 1
    user.user_profile.save()

    response = {
        'status': 'complete',
        'genetic_report_id': genetic_report.id,
        'report_type': report_type,
        'url': url
    }

    return response


@app.task
def gene_report_pdf_creator(report_state, host_path, user_id, reports_files_id):
    template = get_template('genome/reports/snp_static_report_.html')
    
    context = {
        'host_path': 'http://%s/' % host_path
    }

    html = template.render(context=context, request=None)
    out_path = '/tmp/%s-%s.pdf' % (report_state, user_id)

    options = {
        'page-size': 'A4',
        'encoding': "UTF-8",
        'margin-top': 15,
        'margin-bottom': 15,
        'zoom': 1
    }

    pdfkit.from_string(html, out_path, options=options)

    key_name = 'reports/%s-%s.pdf' % (report_state, user_id)
    url = s3_file_dwnld_url_utility(key_name, out_path)
    
    user = User.objects.get(id=user_id)
    if ReportsFiles.objects.filter(user=user).exists():
        ReportsFiles.objects.filter(
            id=reports_files_id,
            user=user
        ).update(updated_at=timezone.now(), status='completed', report_url=url)

    response = {
        'reports_files_id': reports_files_id,
        'status': 'complete',
        'url': url
    }

    return response


def upload_vcf(archive, file, name, user, obj, dashboard_uri):
    try:
        print('tasks.upload_vcf Start processing file %s' % name)
        vcf_reader = vcf.Reader(open(file), 'r')
        user_rsids = list(UserRsid.objects.filter(file=obj).values_list("rsid", flat=True))
        p_total = Snp.objects.count() + Gene.objects.count()
        obj.set_total_points(p_total, latency=100)
        print("Process file...")
        sample = vcf_reader.samples[0]
        for record in vcf_reader:
            snp = Snp.objects.filter(rsid=record.ID).first()
            chr_id = str(record.CHROM).replace('chr', '')
            chr_pos = str(record.POS)
            if snp is None:
                snp = Snp.objects.filter(chr_id=chr_id, chr_pos=chr_pos).first()
            if snp is not None and snp.rsid not in user_rsids:
                genotype = record.genotype(sample).gt_bases
                if genotype:
                    genotype = genotype.replace('/', '')
                    UserRsid.objects.create(
                        rsid=snp.rsid,
                        chromosome=chr_id,
                        position=chr_pos,
                        genotype=genotype,
                        file=obj,
                        genotype_style=check_genotype_style(genotype, snp)
                    )
                    user_rsids.append(snp.rsid)
                    obj.update_progress()
        print('tasks.upload_vcf Finished processing file %s' % name)
    except Exception:
        handle_errors(obj)


@app.task
def prepare_report_file(serialized_request):
    deserialized_request = json.loads(serialized_request)

    per_page = get_report_pagination(deserialized_request['per_page'])
    pages = int(deserialized_request['pages'])
    report_state = deserialized_request['report_state']
    user = User.objects.filter(pk=deserialized_request["user_id"]).first()

    if ReportsFiles.objects.filter(user=user).exists():
        ReportsFiles.objects.filter(user=user).update(
            status='pending'
        )
    else:
        ReportsFiles.objects.create(
            user=user,
            report_url='',
            created_at=timezone.now(),
            updated_at=timezone.now(),
            status='pending'
        )

    get_report_params = {
        "snps_to_look_at": {"function": get_snps_report_data, "filename": "My Bad SNPs report",
                            "default_paginator": True},
        "my_important_snps": {"function": get_important_report_data, "filename": "My Important SNPs report",
                              "default_paginator": True},
        "my_rare_snps": {"function": get_rare_report_data, "filename": "My Bad Rare SNPs report",
                         "default_paginator": True},
        "bookmarked_snps": {"function": get_bookmarked_report_data, "filename": "My Bookmarked SNPs report",
                            "default_paginator": True},
        "variance_report": {"function": get_snp_explorer_data, "filename": "My Custom SNPs report",
                            "default_paginator": False},
        "list_gene_pack": {"function": get_list_gene_pack_data, "filename": "My Gene Pack SNPs report",
                           "default_paginator": True},
    }
    params = get_report_params[report_state]

    query_set = params['function'](deserialized_request)
    template = get_template('fileapi/pdf_report_template.html')

    if params['default_paginator']:
        paginator, page_set = paginate_report(deserialized_request, query_set, per_page=per_page * pages)
        object_list = page_set.object_list
    else:
        object_list, paginator = paginate_sqla_statement(query_set, deserialized_request['page'], per_page=per_page * pages)
        setattr(paginator, 'count', paginator.total_count)

    data_set = [(obj._asdict() if not isinstance(obj, (dict, ResultObject,)) else obj) for obj in object_list]

    data_set = _snps_has_info(data_set, user.user_profile.active_file)

    genes = _get_snps_genes(data_set)

    context = {
        "query_set": data_set,
        "query_set_count": paginator.count,
        "genes": genes,
        "user": user,
    }
    html = template.render(context)

    import pdfkit
    out_path = '/tmp/%s-%s.pdf' % (report_state, deserialized_request["user_id"],)

    options = {
        'page-size': 'A4',
        'encoding': "UTF-8",
        'margin-top': 15,
        'margin-bottom': 15,
        'zoom': 1
    }

    pdfkit.from_string(html, out_path, options=options)

    os.environ['S3_USE_SIGV4'] = S3_USE_SIGV4
    os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY

    s3 = boto3.client('s3')
    key_name = 'reports/%s-%s.pdf' % (report_state, deserialized_request["user_id"],)

    if boto3.resource('s3').Object(settings.S3_BUCKET, key_name).load():
        s3.delete_object(
            Bucket=settings.S3_BUCKET,
            Key=key_name
        )

    s3.upload_file(out_path, settings.S3_BUCKET, key_name)

    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': settings.S3_BUCKET,
            'Key': key_name
        }
    )
    if ReportsFiles.objects.filter(user=user).exists():
        ReportsFiles.objects.filter(user=user).update(
            report_url=url,
            updated_at=timezone.now(),
            status='completed'
        )

