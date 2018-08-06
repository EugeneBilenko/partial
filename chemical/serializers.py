from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import strip_tags
from django.template.defaultfilters import truncatechars


class ChemicalInteractsGenesSerializer(DjangoJSONEncoder):
    def default(self, page):
        if page.has_next():
            has_next = True
            next_page_number = page.next_page_number()
        else:
            next_page_number = page.paginator.num_pages
            has_next = False
        result = {'paginator':
                    {
                    'has_next': has_next,
                    'next_page_number': next_page_number,
                    },
                  'object_list': []
                 }
        if page:
            for item in page.object_list:
                try:
                    organism = item.organism.english_name
                    pubmed = [pubmed for pubmed in item.pub_med_ids.split('|')]
                except:
                    organism = ''
                    pubmed = ''

        # 'gene': item['gene__name'],
        # 'summary': truncatechars(strip_tags(item['gene__description_simple'])
                    # .replace('[R]', '').replace('(R)', ''), 300),
        # 'interaction': ", ".join(["%s %s" % (action['f1'].capitalize(), action['f2'],)
                    # for action in item['actions_merged']]),

                result['object_list'].append({
                    'gene': item.gene.name,
                    'summary': truncatechars(strip_tags(item.gene.description_simple)
                                             .replace('[R]', '').replace('(R)', ''), 300),
                    'interaction': '{} {}'.format(item.actions.first().action.capitalize(),
                                                  item.actions.first().interaction_type.name),
                    'organism': organism,
                    'pubmed': pubmed,
                })
        return result


class ChemicalInteractsDiseaseSerializer(DjangoJSONEncoder):
    def default(self, page):
        if page.has_next():
            has_next = True
            next_page_number = page.next_page_number()
        else:
            next_page_number = page.paginator.num_pages
            has_next = False
        result = {
            'paginator': {
                'has_next': has_next,
                'next_page_number': next_page_number,
            },
            'object_list': []
        }
        if page:
            for item in page.object_list:
                result['object_list'].append({
                    'disease': item.get("disease__name"),
                    'disease_slug': item.get("disease__slug"),
                    'inference_score': item.get("max_inference_score"),
                    'pub_med_ids': item.get("pubmed_ids", []),
                    'genes': item.get("genes", []),
                })
        return result
