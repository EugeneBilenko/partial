import csv

import pandas
from django.core.management import BaseCommand

import numpy as np

from django.db import transaction

from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import DiseaseTrait, DiseaseTraitCategory, DiseasePathway, DiseasePathwayInteraction


class Command(BaseCommand):
    help = """Update disease - add gene symbol, synonyms, fullname
            ./manage.py UploadCTDDisease --file CTD_Diseases.csv
    """

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):

        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL)
        data = data.replace(np.nan, '', regex=True)
        pathways = data[["PathwayName", "PathwayID"]].drop_duplicates()
        pathways.columns = ("pathway_name", "pathway_id")
        pathways = pathways.to_dict('records')
        data = data.to_dict('records')
        count = len(data)
        with transaction.atomic():
            interactions_to_create = []
            DiseasePathway.objects.bulk_create([DiseasePathway(
                pathway_name=record["pathway_name"],
                pathway_id=record["pathway_id"]
            ) for record in pathways])
            existing_pathways = dict(DiseasePathway.objects.values_list("pathway_id", "id"))
            existing_diseases = dict(DiseaseTrait.objects.filter(category=disease_category).values_list("ctd_id", "id"))
            existing_genes = dict(Gene.objects.values_list("symbol", "id"))
            for row in data:
                remaining_time(count)
                disease = existing_diseases.get(row["DiseaseID"])
                pathway = existing_pathways.get(row["PathwayID"])
                gene = existing_genes.get(row["InferenceGeneSymbol"].lower())
                interactions_to_create.append(
                    DiseasePathwayInteraction(
                        disease_id=disease,
                        pathway_id=pathway,
                        gene_id=gene,
                        gene_symbol=row["InferenceGeneSymbol"]
                    )
                )
            DiseasePathwayInteraction.objects.bulk_create(interactions_to_create)
disease_category = DiseaseTraitCategory.objects.get(name="Disease")
