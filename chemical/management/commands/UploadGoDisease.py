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


class Command(BaseCommand):
    help = """
    ./manage.py UploadGoDisease --file ~/Downloads/CTD_Disease-GO_biological_process_associations.csv --go-type 'biological-process'
    ./manage.py UploadGoDisease --file ~/Downloads/CTD_Disease-GO_molecular_function_associations.csv --go-type 'molecular-function'
    ./manage.py UploadGoDisease --file ~/Downloads/CTD_Disease-GO_cellular_component_associations.csv --go-type 'cellular-component'

    """

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)
        parser.add_argument('--go-type', type=str)

    def handle(self, *args, **options):

        go_type = options.get('go_type')
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL)
        data = data.replace(np.nan, '', regex=True)
        go_data = data[["GOName", "GOID"]].sort("GOID").drop_duplicates().to_dict('records')
        # import pdb
        # pdb.set_trace()
        with transaction.atomic():
            GeneOntology.objects.bulk_create([GeneOntology(
                go_id=record.get("GOID"),
                go_name=record.get("GOName"),
                type=go_type
            ) for record in go_data])
            go_objects = dict(GeneOntology.objects.values_list("go_id", "id"))
            disease_objects = dict(DiseaseTrait.objects.filter(ctd_id__isnull=False).values_list("ctd_id", "id"))
            data = data.to_dict('records')
            count = len(data)
            interactions_to_save = []
            for row in data:
                remaining_time(count)
                go = go_objects.get(row["GOID"])
                disease = disease_objects.get("MESH:"+row["DiseaseID"])
                if go and disease:
                    interactions_to_save.append(
                        DiseaseGOAssociations(
                            disease_id=disease,
                            gene_ontology_id=go,
                            inference_gene=row["InferenceGeneSymbols"],
                            inference_gene_qty=row["InferenceGeneQty"]
                        )
                    )
            DiseaseGOAssociations.objects.bulk_create(interactions_to_save)

