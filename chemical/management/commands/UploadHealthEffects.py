import csv

import pandas
from django.core.management import BaseCommand
from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "Upload health effects - files health_effects.csv"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):

        headers = {
            "id": int, "name": str, "description": str, "chebi_name": str, "chebi_id": str, "created_at": str, "updated_at": str, "creator_id": str,
            "updater_id": str, "chebi_definition": str

        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "id", "name", "description", "chebi_name", "chebi_id", "created_at", "updated_at", "creator_id",
            "updater_id", "chebi_definition"

        ]
        data = data[["id", "name", "description"]]
        df_records = data.to_dict('records')
        print("start model creating")
        model_instances = [HealthEffect(
            file_id=record['id'],
            name=record['name'],
            description=record['description'] if str(record['description']) != 'nan' else ''
        ) for record in df_records]

        HealthEffect.objects.bulk_create(model_instances)
        print("Done")
