from django.db.models import Case, CharField, Count, Max, F, Value, When
from rest_framework.decorators import detail_route, list_route
from sqlalchemy import and_
from sqlalchemy import column
from sqlalchemy import desc
from sqlalchemy import distinct
from sqlalchemy import func
from sqlalchemy.sql import label

from rest_framework.decorators import detail_route
from rest_framework.generics import UpdateAPIView, GenericAPIView, RetrieveUpdateAPIView
from rest_framework.mixins import UpdateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from sqlalchemy import and_, column, desc, distinct, func
from sqlalchemy.sql import label

from analysis.models import CustomSymptomSeverity, CustomConditionSeverity
from api.serializers import (
    ChemicalPathwaySerializer, ChemicalGeneInteractionSerializer, ChemicalOrganismSerializer,
    SnpSerializer, UserProfileSymptomSerializer, CustomSymptomSeveritySerializer,
    UserProfileConditionSerializer, CustomConditionSeveritySerializer, UserProfileSerializer
)
from chemical.models import Chemical
from decodify.aggregators import ArrayAgg

from genome.helpers import badges_for_gene, paginate_sqla_statement
from genome.models import Gene, Snp, UserRsid, SnpStudy, UserProfileSymptoms, UserProfileCondition
from users.models import CollectedEmail
from fileapi.tasks import gene_report_pdf_snps


class ChemicalView(GenericViewSet):
    """
    Get chemical related data
    """

    queryset = Chemical.objects.all()

    @detail_route(url_path="related-pathways")
    def related_pathways(self, request, pk):
        instance = self.get_object()
        pathways = instance.pathways.all()
        pathways = self.paginate_queryset(pathways)

        return self.get_paginated_response(
            ChemicalPathwaySerializer(pathways, many=True).data
        )

    @detail_route(url_path="genes-interactions")
    def genes_interactions(self, request, pk):
        instance = self.get_object()

        interactions = instance.chemicalgeneinteraction_set.all().annotate(
            total=Count('actions') + F('amount') - 1,
            action=ArrayAgg('actions__action')
        ).order_by('-total').prefetch_related(
            "actions", "actions__interaction_type"
        ).select_related("gene")

        interactions = self.paginate_queryset(interactions)

        all_interact_genes = {interaction.gene.id for interaction in interactions}

        if request.user.is_authenticated():
            contains_risk_allele, bad_genes = badges_for_gene(request.user, all_interact_genes)
            for interaction in interactions:
                setattr(interaction.gene, 'bad_gene', (str(interaction.gene.pk) in bad_genes))
                setattr(interaction.gene, 'contains_risk_allele', (str(interaction.gene.pk) in contains_risk_allele))

        return self.get_paginated_response(
            ChemicalGeneInteractionSerializer(interactions, many=True).data
        )

    @detail_route(url_path="top-organisms")
    def top_organisms(self, request, pk):
        instance = self.get_object()

        organisms = instance.concentrations.exclude(unified_concentration__isnull=True).exclude(
            organism__slug__isnull=True).annotate(
            slug=F("organism__slug"),
            name=Case(
                When(organism__english_name__isnull=False, then=F("organism__english_name")),
                default=F("organism__latin_name"),
                output_field=CharField(),
            )).values("slug", "name", "organism__english_name", "organism__latin_name", "organism__slug", "conc_unit",
                      "conc_min", "conc_max").annotate(
            max_conc=Max("unified_concentration")).filter(rel_type="organism").order_by("-max_conc").all()

        organisms = self.paginate_queryset(organisms)
        return self.get_paginated_response(
            ChemicalOrganismSerializer(organisms, many=True).data
        )


