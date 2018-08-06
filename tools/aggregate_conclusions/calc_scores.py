import functools
import math
import operator

import numpy as np

# sets the boltzmann function parameters dictionary
BOLTZMANN_PARAMS = {
    'OR': {'A': 0.552, 'k1': 91.394, 'h1': 1.844, 'k2': 4.045, 'h2': 1.217},  # p-value weighting parameters
    'pVal': {'k': 1.982, 'h': 1.207},  # odds ratio weighting parameters
    'rFreq': {'A0': 0.10, 'n': 0.33},  # risk allele weighting parameters
    'Gene': {1: 1.00, 2: 0.50, 3: 0.25},  # genotype match weighting parameters
    'cType': 'Mean'
}

# sets up the score calculation function dictionary
SCORE_FUNCTIONS = {
    'Max': lambda x: 100.0 * np.max(x),  # takes max of all scores
    'Mean': lambda x: 100.0 * np.mean(x),  # takes mean(avg) of all scores
    'Median': lambda x: 100.0 * np.median(x)  # takes median of all scores
}


def calc_agg_scores(dtD):
    """
    calculates the aggregate scores for all traits/diseases
    :param dtD:
    :return:
    """

    # calculates the aggregate scores for each trait
    for dt in dtD:
        dtD[dt]['Score'] = calc_trait_score(dtD[dt]['Match'])

    # returns the disease/trait match
    return dtD


def calc_trait_score(dtM):
    """
    calculates the aggregate score for an individual trait/disease
    :param dtM:
    :return: the overall trait score
    """

    if not len(dtM):
        return 0.0

    # memory allocation
    score = [0.] * len(dtM)
    i = 0

    # calculates the scores for each study
    for dt in dtM:
        score[i] = calc_study_score(dt)
        dt['ScoreM'] = round(100.0 * score[i], 2)
        i += 1

    score_func = SCORE_FUNCTIONS[BOLTZMANN_PARAMS['cType']]

    return round(score_func(score), 2)


def calc_study_score(dtM):
    """
    calculates the aggregate score for an individual GWAS
    """

    # memory allocation and initialisations
    p_fix = 1.0
    power = [1.] * 4
    cType = dtM['cType']
    mType = dtM['mType']

    # sets the genotype match weighting
    if isinstance(mType, int):
        # case is for a single snp match
        power[0] = calc_single_snp_weight(mType)
    else:
        # case is for a multiple snp match
        power[0] = calc_multi_snp_weight(mType)

    # calculates the odds ratio/beta score weighting
    if not dtM['cInt']:
        # case is no confidence interval score was recorded
        power[1] = p_fix
    elif cType == 'OR':
        # case is the odds ratio was specified
        power[1] = calc_double_exp(np.log10(float(dtM['cInt'])))
    elif cType == 'Beta':
        # case is the beta score was specified
        power[1] = p_fix
    else:
        # case is no confidence interval was specified
        power[1] = p_fix

    # calculates the minus-log p-value weighting
    power[2] = calc_single_exp(float(dtM['mlpVal']))

    # calculates the risk allele frequency
    if dtM['rFreq'] is None or type(dtM['rFreq']) is str:
        # case is the risk-frequency is not reported, so set a fixed value
        power[3] = p_fix
    else:
        # otherwise, calculate the risk-frequency weighting
        rFreq = min(1.0, dtM['rFreq'])
        rfP = BOLTZMANN_PARAMS['rFreq']
        power[3] = rfP['A0'] + (1 - rfP['A0']) * (1 - rFreq ** rfP['n'])

    # returns the final study score value
    return functools.reduce(operator.mul, power)


def calc_single_exp(X):
    """
    calculates the single exponential weighting transfer function
    """

    # returns the single exponential value
    return 1.0 - math.exp(-BOLTZMANN_PARAMS['pVal']['k'] * X ** BOLTZMANN_PARAMS['pVal']['h'])


def calc_single_snp_weight(mType):
    """
    returns the weighting score for a single snp study
    """

    # returns the weighting value
    return BOLTZMANN_PARAMS['Gene'][int(mType)]


def calc_multi_snp_weight(mType):
    """
    returns the weighting score for a multi snp study
    """

    # memory allocation
    power = [0.] * len(mType)

    # sets the allele weights for all 
    for i in range(len(mType)):
        power[i] = calc_single_snp_weight(mType[i])

    # returns the final score weight
    return np.prod(power)


def calc_double_exp(X):
    """
    calculates the single exponential weighting transfer function
    """

    # returns the single exponential value
    A = BOLTZMANN_PARAMS['OR']['A']
    k1 = BOLTZMANN_PARAMS['OR']['k1']
    k2 = BOLTZMANN_PARAMS['OR']['k2']
    h1 = BOLTZMANN_PARAMS['OR']['h1']
    h2 = BOLTZMANN_PARAMS['OR']['h2']
    return 1.0 - (A * math.exp(-k1 * X ** h1) + (1.0 - A) * math.exp(-k2 * X ** h2))
