import csv

import pandas
from django.core.management import BaseCommand

import numpy as np

from django.db import transaction
from django.db.models import Q

from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import Synonym, DiseaseTrait, DiseaseSynonym, DiseaseTraitCategory, GeneDiseaseTrait


class Command(BaseCommand):
    help = """Update disease - add gene symbol, synonyms, fullname
            ./manage.py UploadCTDDisease --file CTD_Diseases.csv
    """

    def add_arguments(self, parser):
        parser.add_argument('--chemical-disease', type=str)
        parser.add_argument('--gene-disease', type=str)
        parser.add_argument('--disease-pathway', type=str)

    def upload_chemical_disease_interactions(self, file):
        existing_chemicals = dict(Chemical.objects.filter(chemical_number__isnull=False).values_list("chemical_number", "id"))
        existing_diseases = dict(DiseaseTrait.objects.filter(ctd_id__isnull=False).values_list("ctd_id", "id"))
        existing_genes = dict(Gene.objects.filter(symbol__isnull=False).values_list("symbol", "id"))
        import os
        files = os.listdir(file)
        count = len(files)*1000000
        # import pdb
        # pdb.set_trace()
        with transaction.atomic():
            for part in files:
                data = pandas.read_csv(file + part, header=None, comment="#", delimiter=',', quoting=csv.QUOTE_ALL)
                data.columns = ["ChemicalName", "ChemicalID", "CasRN", "DiseaseName", "DiseaseID",
                                "DirectEvidence", "InferenceGeneSymbol", "InferenceScore", "OmimIDs", "PubMedIDs"]
                data = data.replace(np.nan, '', regex=True)
                data = data.to_dict('records')
                interactions_to_create = []
                for row in data:
                    remaining_time(count)
                    chemical = existing_chemicals.get("MESH:"+row["ChemicalID"])
                    disease = existing_diseases.get(row["DiseaseID"])
                    gene = existing_genes.get(row["InferenceGeneSymbol"].lower())
                    # import pdb
                    # pdb.set_trace()
                    if gene and disease:
                        interactions_to_create.append(
                            ChemicalDiseaseInteraction(
                                chemical_id=chemical,
                                disease_id=disease,
                                inference_gene_id=gene,
                                direct_evidence=row["DirectEvidence"],
                                inference_score=float(row["InferenceScore"]) if row["InferenceScore"] else 0,
                                omim_ids=row["OmimIDs"],
                                pub_med_ids=row["PubMedIDs"],
                                cas_rn=row["CasRN"]
                            )
                        )
                    else:
                        continue
                ChemicalDiseaseInteraction.objects.bulk_create(interactions_to_create)

    def handle(self, *args, **options):
        self.upload_chemical_disease_interactions(options.get("gene_disease"))
