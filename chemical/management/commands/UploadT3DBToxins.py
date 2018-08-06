import csv


import time
import datetime
import math


import pandas
from django.core.management import BaseCommand
from django.db import transaction

from django.db.models import Q

from chemical.models import *


class Command(BaseCommand):
    help = "./manage.py UploadT3DBToxins --file toxins.csv "

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str)

    def create_t3db_instance(self, chemical, data, synonyms):
        ChemicalT3DBData.objects.create(
            chemical=chemical,
            name=data["Name"] if type(data["Name"]) == str else '',
            chemical_class=data["Class"] if type(data["Class"]) == str else '',
            description=data["Description"] if type(data["Description"]) == str else '',
            types=data["Types"] if type(data["Types"]) == str else '',
            synonyms="|".join(synonyms),
            chemical_formula=data["Chemical Formula"] if type(data["Chemical Formula"]) == str else '',
            average_molecular_mass=data["Average Molecular Mass"] if type(data["Average Molecular Mass"]) == str else '',
            monoisotopic_mass=data["Monoisotopic Mass"] if type(data["Monoisotopic Mass"]) == str else '',
            iupac_name=data["IUPAC Name"] if type(data["IUPAC Name"]) == str else '',
            traditional_name=data["Traditional Name"] if type(data["Traditional Name"]) == str else '',
            smiles=data["SMILES"] if type(data["SMILES"]) == str else '',
            kingdom=data["Kingdom"] if type(data["Kingdom"]) == str else '',
            super_class=data["Super Class"] if type(data["Super Class"]) == str else '',
            primary_class=data["Class.1"] if type(data["Class.1"]) == str else '',
            sub_class=data["Sub Class"] if type(data["Sub Class"]) == str else '',
            direct_parent=data["Direct Parent"] if type(data["Direct Parent"]) == str else '',
            alternate_parents=data["Alternate Parents"] if type(data["Alternate Parents"]) == str else '',
            geometric_description=data["Geometric Description"] if type(data["Geometric Description"]) == str else '',
            substituents=data["Substituents"] if type(data["Substituents"]) == str else '',
            descriptors=data["Descriptors"] if type(data["Descriptors"]) == str else '',
            status=data["Status"] if type(data["Status"]) == str else '',
            origin=data["Origin"] if type(data["Origin"]) == str else '',
            cellular_locations=data["Cellular Locations"] if type(data["Cellular Locations"]) == str else '',
            biofluids=data["Biofluids"] if type(data["Biofluids"]) == str else '',
            tissues=data["Tissues"] if type(data["Tissues"]) == str else '',
            pathways=data["Pathways"] if type(data["Pathways"]) == str else '',
            state=data["State"] if type(data["State"]) == str else '',
            appearance=data["Appearance"] if type(data["Appearance"]) == str else '',
            melting_point=data["Melting Point"] if type(data["Melting Point"]) == str else '',
            boiling_point=data["Boiling Point"] if type(data["Boiling Point"]) == str else '',
            solubility=data["Solubility"] if type(data["Solubility"]) == str else '',
            log_p=data["LogP"] if type(data["LogP"]) == str else '',
            route_of_exposure=data["Route of Exposure"] if type(data["Route of Exposure"]) == str else '',
            mechanism_of_toxicity=data["Mechanism of Toxicity"] if type(data["Mechanism of Toxicity"]) == str else '',
            metabolism=data["Metabolism"] if type(data["Metabolism"]) == str else '',
            toxicity=data["Toxicity"] if type(data["Toxicity"]) == str else '',
            lethal_dose=data["Lethal Dose"] if type(data["Lethal Dose"]) == str else '',
            carcinogenicity=data["Carcinogenicity"] if type(data["Carcinogenicity"]) == str else '',
            uses_sources=data["Uses/Sources"] if type(data["Uses/Sources"]) == str else '',
            minimum_risk_level=data["Minimum Risk Level"] if type(data["Minimum Risk Level"]) == str else '',
            health_effects=data["Health Effects"] if type(data["Health Effects"]) == str else '',
            symptoms=data["Symptoms"] if type(data["Symptoms"]) == str else '',
            treatment=data["Treatment"] if type(data["Treatment"]) == str else '',
            wikipedia_link=data["Wikipedia Link"] if type(data["Wikipedia Link"]) == str else '',
            drug_bank_id=data["DrugBank ID"] if type(data["DrugBank ID"]) == str else ''
        )

    def update_existing_chemical(self, chemical, categories, data):
        if str(data["Synonyms"]) == "nan":
            synonyms = []
        else:
            synonyms = [record.replace("\"", "") for record in data["Synonyms"].split(", ")]
        if chemical.synonyms != "":
            existing_synonyms = chemical.synonyms.split("|")
            existing_synonyms.extend(synonyms)
            chemical.synonyms = "|".join(list(set(existing_synonyms)))
        for category in categories:
            chemical.categories.add(category)
        chemical.categories.remove(SubstanceCategory.objects.get(slug="natural-treatments"))
        self.create_t3db_instance(chemical, data, synonyms)
        chemical.t3db_id = data["T3DB ID"] if type(data["T3DB ID"]) == str else ''
        chemical.inchi_identifier = data["InChI Identifier"] if type(data["InChI Identifier"]) == str else ''
        chemical.inchi_key = data["InChI Key"] if type(data["InChI Key"]) == str else ''
        chemical.hmdb_id = data["HMDB ID"] if type(data["HMDB ID"]) == str else ''
        chemical.pubchem_Compound_ID = data["PubChem Compound ID"] if type(data["PubChem Compound ID"]) == str else ''
        chemical.chembl_id = data["ChEMBL ID"] if type(data["ChEMBL ID"]) == str else ''
        chemical.chem_spider_id = data["ChemSpider ID"] if type(data["ChemSpider ID"]) == str else ''
        chemical.kegg_compound_id = data["KEGG Compound ID"] if type(data["KEGG Compound ID"]) == str else ''
        chemical.uni_prot_id = data["UniProt ID"] if type(data["UniProt ID"]) == str else ''
        chemical.omim_id = data["OMIM ID"] if type(data["OMIM ID"]) == str else ''
        chemical.chebi_id = data["ChEBI ID"] if type(data["ChEBI ID"]) == str else ''
        chemical.bio_cyc_id = data["BioCyc ID"] if type(data["BioCyc ID"]) == str else ''
        chemical.ctd_id = data["CTD ID"] if type(data["CTD ID"]) == str else ''
        chemical.stitch_di = data["Stitch ID"] if type(data["Stitch ID"]) == str else ''
        chemical.pdb_id = data["PDB ID"] if type(data["PDB ID"]) == str else ''
        chemical.actor_id = data["ACToR ID"] if type(data["ACToR ID"]) == str else ''
        chemical.save()

    def create_new_chemical(self, categories, data):
        if str(data["Synonyms"]) == "nan":
            synonyms = []
        else:
            synonyms = [record.replace("\"", "") for record in data["Synonyms"].split(", ")]
        chemical = Chemical(
            name=data["Name"],
            cas_rn=data["CAS Number"],
            definition=data["Description"],
            category_associated_from=data["Name"],
            synonyms="|".join(synonyms),
            t3db_id=data["T3DB ID"] if type(data["T3DB ID"]) == str else '',
            inchi_identifier=data["InChI Identifier"] if type(data["InChI Identifier"]) == str else '',
            inchi_key=data["InChI Key"] if type(data["InChI Key"]) == str else '',
            hmdb_id=data["HMDB ID"] if type(data["HMDB ID"]) == str else '',
            pubchem_Compound_ID=data["PubChem Compound ID"] if type(data["PubChem Compound ID"]) == str else '',
            chembl_id=data["ChEMBL ID"] if type(data["ChEMBL ID"]) == str else '',
            chem_spider_id=data["ChemSpider ID"] if type(data["ChemSpider ID"]) == str else '',
            kegg_compound_id=data["KEGG Compound ID"] if type(data["KEGG Compound ID"]) == str else '',
            uni_prot_id=data["UniProt ID"] if type(data["UniProt ID"]) == str else '',
            omim_id=data["OMIM ID"] if type(data["OMIM ID"]) == str else '',
            chebi_id=data["ChEBI ID"] if type(data["ChEBI ID"]) == str else '',
            bio_cyc_id=data["BioCyc ID"] if type(data["BioCyc ID"]) == str else '',
            ctd_id=data["CTD ID"] if type(data["CTD ID"]) == str else '',
            stitch_di=data["Stitch ID"] if type(data["Stitch ID"]) == str else '',
            pdb_id=data["PDB ID"] if type(data["PDB ID"]) == str else '',
            actor_id=data["ACToR ID"] if type(data["ACToR ID"]) == str else '',
        )
        chemical.save()
        for category in categories:
            chemical.categories.add(category)
        self.create_t3db_instance(chemical, data, synonyms)

    def handle(self, *args, **options):

        headers = {
            "T3DB ID": str, "Name": str, "Class": str, "Description": str, "Categories": str, "Types": str,
            "Synonyms": str, "CAS Number": str, "Chemical Formula": str, "Average Molecular Mass": str,
            "Monoisotopic Mass": str, "IUPAC Name": str, "Traditional Name": str, "SMILES": str,
            "InChI Identifier": str, "InChI Key": str, "Kingdom": str, "Super Class": str, "Class1": str,
            "Sub Class": str, "Direct Parent": str, "Alternate Parents": str, "Geometric Description": str,
            "Substituents": str, "Descriptors": str, "Status": str, "Origin": str, "Cellular Locations": str,
            "Biofluids": str, "Tissues": str, "Pathways": str, "State": str, "Appearance": str, "Melting Point": str,
            "Boiling Point": str, "Solubility": str, "LogP": str, "Route of Exposure": str,
            "Mechanism of Toxicity": str, "Metabolism": str, "Toxicity": str, "Lethal Dose": str,
            "Carcinogenicity": str, "Uses/Sources": str, "Minimum Risk Level": str, "Health Effects": str,
            "Symptoms": str, "Treatment": str, "DrugBank ID": str, "HMDB ID": str, "PubChem Compound ID": str,
            "ChEMBL ID": str, "ChemSpider ID": str, "KEGG Compound ID": str, "UniProt ID": str, "OMIM ID": str,
            "ChEBI ID": str, "BioCyc ID": str, "CTD ID": str, "Stitch ID": str, "PDB ID": str, "ACToR ID": str,
            "Wikipedia Link": str, "Creation Date": str, "Update Date": str
        }
        data = pandas.read_csv(options.get('file'), header=0, delimiter=',', quoting=csv.QUOTE_ALL, dtype=headers)
        data = data.dropna(subset=["CAS Number"])
        categories = ", ".join(data.groupby("Categories").groups.keys())
        categories = categories.split(', ')
        categories_unique = list(set(categories))
        categories_clean = [record.replace("\"", "") for record in categories_unique]
        parent_category = SubstanceCategory.objects.get(slug="toxins")
        # substance_categories_instances = [SubstanceCategory.objects.create(
        #     name=record,
        #     slug=slugify(record),
        #     parent=parent_category
        # ) for record in categories_clean]

        i = 0
        count = len(data)
        start_time = time.monotonic()
        last_i = 0
        with transaction.atomic():
            for index, row in data.iterrows():
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
                chemicals = Chemical.objects.filter(cas_rn=row["CAS Number"]).all()
                categories = SubstanceCategory.objects.filter(
                    slug__in=[
                        slugify(record1) for record1 in [
                            record.replace("\"", "") for record in row["Categories"].split(", ")
                            ]
                        ]
                )
                if chemicals.exists():
                    for chemical in chemicals.all():
                        self.update_existing_chemical(chemical, categories, row)
                else:
                    if str(row["Synonyms"]) == "nan":
                        synonyms = []
                    else:
                        synonyms = [record.replace("\"", "") for record in row["Synonyms"].split(", ")]
                    query = Q(name__iexact=row["Name"]) | Q(synonyms__iexact=row["Name"]) | Q(
                        synonyms__istartswith=row["Name"] + "|") | Q(synonyms__iendswith="|" + row["Name"]) | Q(
                        synonyms__icontains="|" + row["Name"] + "|")
                    for synonym in synonyms:
                        query |= Q(name__iexact=synonym) | Q(synonyms__iexact=synonym) | Q(
                            synonyms__istartswith=synonym + "|") | Q(synonyms__iendswith="|" + synonym) | Q(
                            synonyms__icontains="|" + synonym + "|")
                    chemicals = Chemical.objects.filter(query)
                    if chemicals.exists():
                        for chemical in chemicals.all():
                            self.update_existing_chemical(chemical, categories, row)
                    else:
                        self.create_new_chemical(categories, row)


