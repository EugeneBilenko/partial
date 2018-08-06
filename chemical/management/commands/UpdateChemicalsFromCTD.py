import csv

import pandas
from django.core.management import BaseCommand
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        headers = {
            "ChemicalName": str, "ChemicalID": str, "CasRN": str, "Definition": str, "TreeNumbers": str,
            "ParentTreeNumbers": str, "Synonyms": str, "DrugBankIDs": str

        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "chemical_name", "chemical_id", "cas_rn", "definition", "tree_numbers", "parent_tree_numbers",
            "synonyms", "drug_bank_ids"
        ]

        rows_count = data.count()
        i = 0
        for index, item in data.iterrows():
            i += 1
            print("%s of %s" % (i, rows_count,))
            Chemical.objects.filter(chemical_number=item.chemical_id).update(
                cas_rn=item.cas_rn,
                definition=item.definition,
                drug_bank_ids=item.drug_bank_ids
            )
