import numpy
from django.core.urlresolvers import reverse

# unit mapping dictionaries
uFcn = {
    'NE': 'mg', 'aTE': 'mg', 'mg/100 g': 'mg', 'mg/100 ml': 'mg', 'IU': 'ug', 'RE': 'ug', 'ug_DFE': 'ug', 'ug_RAE': 'ug'
}
uMap = {
    'g': {
        'mg': lambda x: '{0:.1f}'.format(float(x) / 1000),
        'mg/100 g': lambda x: '{0:.1f}'.format(float(x) / 1000),
        'mg/100 ml': lambda x: '{0:.1f}'.format(float(x) / 1000),
        'g': lambda x: x,
        'ppm': lambda x: '{0:.1f}'.format(float(x) / 10000),
        'ug': lambda x: '{0:.1f}'.format(float(x) / 1000000)
    },
    'mg': {
        'NE': lambda x: x,
        'aTE': lambda x: x,
        'g': lambda x: '{0:.1f}'.format(float(x) / 1000),
        'mg': lambda x: x,
        'mg/100 g': lambda x: x,
        'mg/100 ml': lambda x: x,
        'ppm': lambda x: '{0:.1f}'.format(float(x) / 10),
        'ug': lambda x: str(float(x) * 1000)
    },
    'ug': {
        'IU': lambda x: str(float(x) * 40),
        'RE': lambda x: x,
        'g': lambda x: str(float(x) * 1000000),
        'mg': lambda x: str(float(x) * 1000),
        'mg/100 g': lambda x: str(float(x) * 1000),
        'mg/100 ml': lambda x: str(float(x) * 1000),
        'ppm': lambda x: str(float(x) * 100),
        'ug': lambda x: x,
        'ug_DFE': lambda x: x,
        'ug_RAE': lambda x: x
    },
    'kJ': {
        'kcal': lambda x: str(float(x) * 4.184),
        'kJ': lambda x: x
    }
}


# COMPOUND SEARCH FUNCTIONS
def det_match_results(chemical, sType=None, limit=20):
    """
    for the django model query set, qS, determine the top N compounds
    by concentration.
    :param chemical: Chemical model object
    :param sType: String, accept: None, 'preparation', 'organism'
    :param N: Integer
    :return: the compound unit dictionary
    """

    # determines the query set for the current compound. excludes any
    # entries where there are no units/unified concentration values
    criteria = {
        'unified_concentration__isnull': False,
        'conc_unit__isnull': False
    }

    if sType:
        criteria['rel_type'] = sType

    cc_list = chemical.concentrations.filter(
        **criteria
    ).values_list(
        'rel_type', 'unified_concentration', 'conc', 'conc_max',
        'conc_unit', 'orig_food_common_name', 'orig_food_part',
        'ref_food', 'organism__slug'
    )

    cc_count = len(cc_list)

    # return none if empty queryset executed
    if not cc_count:
        return []

    matchD = list()
    cc_array = numpy.array(cc_list)

    # retrieves the concentration unit/unified concentration strings
    rel_type = cc_array[:, 0]
    unified_concentration = cc_array[:, 1]
    conc = cc_array[:, 2]
    conc_max = cc_array[:, 3]
    conc_unit = cc_array[:, 4]
    orig_food_common_name = cc_array[:, 5]
    orig_food_part = cc_array[:, 6]
    ref_food = cc_array[:, 7]
    slug_url = cc_array[:, 8]

    # determines the unique units for the current compound
    cu_unique_keys, indU, Nc = numpy.unique(conc_unit, return_inverse=True, return_counts=True)

    substance_form = get_substance_form(conc_unit)

    # determines the most likely unit
    units = det_likely_units(cu_unique_keys, unified_concentration, Nc, uFcn)

    # determines if the all of the units matches the specifed units
    # if not, then map the non-matching units to the specified units
    isMatch = cu_unique_keys == units

    for j in range(len(isMatch)):
        if not isMatch[j]:
            # applies the unit mapping to the specified units
            uMapNw = uMap[units][cu_unique_keys[j]]

            # calculates the concentration conversion (based on type)
            for k in numpy.where(indU == j)[0]:
                if cu_unique_keys[j] == 'ppm':
                    # case is for units in ppm
                    conc[k] = uMapNw(conc_max[k])
                else:
                    # case is for other unit types
                    conc[k] = uMapNw(conc[k])

    # determines the top N-group indices
    gInd = group_search_results(ref_food, conc, limit)

    # sets the search results into the overall match dictionary
    for iNw in gInd:
        # sets the sub-dictionary into the overall dictionary
        matchD.append({
            'substance': ref_food[iNw[0]],
            'substance_url': reverse('chemical:organism', args=(slug_url[iNw[0]],)) if slug_url[iNw[0]] else None,
            'unit': units,
            'concentration_range': [conc[iNw][-1], conc[iNw][0]],
            'concentration': conc[iNw].tolist(),
            'food_name': orig_food_common_name[iNw].tolist(),
            'food_part': orig_food_part[iNw].tolist(),
            'type': rel_type[iNw].tolist(),
            'substance_form': substance_form[iNw].tolist(),
        })

    return matchD


