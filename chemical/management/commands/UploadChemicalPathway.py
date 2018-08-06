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
    ./manage.py UploadChemicalPathway --file ~/Downloads/CTD_chem_pathways_enriched.csv
    """

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):

        go_type = options.get('go_type')
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL)
        data = data.replace(np.nan, '', regex=True)
        with transaction.atomic():
            existing_chemicals = dict(
                Chemical.objects.filter(chemical_number__isnull=False).values_list("chemical_number", "id"))
            data = data.to_dict('records')
            count = len(data)
            interactions_to_save = []
            for row in data:
                remaining_time(count)
                chemical = existing_chemicals.get("MESH:" + row["ChemicalID"])
                if chemical:
                    interactions_to_save.append(
                        ChemicalPathway(
                            chemical_id=chemical,
                            cas_rn=row.get("CasRN"),
                            pathway_name=row.get("PathwayName"),
                            pathway_id=row.get("PathwayID"),
                            p_value=row.get("PValue"),
                            corrected_p_value=row.get("CorrectedPValue"),
                            target_match_qty=row.get("TargetMatchQty"),
                            target_total_qty=row.get("TargetTotalQty"),
                            background_match_qty=row.get("BackgroundMatchQty"),
                            background_total_qty=row.get("BackgroundTotalQty")
                        )
                    )
            ChemicalPathway.objects.bulk_create(interactions_to_save)

