import csv


import time
import datetime
import math


import pandas
from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import F

from chemical.models import *


class Command(BaseCommand):
    help = "./manage.py AssignFooDBCompounds --compounds-file compounds.csv --synonyms-file compound_synonyms.csv"

    def add_arguments(self, parser):
        parser.add_argument('--compounds-file', type=str)
        parser.add_argument('--synonyms-file', type=str)

    def prepare_synonyms_dictionary(self, file):
        # Get and parse FooDB synonyms file
        synonyms_headers = {
            "id": str, "synonym": str, "synonym_source": str, "created_at": str, "updated_at": str, "source_id": str,
            "source_type": str
        }
        synonyms_data = pandas.read_csv(file, header=0, delimiter=',', quoting=csv.QUOTE_ALL,
                                        dtype=synonyms_headers)
        synonyms_data.columns = [
            "id", "synonym", "synonym_source", "created_at", "updated_at", "source_id", "source_type"
        ]
        synonyms_data = synonyms_data[["synonym", "source_id"]]
        synonyms_data_grouped = synonyms_data.groupby("source_id")
        synonyms_data_keys = synonyms_data_grouped.groups.keys()

        response = dict()
        for key in synonyms_data_keys:
            response[key] = synonyms_data_grouped.get_group(key).synonym
        del synonyms_data
        del synonyms_data_grouped
        del synonyms_data_keys
        return response

    def handle(self, *args, compounds_file=None, **options):
        category = SubstanceCategory.objects.get(slug='natural-treatments')

        # Get and parse FooDB compounds file
        compound_headers = {
            "id": str, "legacy_id": str, "type": str, "public_id": str, "name": str, "export": str, "state": str,
            "annotation_quality": str, "description": str, "cas_number": str, "melting_point": str,
            "protein_formula": str, "protein_weight": str, "experimental_solubility": str, "experimental_logp": str,
            "hydrophobicity": str, "isoelectric_point": str, "metabolism": str, "kegg_compound_id": str,
            "pubchem_compound_id": str, "pubchem_substance_id": str, "chebi_id": str, "het_id": str, "uniprot_id": str,
            "uniprot_name": str, "genbank_id": str, "wikipedia_id": str, "synthesis_citations": str,
            "general_citations": str, "comments": str, "protein_structure_file_name": str,
            "protein_structure_content_type": str, "protein_structure_file_size": str,
            "protein_structure_updated_at": str, "msds_file_name": str, "msds_content_type": str, "msds_file_size": str,
            "msds_updated_at": str, "creator_id": str, "updater_id": str, "created_at": str, "updated_at": str,
            "phenolexplorer_id": str, "dfc_id": str, "hmdb_id": str, "duke_id": str, "drugbank_id": str, "bigg_id": str,
            "eafus_id": str, "knapsack_id": str, "boiling_point": str, "boiling_point_reference": str, "charge": str,
            "charge_reference": str, "density": str, "density_reference": str, "optical_rotation": str,
            "optical_rotation_reference": str, "percent_composition": str, "percent_composition_reference": str,
            "physical_description": str, "physical_description_reference": str, "refractive_index": str,
            "refractive_index_reference": str, "uv_index": str, "uv_index_reference": str, "experimental_pka": str,
            "experimental_pka_reference": str, "experimental_solubility_reference": str,
            "experimental_logp_reference": str, "hydrophobicity_reference": str, "isoelectric_point_reference": str,
            "melting_point_reference": str, "moldb_alogps_logp": str, "moldb_logp": str, "moldb_alogps_logs": str,
            "moldb_smiles": str, "moldb_pka": str, "moldb_formula": str, "moldb_average_mass": str, "moldb_inchi": str,
            "moldb_mono_mass": str, "moldb_inchikey": str, "moldb_alogps_solubility": str, "moldb_id": str,
            "moldb_iupac": str, "structure_source": str, "duplicate_id": str, "old_dfc_id": str, "dfc_name": str,
            "compound_source": str, "flavornet_id": str, "goodscent_id": str, "superscent_id": str,
            "phenolexplorer_metabolite_id": str, "kingdom": str, "superklass": str, "klass": str, "subklass": str,
            "direct_parent": str, "molecular_framework": str, "chembl_id": str, "chemspider_id": str,
            "meta_cyc_id": str, "foodcomex": str, "phytohub_id": str
        }
        compound_data = pandas.read_csv(compounds_file, header=0, delimiter=',', quoting=csv.QUOTE_ALL,
                                        dtype=compound_headers)
        compound_data.columns = [
            "id", "legacy_id", "type", "public_id", "name", "export", "state", "annotation_quality", "description",
            "cas_number", "melting_point", "protein_formula", "protein_weight", "experimental_solubility",
            "experimental_logp", "hydrophobicity", "isoelectric_point", "metabolism", "kegg_compound_id",
            "pubchem_compound_id", "pubchem_substance_id", "chebi_id", "het_id", "uniprot_id", "uniprot_name",
            "genbank_id", "wikipedia_id", "synthesis_citations", "general_citations", "comments",
            "protein_structure_file_name", "protein_structure_content_type", "protein_structure_file_size",
            "protein_structure_updated_at", "msds_file_name", "msds_content_type", "msds_file_size", "msds_updated_at",
            "creator_id", "updater_id", "created_at", "updated_at", "phenolexplorer_id", "dfc_id", "hmdb_id",
            "duke_id", "drugbank_id", "bigg_id", "eafus_id", "knapsack_id", "boiling_point", "boiling_point_reference",
            "charge", "charge_reference", "density", "density_reference", "optical_rotation",
            "optical_rotation_reference", "percent_composition", "percent_composition_reference",
            "physical_description", "physical_description_reference", "refractive_index", "refractive_index_reference",
            "uv_index", "uv_index_reference", "experimental_pka", "experimental_pka_reference",
            "experimental_solubility_reference", "experimental_logp_reference", "hydrophobicity_reference",
            "isoelectric_point_reference", "melting_point_reference", "moldb_alogps_logp", "moldb_logp",
            "moldb_alogps_logs", "moldb_smiles", "moldb_pka", "moldb_formula", "moldb_average_mass",
            "moldb_inchi", "moldb_mono_mass", "moldb_inchikey", "moldb_alogps_solubility", "moldb_id", "moldb_iupac",
            "structure_source", "duplicate_id", "old_dfc_id", "dfc_name", "compound_source", "flavornet_id",
            "goodscent_id", "superscent_id", "phenolexplorer_metabolite_id", "kingdom", "superklass", "klass",
            "subklass", "direct_parent", "molecular_framework", "chembl_id", "chemspider_id", "meta_cyc_id",
            "foodcomex", "phytohub_id"
        ]
        compound_data = compound_data[["id", "name", "description", "cas_number"]]
        compound_data = compound_data.dropna(subset=['cas_number'])

        synonyms_data = self.prepare_synonyms_dictionary(options.get("synonyms_file"))
        i = 0
        count = len(compound_data)
        start_time = time.monotonic()
        last_i = 0
        chemicals_to_save = []
        for index, row in compound_data.iterrows():
            i += 1
            if time.monotonic() - start_time >= 1:
                start_time = time.monotonic()
                i_per_sec = i - last_i
                last_i = i
                time_remaining = (count - i) / i_per_sec
                time_remaining = datetime.timedelta(seconds=math.floor(time_remaining))
                print("Time left %s" % time_remaining, end=" ")
                print("%s rows per second" % i_per_sec, end=" ")
                print("%s/%s" % (i, count,))
            chemicals = Chemical.objects.filter(cas_rn=row["cas_number"])
            synonyms = synonyms_data[row["id"]] if row["id"] in synonyms_data else []
            if chemicals.exists():
                for chemical in chemicals.all():
                    if row["description"] != "":
                        if chemical.definition != "":
                            chemical.definition = str(chemical.definition) + "\n" + str(row["description"])
                        else:
                            chemical.definition = row["description"]
                    if chemical.category_associated_from:
                        chemical.category_associated_from = ", ".join(
                            [row["name"], chemical.category_associated_from])
                    else:
                        chemical.category_associated_from = row["name"]
                    if chemical.synonyms != "":
                        existing_synonyms = chemical.synonyms.split("|")
                        existing_synonyms.extend(synonyms)
                        chemical.synonyms = "|".join(list(set(existing_synonyms)))
                    else:
                        chemical.synonyms = synonyms
                    chemical.foodb_id = row["id"]
                    chemicals_to_save.append(chemical)
            else:
                chemical = Chemical(
                    name=row["name"],
                    cas_rn=row["cas_number"],
                    definition=row["description"],
                    category_associated_from=row["name"],
                    foodb_id=row["id"],
                    synonyms="|".join(synonyms)
                )
                chemicals_to_save.append(chemical)

        with transaction.atomic():
            for chemical in chemicals_to_save:
                chemical.save()
                chemical.categories.add(category)
                print("success")