def group_search_results(ref_food, Conc, limit):
    """
    groups search results by their reference food into a max of N groups
    """

    # initialisations
    nFood = len(Conc)
    rList = []
    ind = []
    nM = 0

    # determines the sorted indices (by descending concentration)
    iSort = numpy.argsort(-Conc.astype(float))
    rFood = ref_food[iSort]

    # keep loop until either A) the correct number of categories have been
    # determined, or B) there are no more foods to search
    for i in range(nFood):
        if rFood[i] in rList:
            # if the reference food is in the existing list, then append the
            # sorted index to that index array element
            indF = rList.index(rFood[i])
            ind[indF] = numpy.append(ind[indF], iSort[i])
        elif nM == limit:
            # if the number of matches equals the limit, then exit
            return ind
        else:
            # otherwise, create a new element for the unique match
            ind.append(numpy.array([iSort[i]]))
            rList.append(rFood[i])
            nM += 1

    # returns the index array
    return ind


# COMPOUND UNIT FUNCTIONS
def det_likely_units(cu_unique_keys, unified_concentration, Ncount, uFcn):
    """
    Determines the most likely units for the given compound.
    """

    # initialisations
    uStr = ['g', 'mg', 'ug', 'kJ']
    isOK = numpy.where([(x in uStr) for x in cu_unique_keys])[0]

    # determines if there are any matches with the specified units
    nOK = len(isOK)
    if nOK == 0:
        # if no matching units, then determine the other likely units
        if len(cu_unique_keys) == 1 and cu_unique_keys[0] == 'ppm':
            ppmMax = max(numpy.array(unified_concentration, dtype=float))
            if ppmMax < 100:
                return 'ug'
            elif ppmMax < 100000:
                return 'mg'
            else:
                return 'g'
        else:
            indFcn = [i for i in range(len(cu_unique_keys)) if (cu_unique_keys[i] in uFcn)]
            return uFcn[cu_unique_keys[indFcn[0]]]
    elif nOK > 1:
        # more than one match, so return the unit with the highest count
        return cu_unique_keys[isOK[numpy.argmax(Ncount[isOK])]]
    else:
        # otherwise, return the only matching unit
        return cu_unique_keys[isOK[0]]


# MISCELLANEOUS FUNCTIONS
def get_substance_form(conc_unit):
    """
    Sets up an array flagging whether the substance is a food or drink
    """

    # memory allocation
    substance_form = numpy.array(['Food'] * len(conc_unit), dtype='U5')

    # if there are any drinks, reset the substance form string to drink
    if 'mg/100 ml' in conc_unit:
        for i in numpy.where(conc_unit == 'mg/100 ml'):
            substance_form[i] = 'Drink'

    # returns the substance form array
    return substance_form
