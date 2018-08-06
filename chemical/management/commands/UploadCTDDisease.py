import csv

import pandas
from django.core.management import BaseCommand

import numpy as np

from django.db import transaction
from django.db.models import Q

from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import Synonym, DiseaseTrait, DiseaseSynonym, DiseaseTraitCategory


class Command(BaseCommand):
    help = """Update disease - add gene symbol, synonyms, fullname
            ./manage.py UploadCTDDisease --file CTD_Diseases.csv
    """

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def create_and_update_synonyms(self, disease, row):
        synonyms = []
        if row["ctd_synonyms"]:
            synonyms = row["ctd_synonyms"].split("|")
        list_to_append = []
        for synonym in synonyms:
            list_to_append.append(
                DiseaseSynonym.objects.get_or_create(
                    name=synonym
                )[0])
        if list_to_append:
            disease.ctd_synonyms.add(*list_to_append)

    def update_existing_disease(self, disease, row):
        disease.ctd_name = row["ctd_name"]
        disease.ctd_id = row["ctd_id"]
        disease.ctd_alt_id = row["ctd_alt_id"]
        disease.ctd_definition = row["ctd_definition"]
        disease.ctd_parent_ids = row["ctd_parent_ids"]
        disease.ctd_tree_numbers = row["ctd_tree_numbers"]
        disease.ctd_parent_tree_numbers = row["ctd_parent_tree_numbers"]
        disease.ctd_slim_mapping = row["ctd_slim_mapping"]
        disease.save()
        self.create_and_update_synonyms(disease, row)

    def create_new_disease(self, row):
        disease = DiseaseTrait.objects.create(
            name=row["ctd_name"],
            slug=slugify(row["ctd_name"]),
            ctd_name=row["ctd_name"],
            ctd_id=row["ctd_id"],
            ctd_alt_id=row["ctd_alt_id"],
            ctd_definition=row["ctd_definition"],
            ctd_parent_ids=row["ctd_parent_ids"],
            ctd_tree_numbers=row["ctd_tree_numbers"],
            ctd_parent_tree_numbers=row["ctd_parent_tree_numbers"],
            ctd_slim_mapping=row["ctd_slim_mapping"],
            category=disease_category
        )
        self.create_and_update_synonyms(disease, row)

    def handle(self, *args, **options):
        headers = {
            "DiseaseName": str, "DiseaseID": str, "AltDiseaseIDs": str, "Definition": str, "ParentIDs": str,
            "TreeNumbers": str, "ParentTreeNumbers": str, "Synonyms": str, "SlimMapping": str

        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "ctd_name", "ctd_id", "ctd_alt_id", "ctd_definition", "ctd_parent_ids", "ctd_tree_numbers",
            "ctd_parent_tree_numbers", "ctd_synonyms", "ctd_slim_mapping"
        ]
        data = data.replace(np.nan, '', regex=True)
        count = len(data)
        with transaction.atomic():
            for index, row in data.iterrows():
                remaining_time(count)
                query = Q(name__iexact=row["ctd_name"])
                for synonym in row.ctd_synonyms.split("|"):
                    query |= Q(name__iexact=synonym)
                diseases = DiseaseTrait.objects.filter(category=disease_category).filter(query)
                if diseases.exists():
                    for disease in diseases:
                        self.update_existing_disease(disease, row)
                else:
                    self.create_new_disease(row)


disease_category = DiseaseTraitCategory.objects.get(name="Disease")
