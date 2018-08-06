from django.core.management import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from chemical.models import *
from decodify.helpers import remaining_time


class Command(BaseCommand):
    help = "Make Health Effects slug"

    def handle(self, *args, **options):
        organisms = Organism.objects.all()
        count = organisms.count()
        with transaction.atomic():
            for organism in organisms:
                remaining_time(count)
                # if not organism.slug:
                organism.slug = slugify("-".join([str(organism.id), organism.latin_name]))
                organism.save()
            # effect.slug = slugify(effect.name)
            # effect.save()
