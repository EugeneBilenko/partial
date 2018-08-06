from collections import defaultdict

from genome.tasks import app


def match_single_snp(disease_count, snp_list, study_dict):
    """
    Determines the single snp data matches (from the dictionary, snp_list)
    within the gwas sorted dictionary, study_dict
    :param disease_count:
    :param snp_list:
    :param study_dict:
    :return: the storage dictionary
    """

    # loops through each snp within the gwas dataset determining if there is a
    # match within the snp data file

    for rsid, genotype, pk in snp_list:
        # if there is a match, then determine the unique genotype
        # characters (plus the missing allele matching character). also
        # determine if the genotype is homozygous by the string length
        unique_gc = ''.join(set(genotype)) + "X"
        is_homo = len(unique_gc) == 2
        snp_study_item = study_dict.get(rsid)
        if snp_study_item:
            # searches for all the genotype characters within the matching
            # gwas dictionary field. if there is a match, then append the
            # data to the corresponding disease/trait dictionary key
            for gC in unique_gc:
                if gC in snp_study_item:
                    for dt in snp_study_item[gC]:
                        # retrieves the dictionary field and adds the homozygous field
                        gwasM = dict(snp_study_item[gC][dt])
                        # the match type: 1 - heterozygous, 2 - homozygous, 3 - missing allele
                        gwasM['mType'] = 3 if gC == "X" else 2 - int(is_homo)
                        gwasM['rsid'] = rsid
                        gwasM['gType'] = gC
                        gwasM['userSnpId'] = pk
                        # appends the match to the disease/trait dictionary
                        disease_count[dt]["Match"].append(gwasM)

    return disease_count


def rec_dd():
    """
    default dictionary recursion function
    :return: the default dictionary
    """
    return defaultdict(rec_dd)


def create_gwas_dict(query):
    gwas_dict = rec_dd()
    study = query.values(
        'id',
        'snp__rsid',
        'snp_id',
        'diseasestrait_text',
        'parent_term',
        'risk_allele',
        'p_value_mlog',
        'odds_ratio',
        'ci_text',
        'risk_allele_frequency'
    )
    for i in study:
        if not i['risk_allele']:
            i['risk_allele'] = 'X'

        if not i['ci_text'].strip():
            # case is no confidence interval type was given
            c_type = None
        elif 'increase' in i['ci_text'] or 'decrease' in i['ci_text']:
            # case is a beta coefficient
            c_type = 'BETA'
        else:
            # otherwise, case is an odds ratio
            c_type = 'OR'

        gwas_dict[i['snp__rsid']][i['risk_allele']][i['diseasestrait_text']] = {
            'studyId': i['id'],
            'snpId': i['snp_id'],
            'mlpVal': i['p_value_mlog'],
            'cInt': i['odds_ratio'],
            'cType': c_type,
            'cIntT': i['ci_text'],
            'rFreq': i['risk_allele_frequency']
        }
    return gwas_dict


def check_task_active_scheduled(task_name):
    """
    function check if passed task exists in scheduled or active queue in Celery
    :param task_name: name of the task registered in Celery
    :return: tuple of two (bool, str): first param is status in queues, second is log
    """
    i = app.control.inspect()
    active_scheduled = False
    logs = ''
    tasks_scheduled = i.scheduled()
    tasks_active = i.active()

    if type(tasks_active) is dict:
        for key in tasks_active.keys():
            for task in tasks_active[key]:
                logs += 'active: {0}<br>'.format(task.get('name'))
                if task.get('name') == task_name:
                    active_scheduled = True

    if not active_scheduled and type(tasks_scheduled) is dict:
        for key in tasks_scheduled.keys():
            for task in tasks_scheduled[key]:
                logs += 'scheduled: {0}<br>'.format(task.get('request', {}).get('name'))
                if task.get('request', {}).get('name') == task_name:
                    active_scheduled = True

    return active_scheduled, logs
