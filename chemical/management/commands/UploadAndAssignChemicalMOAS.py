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
from genome.models import Synonym


class Command(BaseCommand):
    help = "./manage.py UploadAndAssignChemicalMOAS --file moas.csv"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):

        headers = {
            "Toxin T3DB ID": str,
            "Toxin Name": str,
            "Target BioDB ID": str,
            "Target Name": str,
            "Target UniProt ID": str,
            "Mechanism of Action": str,
            "References": str,
            "Creation Date": str,
            "Update Date": str
        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data = data.replace(np.nan, '', regex=True)
        mechanisms = data.groupby("Mechanism of Action").groups

        targets = data[["Target BioDB ID", "Target Name", "Target UniProt ID"]].drop_duplicates()
        targets.columns = ["biodb_id", "name", "uniprot_id"]

        references = data[["References"]].drop_duplicates()
        references.columns = ["description"]

        moas_data = data.groupby("Toxin T3DB ID").groups

        with transaction.atomic():
            ChemicalMechanismOfAction.objects.bulk_create(
                [ChemicalMechanismOfAction(description=record) for record in mechanisms.keys()]
            )
            Target.objects.bulk_create(
                [Target(**record) for record in targets.to_dict('records')]
            )
            Reference.objects.bulk_create(
                [Reference(**record) for record in references.to_dict('records')]
            )
            i = 1
            count = len(data)
            start_time = time.monotonic()
            last_i = 0
            for key, indexes in moas_data.items():
                if time.monotonic() - start_time >= 1:
                    start_time = time.monotonic()
                    i_per_sec = i - last_i
                    last_i = i
                    time_remaining = (count - i) / i_per_sec
                    time_remaining = datetime.timedelta(seconds=math.floor(time_remaining))
                    print("Time left %s" % time_remaining, end=" ")
                    print("%s rows per second" % i_per_sec, end=" ")
                    print("%s/%s" % (i, count,))
                chemical = Chemical.objects.filter(t3db_id=key).first()
                if chemical:
                    for mech, indexes1 in data.ix[indexes].groupby("Mechanism of Action").groups.items():
                        mechanism = ChemicalMechanismOfAction.objects.filter(description=mech).first()
                        ref_array = []
                        target_array = []
                        for index, row in data.ix[indexes1].iterrows():
                            i += 1
                            ref_array.append(Reference.objects.filter(description=row["References"]).first())
                            target_array.append(Target.objects.filter(biodb_id=row["Target BioDB ID"]).first())
                        moas = ChemicalTargetMechanism.objects.create(
                            chemical=chemical,
                            mechanism_of_action=mechanism
                        )
                        moas.target.add(*target_array)
                        moas.reference.add(*ref_array)

