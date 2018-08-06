import time
import datetime
import math

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q, Count
from django.db.models.functions import Lower

from chemical.models import *
from decodify.helpers import remaining_time


class Command(BaseCommand):
    help = "Add chemical category - files natural.txt, popular_drugs.txt"

    def merge_text_field(self, text1, text2):
        if text1 and not text2:
            return text1
        if text2 and not text1:
            return text2
        if text1 and text2:
            return "\n".join([text1, text2])
        else:
            return ""

    def merge_id_field(self, id1, id2):
        if id1 and not id2:
            return id1
        if id2 and not id1:
            return id2
        if id1 and id2:
            return "|".join([id1, id2])
        else:
            return ""

    def merge(self, to_chemical, from_chemical):
        # to_chemical.display_as = me
        to_chemical.definition = self.merge_text_field(to_chemical.definition, from_chemical.definition)
        to_chemical.synonyms = self.merge_text_field(to_chemical.synonyms, from_chemical.synonyms)
        to_chemical.associated_from = self.merge_text_field(to_chemical.associated_from, from_chemical.associated_from)
        # to_chemical.recommendation_status
        to_chemical.category_associated_from = self.merge_text_field(to_chemical.category_associated_from, from_chemical.category_associated_from)
        # to_chemical.categories
        to_chemical.chemical_number = self.merge_id_field(to_chemical.chemical_number, from_chemical.chemical_number)
        to_chemical.parent_chemical_numbers = self.merge_id_field(to_chemical.parent_chemical_numbers, from_chemical.parent_chemical_numbers)
        # to_chemical.health_effects = merge_id_field
        to_chemical.cas_rn = self.merge_id_field(to_chemical.cas_rn, from_chemical.cas_rn)
        to_chemical.drug_bank_ids = self.merge_id_field(to_chemical.drug_bank_ids, from_chemical.drug_bank_ids)
        to_chemical.foodb_id = self.merge_id_field(to_chemical.foodb_id, from_chemical.foodb_id)
        to_chemical.name_scientific = self.merge_text_field(to_chemical.name_scientific, from_chemical.name_scientific)
        to_chemical.itis_id = self.merge_id_field(to_chemical.itis_id, from_chemical.itis_id)
        to_chemical.wikipedia_id = self.merge_id_field(to_chemical.wikipedia_id, from_chemical.wikipedia_id)
        # to_chemical.picture_file_name = me
        # to_chemical.picture_content_type = me
        # to_chemical.picture_file_size = me
        to_chemical.t3db_id = self.merge_id_field(to_chemical.t3db_id, from_chemical.t3db_id)
        to_chemical.inchi_identifier = self.merge_id_field(to_chemical.inchi_identifier, from_chemical.inchi_identifier)
        to_chemical.inchi_key = self.merge_id_field(to_chemical.inchi_key, from_chemical.inchi_key)
        to_chemical.hmdb_id = self.merge_id_field(to_chemical.hmdb_id, from_chemical.hmdb_id)
        to_chemical.pubchem_Compound_ID = self.merge_id_field(to_chemical.pubchem_Compound_ID, from_chemical.pubchem_Compound_ID)
        to_chemical.chembl_id = self.merge_id_field(to_chemical.chembl_id, from_chemical.chembl_id)
        to_chemical.chem_spider_id = self.merge_id_field(to_chemical.chem_spider_id, from_chemical.chem_spider_id)
        to_chemical.kegg_compound_id = self.merge_id_field(to_chemical.kegg_compound_id, from_chemical.kegg_compound_id)
        to_chemical.uni_prot_id = self.merge_id_field(to_chemical.uni_prot_id, from_chemical.uni_prot_id)
        to_chemical.omim_id = self.merge_id_field(to_chemical.omim_id, from_chemical.omim_id)
        to_chemical.chebi_id = self.merge_id_field(to_chemical.chebi_id, from_chemical.chebi_id)
        to_chemical.bio_cyc_id = self.merge_id_field(to_chemical.bio_cyc_id, from_chemical.bio_cyc_id)
        to_chemical.ctd_id = self.merge_id_field(to_chemical.ctd_id, from_chemical.ctd_id)
        to_chemical.stitch_di = self.merge_id_field(to_chemical.stitch_di, from_chemical.stitch_di)
        to_chemical.pdb_id = self.merge_id_field(to_chemical.pdb_id, from_chemical.pdb_id)
        to_chemical.actor_id = self.merge_id_field(to_chemical.actor_id, from_chemical.actor_id)
        # to_chemical.affiliate_us
        # to_chemical.affiliate_international
        # to_chemical.selfhacked_link
        t3db = from_chemical.t3db_data.all()
        if t3db.exists():
            for data in t3db:
                data.chemical = to_chemical
                data.save()
        concentrations = from_chemical.chemicalconcentration_set.all()
        if concentrations.exists():
            for concentration in concentrations:
                concentration.chemical.set([to_chemical])
        categories = from_chemical.categories.all()
        if categories.exists():
            for category in categories:
                to_chemical.categories.add(category)
        health_effects = from_chemical.health_effects.all()
        if health_effects.exists():
            for health_effect in health_effects:
                to_chemical.health_effects.add(health_effect)
        from_chemical.categories.set([])
        from_chemical.health_effects.set([])
        to_chemical.merging_status = "merged_to"
        from_chemical.merging_status = "merged_from"
        to_chemical.save()
        from_chemical.save()

    def handle(self, *args, **options):
        chemical_names = Chemical.objects.annotate(name_lower=Lower("name")).values("name_lower").annotate(cnt=Count("name_lower")).order_by("-cnt")
        filtered = []
        for pair in chemical_names:
            if pair["cnt"] > 1:
                filtered.append(pair["name_lower"])
        chemicals = Chemical.objects.annotate(name_lower=Lower("name")).filter(name_lower__in=filtered).order_by("name_lower")
        merging_chemical = None
        remaining_cnt = chemicals.count()
        name_lower = ""
        cnt = 0
        first_cnt = 0
        last_cnt = 0
        with transaction.atomic():
            for chemical in chemicals:
                remaining_time(remaining_cnt)
                if name_lower == chemical.name_lower:
                    # print(merging_chemical.id, chemical.id)
                    if merging_chemical.id < chemical.id:
                        self.merge(merging_chemical, chemical)
                        first_cnt += 1
                    else:
                        self.merge(chemical, merging_chemical)
                        last_cnt += 1
                    cnt += 1
                else:
                    name_lower = chemical.name_lower
                    merging_chemical = chemical
        print("Successfully merged %s pairs of chemicals" % (cnt,))
