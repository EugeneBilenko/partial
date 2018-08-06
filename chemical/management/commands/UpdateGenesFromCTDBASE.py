import csv

import pandas
from django.core.management import BaseCommand


import time
import datetime
import math

from django.db import transaction
import numpy as np
from chemical.models import *
from decodify.helpers import remaining_time
from genome.models import Synonym


class Command(BaseCommand):
    help = "Update genes - add gene symbol, synonyms, fullname"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        headers = {
            "GeneSymbol": str, "GeneName": str, "GeneID": str, "AltGeneIDs": str, "Synonyms": str,
            "BioGRIDIDs": str, "PharmGKBIDs": str, "UniprotIDs": str

        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "gene_symbol", "gene_name", "gene_id", "alt_gene_id", "synonyms", "bio_grid_ids", "pharm_gkbid_ids",
            "uniprot_ids"
        ]
        data = data.replace(np.nan, '', regex=True)
        # data = data[["gene_symbol", "gene_name", "synonyms"]]
        existing_genes = Gene.objects.all()
        count = existing_genes.count()
        data.gene_symbol = data.gene_symbol.str.lower().str.strip()
        with transaction.atomic():
            for gene in existing_genes:
                remaining_time(count)
                row = data.ix[data.gene_symbol == gene.symbol]
                if row.index.size == 0:
                    row = data.synonyms.str.contains(gene.name)
                    row = row[row == True]
                    if row.index.size != 0:
                        row = data.ix[row.index]
                    else:
                        continue
                # synonyms_to_add = []
                # if row.synonyms[row.index[0]] and str(row.synonyms[row.index[0]]) != 'nan':
                #     for synonym in row.synonyms[row.index[0]].split("|"):
                #         synonyms_to_add.append(Synonym.objects.get_or_create(name=synonym)[0])
                # synonyms_to_add.append(Synonym.objects.get_or_create(name=gene.name)[0])
                # gene.synonyms.add(*synonyms_to_add)
                gene.ctd_id = row.gene_id[row.index[0]]
                gene.ctd_alt_gene_ids = row.alt_gene_id[row.index[0]]
                gene.ctd_bio_grid_ids = row.bio_grid_ids[row.index[0]]
                gene.ctd_pharm_gkb_ids = row.pharm_gkbid_ids[row.index[0]]
                gene.ctd_uniprot_ids = row.uniprot_ids[row.index[0]]
                # gene.full_name = row.gene_name[row.index[0]]
                # gene.symbol = row.gene_symbol[row.index[0]]
                gene.save()
                #
