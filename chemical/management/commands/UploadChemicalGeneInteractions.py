import csv

import pandas
from django.core.management import BaseCommand

from chemical.models import *


class Command(BaseCommand):
    help = "Upload Chemical-Gene interactions"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def handle(self, *args, **options):
        headers = {
            "ChemicalName": str, "ChemicalID": str, "CasRN": str, "GeneSymbol": str, "GeneID": str,
            "GeneForms": str, "Organism": str, "OrganismID": str, "Interaction": str, "InteractionActions": str,
            "PubMedIDs": str

        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data.columns = [
            "chemical_name", "chemcal_id", "cas_rn", "gene_symbol", "gene_id", "gene_forms", "organism",
            "organism_id", "interaction", "interaction_actions", "pub_med_ids"
        ]

        data = data[["chemical_name", "gene_symbol", "organism", "interaction", "interaction_actions", "pub_med_ids"]]

        data.gene_symbol = data.gene_symbol.str.lower().str.strip()

        genes = Gene.objects.all()

        gene_df = pandas.DataFrame(list(genes.values("name", "description_advanced", "description_simple",
                                                     "fix_advanced", "fix_simple", "creator", "transcription_factors",
                                                     "symbol", "full_name", "synonyms")))
        gene_df.columns = [
            "name", "description_advanced", "description_simple", "fix_advanced", "fix_simple", "creator",
            "transcription_factors", "symbol", "full_name", "synonyms"
        ]

        gene_df = gene_df[["symbol"]]
        match_genes = data.gene_symbol.isin(gene_df.symbol)
        match_genes = data[match_genes == True]
        match_grouped = match_genes.groupby(['gene_symbol', 'chemical_name'])
        match_grouped_with_count = match_grouped.first().join(match_grouped.count(), rsuffix="_r")
        # import pdb
        i = 0
        rows_count = match_grouped_with_count.count()

        for index, row in match_grouped_with_count.iterrows():
            i += 1
            print("%s of %s" % (i, rows_count,))
            gene_symbol, chemical_name = index
            gene = Gene.objects.filter(symbol=gene_symbol).first()
            chemical = Chemical.objects.filter(name=chemical_name).first()
            organism = Organism.objects.filter(latin_name=row.organism).first()
            row['interaction_amount'] = row[
                ['organism_r', 'interaction_r', 'interaction_actions_r', 'pub_med_ids_r']
            ].max()
            interaction_actions = row.interaction_actions.split("|")
            if not gene or not chemical:
                continue
            # pdb.set_trace()
            interaction = ChemicalGeneInteraction.objects.create(
                gene=gene,
                chemical=chemical,
                organism=organism,
                interaction=row.interaction,
                pub_med_ids=row.pub_med_ids,
                amount=row.interaction_amount
            )
            if interaction_actions:
                for interaction_actions_divided in interaction_actions:
                    interaction_actions_divided = interaction_actions_divided.split('^')
                    interaction_action = ChemicalGeneInteractionAction.objects.create(
                        interaction=interaction,
                        interaction_type=ChemicalGeneInteractionType.objects.filter(
                            name=interaction_actions_divided[1]
                        ).first(),
                        action=interaction_actions_divided[0]
                    )


