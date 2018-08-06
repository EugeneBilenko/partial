import pdfkit

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import FileResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.contrib import messages
from django.shortcuts import render

from analysis.forms import CreateSystemForm
from analysis.models import System, Symptom, SystemSymptoms
from analysis.helpers import get_recomendations_for_system, get_systems_queryset
from analysis.templatetags.analysis_filters import is_system_threshold_reached
from genome.helpers import get_potentially_problematic_genes
from genome.models import Gene


@login_required
def personalized_health_report(request):
    queryset = get_systems_queryset(request)

    if not queryset:
        return render(request, "analysis/personalized_health_report.html")

    paginator = Paginator(queryset, 1)

    page = request.GET.get('page')
    try:
        system_page = paginator.page(page)
    except PageNotAnInteger:
        system_page = paginator.page(1)
    except EmptyPage:
        system_page = paginator.page(paginator.num_pages)

    symptoms_list = []
    if system_page:
        system_symptoms = set(system_page.object_list[0].symptoms.all().values_list('name', flat=True))
        user_symptoms = set(request.user.user_profile.symptoms.all().values_list('name', flat=True))
        symptoms_list = system_symptoms.intersection(user_symptoms)

    recommendations = get_recomendations_for_system(system_page.object_list[0])

    potentially_problematic_genes = get_potentially_problematic_genes(request.user)
    bad_genes = Gene.objects.filter(snps__id__in=potentially_problematic_genes).annotate(
        gene_cnt=Count('id')).values_list('id', flat=True)
    # bad_genes = set([gene.id for snp in potentially_problematic_genes for gene in snp.genes.all()])
    system_bad_genes = system_page.object_list[0].genes.filter(id__in=bad_genes)

    return render(request, "analysis/personalized_health_report.html", {
        "queryset": queryset,
        "system": system_page,
        "symptoms_list": symptoms_list,
        "recommendations": recommendations,
        "system_bad_genes": system_bad_genes,
    })


@login_required
def personalized_health_pdf_report(request):
    queryset = get_systems_queryset(request)
    potentially_problematic_genes = get_potentially_problematic_genes(request.user)
    user_symptoms = set(request.user.user_profile.symptoms.all().values_list('name', flat=True))
    bad_genes = Gene.objects.filter(snps__id__in=potentially_problematic_genes).annotate(
        gene_cnt=Count('id')).values_list('id', flat=True)

    systems = []
    for system in queryset:
        data = {}

        system_symptoms = set(system.symptoms.all().values_list('name', flat=True))
        symptoms_list = system_symptoms.intersection(user_symptoms)
        system_bad_genes = system.genes.filter(id__in=bad_genes)
        recommendations = get_recomendations_for_system(system)

        data['system'] = system
        data['recommendations'] = recommendations
        data['symptoms_list'] = symptoms_list
        data['system_bad_genes'] = system_bad_genes
        systems.append(data)

    if request.GET.get("pdf"):
        template = get_template('analysis/personalized_health_report_pdf.html')
        context = {
            "systems": systems,
            "request": request,
        }
        html = template.render(context)
        pdf_name = '/tmp/personalized_health_report-%s.pdf' % request.user.pk
        options = {
            'page-size': 'A4',
            'encoding': "UTF-8",
            'margin-top': 15,
            'margin-bottom': 15,
            'zoom': 1
        }
        pdfkit.from_string(html, pdf_name, options=options)
        response = FileResponse(open(pdf_name, 'rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="personalized_health_report.pdf"'
        return response

    return render(request, "analysis/personalized_health_report_pdf.html", {
        "systems": systems,
    })


@login_required
def create_system(request):
    query_set_symptoms = Symptom.objects.all()
    form = CreateSystemForm()
    if request.method == 'POST':
        form = CreateSystemForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = request.user
            instance.save()
            symptoms = zip(request.POST.getlist('symptoms[]'), request.POST.getlist('weights[]'))
            for symptom, weight in symptoms:
                if int(weight) <= 0:
                    continue
                SystemSymptoms.objects.create(
                    system_id=instance.id,
                    symptom_id=symptom,
                    weight=weight
                )
            form.save_m2m()
            messages.success(request, "System {}. Has been created.".format(instance.name))
            return HttpResponseRedirect(reverse('analysis:personalized-health-report'))

    return render(request, "analysis/create-system.html", {
        'form': form,
        'query_set_symptoms': query_set_symptoms
    })


@login_required
def edit_system(request, id):
    instance = get_object_or_404(System, id=id)
    query_set_symptoms = Symptom.objects.all()
    form = CreateSystemForm(instance=instance)
    if request.method == 'POST':
        form = CreateSystemForm(request.POST, instance=instance)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            symptoms = zip(request.POST.getlist('symptoms[]'), request.POST.getlist('weights[]'))
            SystemSymptoms.objects.filter(system=instance).delete()
            for symptom, weight in symptoms:
                if int(weight) <= 0:
                    continue
                SystemSymptoms.objects.create(
                    system_id=instance.id,
                    symptom_id=symptom,
                    weight=weight
                )
            form.save_m2m()
            messages.success(request, "System {}. Has been modified.".format(instance.name))
            return HttpResponseRedirect(reverse('analysis:personalized-health-report'))
    return render(request, 'analysis/edit-system.html', {
        'form': form,
        'instance': instance,
        'symptoms': SystemSymptoms.objects.filter(system=instance),
        'query_set_symptoms': query_set_symptoms,
    })


@login_required
def delete_system(request, id):
    instance = get_object_or_404(System, pk=id)
    if request.user == instance.user:
        instance.delete()
        messages.success(request, "System {}. Has been deleted.".format(instance.name))
    return HttpResponseRedirect(reverse('analysis:personalized-health-report'))
