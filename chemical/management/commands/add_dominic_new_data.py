import csv
import time
import datetime
import math
from django.db import transaction

import pandas
from django.core.management import BaseCommand
from django.db.models import Q

import numpy as np

from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import Synonym, GeneOntology, DiseaseGOAssociations


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Command(BaseCommand):
    help = """
    ./manage.py UploadGoDisease --file ~/Downloads/CTD_Disease-GO_cellular_component_associations.csv --go-type 'cellular-component'
    """

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def update_and_create_organisms(self, file_path):
        data = pandas.read_csv(file_path, header=0, delimiter='\t', quoting=csv.QUOTE_ALL)
        data = data.replace(np.nan, '', regex=True)
        data = data.to_dict('records')
        organisms_to_create = []
        with transaction.atomic():
            for row in data:
                if row["id"] < 566:
                    organism = Organism.objects.filter(id=row["id"]).first()
                    organism.scientific_name_full = row["scientific_name_full"]
                    organism.scientific_name = row["scientific_name"]
                    organism.common_name = row["common_name"]
                    organism.chinese_name = row["chinese_name"]
                    organism.genus = row["genus"]
                    organism.species = row["species"]
                    organism.family = row["family"]
                    organism.itis_id = row["itis_id"]
                    organism.food_group = row["food_group"]
                    organism.food_subgroup = row["food_subgroup"]
                    organism.food_type = row["food_type"]
                    organism.country = row["country"]
                    organism.tcm_use = row["tcm_use"]
                    organism.definition = row["definition"]
                    organism.foodb_id = row["foodb_id"]
                    organism.save()
                else:
                    organisms_to_create.append(Organism(**row))
            Organism.objects.bulk_create(organisms_to_create)

    def create_preparations(self, file_path):
        data = pandas.read_csv(file_path, header=0, delimiter='\t', quoting=csv.QUOTE_ALL)
        data = data.replace(np.nan, '', regex=True)
        data = data.to_dict('records')
        Preparations.objects.bulk_create([Preparations(**record) for record in data])
        print('success')

    def create_chemical_organism_interactions(self, file_path):
        data = pandas.read_csv(file_path, header=0, delimiter='\t', quoting=csv.QUOTE_ALL)
        data = data.replace(np.nan, '', regex=True)
        data = data.replace('NULL', '', regex=True)
        data = data.to_dict('records')
        cnt = len(data)
        interactions_to_create = []
        for row in data:
            remaining_time(cnt)
            preparation_id = None
            organism_id = None
            if row["rel_type"] == "organism" and row["related_item_id"]:
                organism_id = row["related_item_id"] if row["related_item_id"] > 566 else row["related_item_id"] - 1

            if row["rel_type"] == "preparation" and row["related_item_id"]:
                preparation_id = row["related_item_id"]
            interactions_to_create.append(ChemicalConcentration(
                rel_type=row["rel_type"],
                source_compound_id=int(row["source_compound_id"] or 0),
                source_food_id=int(row["source_food_id"] or 0),
                orig_food_id=row["orig_food_id"],
                orig_food_common_name=row["orig_food_common_name"],
                orig_food_scientific_name=row["orig_food_scientific_name"],
                orig_food_part=row["orig_food_part"],
                orig_compound_id=row["orig_compound_id"],
                orig_compound_name=row["orig_compound_name"],
                conc=float(row["conc"] or 0),
                conc_min=float(row["conc_min"] or 0),
                conc_max=float(row["conc_max"] or 0),
                conc_unit=row["conc_unit"],
                citation=row["citation"],
                citation_type=row["citation_type"],
                orig_method=row["orig_method"],
                orig_unit_expression=row["orig_unit_expression"],
                ref_compound=row["ref_compound"],
                ref_food=row["ref_food"],
                compound_id=int(row["compound_id"] or 0),
                related_item_id=int(row["related_item_id"] or 0),
                preparation_id=preparation_id,
                organism_id=organism_id
            ))
        print("Start bulk creation")
        # with transaction.atomic():
        for interactions in chunks(interactions_to_create, 25000):
            remaining_time(30)
            ChemicalConcentration.objects.bulk_create(interactions)
        print("Finished")

    def handle(self, *args, **options):
        self.create_chemical_organism_interactions(options.get('file'))
