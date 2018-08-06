from django.core.management import BaseCommand
from django.utils.text import slugify

from chemical.models import *
from decodify.helpers import remaining_time


class Command(BaseCommand):
    help = "Make Health Effects slug"

    def handle(self, *args, **options):
        healtheffects = HealthEffect.objects.all()
        count = HealthEffect.objects.count()

        for effect in healtheffects:
            remaining_time(count)
            effect.slug = slugify(effect.name)
            effect.save()
