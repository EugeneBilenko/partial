from django.template.loader import get_template
from django.db.models import F
from django.db.models import Q, Count
from django.contrib.auth.models import User
from genome.models import Snp, DiseaseTrait, DiseaseHierarchy, Gene, UserRsid, SnpGenes, SnpStudy, GenePack
from genome.helpers import filter_by_term, paginate_sqla_statement
from chemical.models import Chemical
from decodify.aggregators import JsonAgg, ArrayAgg

from sqlalchemy import alias
from sqlalchemy import asc
from sqlalchemy import column
from sqlalchemy import desc
from sqlalchemy.orm import Query
from sqlalchemy.sql import label
from sqlalchemy.sql.functions import coalesce, func
from sqlalchemy import and_
from sqlalchemy import or_

from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator, EmptyPage


def get_report_pagination(paginate_by):
    # value = request.GET.get('paginate_by', 50)
    if paginate_by in ['100', '200', '300', '400', '500']:
        return int(paginate_by)
    return 50


def get_snps_report_data(deserialized_request):
    # disease_name = request.GET.get("disease")
    # request.user.user_profile.active_file_id
    disease_name = deserialized_request["disease_name"]
    active_file_id = deserialized_request["active_file_id"]
    result = Snp.objects.filter(
        importance__gte=4,
        related_genes__excluded=False,
        genes__name__isnull=False
    ).prefetch_related(
        "studies", "genes"
    ).extra(
        select={
            "user_genotype": "genome_userrsid.genotype",
            "user_genotype_style": "genome_userrsid.genotype_style",
            # "gene_name": "genome_gene.name",
        },
        tables=["genome_userrsid"],
        where=[
            "genome_snp.rsid = genome_userrsid.rsid",
            "genome_userrsid.file_id = %s" % active_file_id,
            "genome_userrsid.genotype_style='homozygous_minor' OR genome_userrsid.genotype_style='minor'",
        ]
    ).annotate(
        snpstudies=JsonAgg(
            "studies__risk_allele", "studies__risk_allele_frequency",
            "studies__diseasestraits__name", "studies__p_value",
            distinct=True
        ),
        genes_list=ArrayAgg("genes__name", distinct=True)
    ).order_by("genes_list").all()

    if disease_name:
        diseases = DiseaseTrait.objects.filter(name__istartswith=disease_name).values_list("id", flat=True)

        hierarchy = DiseaseHierarchy.objects.filter(
            Q(disease__name__istartswith=disease_name)
        ).order_by("level").first()

        if hierarchy:
            diseases = list(hierarchy.get_descendants().values_list("disease_id", flat=True)) + list(diseases)
        result = result.filter(studies__diseasestraits__pk__in=diseases)
    return result.values(
        "pk", "rsid", "user_genotype", "user_genotype_style", "genes_list", "snpstudies",
        "importance", "minor_allele", "minor_allele_frequency", "red_flag",
    )


def get_important_report_data(deserialized_request):
    # search_object = request.GET.get("search_object")
    # query = request.GET.get("query")
    # request.user.user_profile.active_file_id

    search_object = deserialized_request["search_object"]
    query = deserialized_request["query"]
    active_file_id = deserialized_request["active_file_id"]

    if search_object == 'gene' and query:
        gene = Gene.objects.filter(name__icontains=query).first()
        query_qs = Q(genes=gene)
    elif search_object == 'chemical' and query:
        chemical = Chemical.objects.filter(name__contains=query).exclude(
            recommendation_status='disallow_everywhere',
            categories__name__icontains='Obscure Chemicals'
        ).first()
        query_qs = Q(genes__chemicalgeneinteraction__chemical=chemical)
    elif search_object == 'disease' and query:
        disease = DiseaseTrait.objects.filter(name__contains=query).first()
        query_qs = Q(studies__diseasestraits=disease)
    else:
        query_qs = Q()

    result = Snp.objects.filter(
        query_qs,
        importance__gte=5,
        related_genes__excluded=False,
        genes__name__isnull=False,
    ).prefetch_related(
        "studies", "genes"
    ).extra(
        select={
            "user_genotype": "genome_userrsid.genotype",
            "user_genotype_style": "genome_userrsid.genotype_style",
            # "gene_name": "genome_gene.name",
        },
        tables=["genome_userrsid"],
        where=[
            "genome_snp.rsid = genome_userrsid.rsid",
            "genome_userrsid.file_id = %s" % active_file_id,
        ]
    ).annotate(
        snpstudies=JsonAgg(
            "studies__risk_allele", "studies__risk_allele_frequency",
            "studies__diseasestraits__name", "studies__p_value",
            distinct=True
        ),
        genes_list=ArrayAgg("genes__name", distinct=True)
    ).order_by("genes_list").all()
    return result.values(
        "pk", "rsid", "user_genotype", "user_genotype_style", "genes_list", "snpstudies",
        "importance", "minor_allele", "minor_allele_frequency", "red_flag",
    )