class GeneView(GenericViewSet):
    queryset = Gene.objects.all()
    paginate_by = 20

    def _get_page_link(self, request, direction, pagination_info):
        if direction == 'next' and pagination_info.has_next:
            return request.build_absolute_uri('?page={}'.format(pagination_info.next_page_number))
        elif direction == 'previous' and pagination_info.has_previous:
            return request.build_absolute_uri('?page={}'.format(pagination_info.previous_page_number))
        else:
            return None

    @detail_route(url_path="related-snps")
    def related_snps(self, request, pk):
        page = request.GET.get('page', 1)
        gene = self.get_object()

        snpids = gene.snps.values_list("id", flat=True)
        related_snps = Snp.sa.query(
            Snp.sa.id,
            Snp.sa.rsid,
            Snp.sa.minor_allele,
            Snp.sa.description_simple,
            UserRsid.sa.genotype,
            func.array_agg(distinct(SnpStudy.sa.risk_allele)).label('risk_alleles'),
            Snp.sa.importance,
            label(
                'disease',
                column("""
                            JSON_AGG(DISTINCT
                                ("genome_diseasetrait"."name",
                                "genome_diseasetrait"."slug"))""", is_literal=True))
        ).join(
            UserRsid.sa, UserRsid.sa.rsid == Snp.sa.rsid
        ).join(
            SnpStudy.sa, and_(SnpStudy.sa.snp_id == Snp.sa.id, SnpStudy.sa.risk_allele != None), isouter=True
        ).outerjoin(
            SnpStudy.sa.diseasestraits
        ).filter(
            UserRsid.sa.file_id == request.user.user_profile.active_file.id,
            Snp.sa.id.in_(snpids)
        ).group_by(
            Snp.sa.id, Snp.sa.rsid, Snp.sa.minor_allele, Snp.sa.description_simple, UserRsid.sa.genotype
        ).order_by(desc(Snp.sa.importance))

        result, pagination_info = paginate_sqla_statement(related_snps, page, self.paginate_by)
        res = {
            "count": pagination_info.total_count,
            "next": self._get_page_link(request, 'next', pagination_info),
            "previous": self._get_page_link(request, 'previous', pagination_info),
            "results": SnpSerializer(result, many=True).data
        }
        return Response(res)


class UserProfileSymptomView(UpdateAPIView):
    serializer_class = UserProfileSymptomSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        userprofile = self.request.user.user_profile
        symptom = self.request.POST.get('symptom_id')
        obj = UserProfileSymptoms.objects.get(symptom_id=symptom, userprofile=userprofile)
        return obj

    def put(self, request, *args, **kwargs):
        return self.update(request, partial=True, *args, **kwargs)


class UserProfileConditionView(UserProfileSymptomView):
    serializer_class = UserProfileConditionSerializer

    def get_object(self):
        userprofile = self.request.user.user_profile
        condition = self.request.POST.get('symptom_id')
        obj = UserProfileCondition.objects.get(condition_id=condition, userprofile=userprofile)
        return obj


class CustomSymptomSeverityView(GenericAPIView, UpdateModelMixin, DestroyModelMixin):
    queryset = CustomSymptomSeverity.objects.all()
    serializer_class = CustomSymptomSeveritySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        pk = self.request.POST.get('symptom_id', 0)
        return self.get_queryset().filter(pk=pk).first()

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, partial=True, *args, **kwargs)


class CustomConditionSeverityView(CustomSymptomSeverityView):
    queryset = CustomConditionSeverity.objects.all()
    serializer_class = CustomConditionSeveritySerializer


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.user_profile

    def post(self, request, *args, **kwargs):
        return self.update(request, partial=True, *args, **kwargs)


class PdfGenerateView(GenericViewSet):
    permission_classes = [IsAuthenticated,]

    @list_route(methods=['get'], url_path='pdf')
    def pdf(self, request):
        '''
            Would initiate the tasks for pdf report generation
        '''
        user = request.user
        file_id = request.GET.get('file_id', '')
        report_type = request.GET.get('report_type', '')
        gene_report_pdf_snps.delay(
            user.id,
            file_id,
            report_type=report_type,
            host_path=request.get_host()
            # static_url=settings.STATIC_URL
        )
        return Response(status=200)
