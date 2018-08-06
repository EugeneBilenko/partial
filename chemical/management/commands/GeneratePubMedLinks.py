import csv

import pandas
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from chemical.models import *
from decodify.helpers import remaining_time


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, l.count(), n):
        yield l[i:i + n]


class Command(BaseCommand):
    help = "Make Chemcial slug"

    def handle(self, *args, **options):
        existing_interactions = ChemicalGeneInteraction.objects.all()
        count = existing_interactions.count()
        with transaction.atomic():
            for interactions in chunks(existing_interactions, 10000):
                for interaction in interactions:
                    remaining_time(count)
                    if interaction.pub_med_ids:
                        ids = interaction.pub_med_ids.split("|")
                        refs = ["https://www.ncbi.nlm.nih.gov/pubmed/" + record for record in ids]
                        refs = "\n".join(refs)
                        interaction.references = refs
                        interaction.save()