def get_rare_report_data(deserialized_request):
    # request.user.user_profile.active_file_id
    active_file_id = deserialized_request["active_file_id"]
    result = Snp.objects.filter(
        importance__gte=1,
        minor_allele_frequency__lt=0.15,
        minor_allele_frequency__gt=0,
        related_genes__excluded=False,
        genes__name__isnull=False
    ).prefetch_related(
        "studies", "genes"
    ).extra(
        select={
            "user_genotype": "genome_userrsid.genotype",
            "user_genotype_style": "genome_userrsid.genotype_style",
        },
        tables=["genome_userrsid"],
        where=[
            "genome_snp.rsid = genome_userrsid.rsid",
            "genome_userrsid.file_id = %s" % active_file_id,
            "genome_userrsid.genotype_style = 'homozygous_minor'",
        ]
    ).annotate(
        snpstudies=JsonAgg(
            "studies__risk_allele", "studies__risk_allele_frequency",
            "studies__diseasestraits__name", "studies__p_value",
            distinct=True
        ),
        genes_list=ArrayAgg("genes__name", distinct=True)
    ).order_by("genes_list").all()

    return result.values(
        "pk", "rsid", "user_genotype", "user_genotype_style", "genes_list", "snpstudies",
        "importance", "minor_allele", "minor_allele_frequency", "red_flag",
    )


def get_bookmarked_report_data(deserialized_request):
    user_id = deserialized_request["user_id"]
    active_file_id = deserialized_request["active_file_id"]
    user = User.objects.filter(pk=user_id).first()
    result = user.user_profile.bookmarked_snps.prefetch_related(
        "studies", "genes"
    ).filter(
        related_genes__excluded=False,
        genes__name__isnull=False
    ).extra(
        select={
            "user_genotype": "genome_userrsid.genotype",
            "user_genotype_style": "genome_userrsid.genotype_style",
            # "gene_name": "genome_gene.name",
        },
        tables=["genome_userrsid"],
        where=[
            "genome_snp.rsid = genome_userrsid.rsid",
            "genome_userrsid.file_id = %s" % active_file_id,
        ]
    ).annotate(
        snpstudies=JsonAgg(
            "studies__risk_allele", "studies__risk_allele_frequency",
            "studies__diseasestraits__name", "studies__p_value",
            distinct=True
        ),
        genes_list=ArrayAgg("genes__name", distinct=True)
    ).order_by("genes_list").all()

    return result.values(
        "pk", "rsid", "user_genotype", "user_genotype_style", "genes_list", "snpstudies",
        "importance", "minor_allele", "minor_allele_frequency", "red_flag",
    )


