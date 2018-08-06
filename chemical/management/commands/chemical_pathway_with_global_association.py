from django.core.management import BaseCommand
from django.db import transaction

from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import Pathway


class Command(BaseCommand):
    help = "Make Chemcial slug"

    def handle(self, *args, **options):
        chemical_pathways = ChemicalPathway.objects.all()
        pathways = dict(Pathway.objects.values_list("pathway_id", "id"))
        count = chemical_pathways.count()
        with transaction.atomic():
            for chemical_pathway in chemical_pathways:
                remaining_time(count)
                related_pathway_id = pathways.get(chemical_pathway.pathway_id)
                if related_pathway_id:
                    chemical_pathway.related_pathway_id = related_pathway_id
                    chemical_pathway.save()
        print("Done")