def get_snp_explorer_data(deserialized_request):
    query = deserialized_request["query"]
    sort_by = deserialized_request["sort_by"]
    has_description = deserialized_request["has_description"]
    sbmt = deserialized_request["sbmt"]
    search_object = deserialized_request["search_object"]
    active_file_id = deserialized_request["active_file_id"]

    aljquery = Snp.sa.query(
        Snp.sa.id.label('pk'), Snp.sa.rsid, Snp.sa.importance, Snp.sa.minor_allele,
        Snp.sa.minor_allele_frequency, Snp.sa.red_flag,
        UserRsid.sa.genotype.label('user_genotype'),
        UserRsid.sa.genotype_style.label('user_genotype_style'),
        func.get_genotype_frequency(
            Snp.sa.id,
            UserRsid.sa.genotype,
            'ALL'
        ).label('get_genotype_frequency'),
        label(
            'genes_list',
            column("""ARRAY_AGG(DISTINCT "genome_gene"."name")""", is_literal=True)),
        label(
            'snpstudies',
            column("""
                    JSON_AGG(DISTINCT
                        ("genome_snpstudy"."risk_allele",
                        "genome_snpstudy"."risk_allele_frequency",
                        "genome_diseasetrait"."name",
                        "genome_snpstudy"."p_value"))""", is_literal=True)),
        label(
            'rflag',
            column("""
                    red_flag_algo(
                        minor_allele,
                        JSON_AGG(DISTINCT
                            ("genome_snpstudy"."risk_allele",
                            "genome_snpstudy"."risk_allele_frequency",
                            "genome_diseasetrait"."name",
                            "genome_snpstudy"."p_value")
                        ),
                        genome_userrsid.genotype
                    )""", is_literal=True))).filter(
        Gene.sa.name != None,
        SnpGenes.sa.excluded == False,
        UserRsid.sa.file_id == active_file_id,
        Snp.sa.rsid == UserRsid.sa.rsid
    ).join(SnpGenes.sa).join(Gene.sa).outerjoin(SnpStudy.sa).join(
        UserRsid.sa, UserRsid.sa.rsid == Snp.sa.rsid
    ).outerjoin(SnpStudy.sa.diseasestraits).group_by(
        Snp.sa.id, UserRsid.sa.genotype,
        UserRsid.sa.genotype_style
    )

    if sbmt and has_description == 'on':
        aljquery = aljquery.filter(and_(Snp.sa.description_advanced != ''))

    if not sort_by:
        aljquery = aljquery.order_by('genes_list')

    elif sort_by == 'important_snps':
        aljquery = aljquery.order_by(desc(Snp.sa.importance), 'genes_list')

    elif sort_by == 'red_flagged':
        aljquery = aljquery.having(
            column("""
                        red_flag_algo(
                            minor_allele,
                            JSON_AGG(DISTINCT
                                ("genome_snpstudy"."risk_allele",
                                "genome_snpstudy"."risk_allele_frequency",
                                "genome_diseasetrait"."name",
                                "genome_snpstudy"."p_value")
                            ),
                            genome_userrsid.genotype
                        )""", is_literal=True) == True
        ).order_by('genes_list')

    elif sort_by == 'most_rare':
        aljquery = aljquery.filter(
            and_(
                or_(
                    UserRsid.sa.genotype_style == 'homozygous_minor',
                    UserRsid.sa.genotype_style == 'minor'
                )
            )
        ).order_by('genes_list')

    if query:
        aljquery = filter_by_term(aljquery, search_object, query)

    return aljquery


def get_list_gene_pack_data(deserialized_request, gene_pack=None):
    entity_pk = deserialized_request["entity_pk"]
    active_file_id = deserialized_request["active_file_id"]
    if gene_pack is None:
        gene_pack = GenePack.objects.prefetch_related(
            "genes"
        ).get(id=entity_pk)

    result = Snp.objects.filter(
        importance__gte=1,
        minor_allele_frequency__lte=1.0,
        genes__name__isnull=False,
        genes__in=list(gene_pack.genes.all())
    ).prefetch_related(
        "studies", "genes"
    ).extra(
        select={
            "user_genotype": "genome_userrsid.genotype",
            "user_genotype_style": "genome_userrsid.genotype_style",
            # "gene_name": "genome_gene.name",
        },
        tables=["genome_userrsid"],
        where=[
            "genome_snp.rsid = genome_userrsid.rsid",
            "genome_userrsid.file_id = %s" % active_file_id,
        ]
    ).annotate(
        snpstudies=JsonAgg(
            "studies__risk_allele", "studies__risk_allele_frequency",
            "studies__diseasestraits__name", "studies__p_value",
            distinct=True
        ),
        genes_list=ArrayAgg("genes__name", distinct=True)
    ).order_by("genes_list").all()

    return result.values(
        "pk", "rsid", "user_genotype", "user_genotype_style", "genes_list", "snpstudies",
        "importance", "minor_allele", "minor_allele_frequency", "red_flag",
    )


def paginate_report(deserialized_request, data_list, per_page=50):
    p = deserialized_request["page"]
    paginator = Paginator(data_list, per_page)
    try:
        page_set = paginator.page(p)
    except PageNotAnInteger:
        page_set = paginator.page(1)
    except EmptyPage:
        page_set = paginator.page(paginator.num_pages)
    return paginator, page_set


