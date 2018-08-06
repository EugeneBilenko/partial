import re
from html import parser

import numpy as np


def setup_indiv_dict(desc_d, list_desc, isSA):
    # reads the snp file and creates the word dictionary from this
    words_dict = read_snp_file(list_desc, isSA)

    # reshapes the word dictionary and determines the number of words for each 
    # snp entry
    for rsid, category_id, group_id, sentence_list in words_dict:
        # sets the dictionary entries for each line in the description list
        for index in range(len(sentence_list)):
            if np.size(sentence_list[index]):
                # determines the unique words in the line, and sets their
                # indices within the overall dictionary
                dLU, iU = np.unique(sentence_list[index], return_inverse=True)
                for i in range(len(iU)):
                    # determines the location of the words within the
                    # current line and sets their indices in the dictionary
                    if iU[i] >= 0:
                        ind = np.where(iU == iU[i])
                        cWord = dLU[iU[i]]
                        indT = np.array([[category_id, group_id, index, x] for x in ind[0]])
                        iU[ind] = -1
                        # increments the word counter
                        nCnw = np.size(indT, axis=0)
                        try:
                            desc_d[cWord][rsid]['Count'] += nCnw
                            desc_d[cWord][rsid]['Index'] = np.concatenate(
                                (desc_d[cWord][rsid]['Index'], indT)
                            )
                        except:
                            desc_d[cWord][rsid]['Count'] = nCnw
                            desc_d[cWord][rsid]['Index'] = indT
    # returns the final combined array
    return desc_d


def read_snp_file(list_desc, is_sa):
    """
    opens and reads the entire snp genome data file, and organises the data
    into a sorted dictionary
    """

    # memory allocation
    word_dict = list()

    # other initialisations dependent on the data type
    if is_sa:
        for snp_allele in list_desc:
            # get RSID column
            rsid = snp_allele[3]
            # retrieves the snp/category ID's depending on the dataset
            category_id = snp_allele[4] if snp_allele[4] else -1  # category_id column
            # sets the split description strings
            counter = 1
            for j in [0, 1, 2]:
                words = split_desc_string(rsid, parser.unescape(snp_allele[j]))
                word_dict.append([rsid, category_id, counter, words])
                counter += 1
    else:
        # sets the split description strings for each row in the dataset
        for snp in list_desc:
            words = split_desc_string(snp.rsid, parser.unescape(snp.description_advanced))
            word_dict.append([snp.rsid, 0, 0, words])

    # returns the final dictionary
    return word_dict


def split_desc_string(rsID, descFull):
    """
    splits up the full description line into a list of legitimate words
    for each line
    """

    # strips the html tags from the string
    p = re.compile(r'<.*?>')
    desc = p.sub('', descFull)

    # if there is no information attached to the field, return an empty list
    if 'no info' in desc.lower():
        return {}

    # removes any other special characters
    for char in ['&quot;', '\\t', '(R)', '[R]', '\u2009', '[PMID', '\xa0', rsID, '..']:
        desc = desc.replace(char, ' ')

        # splits up the description by the carriage returns
    desc = desc.replace('\\r', '\\n')
    descL = list(filter(None, desc.split('\\n')))
    for i in range(len(descL)):
        descL[i] = remove_numbers(descL[i])

    # determines if there are more than one item in the string list
    if len(descL) > 1:
        # if so, then remove any empty array
        return list(filter(None, descL))
    else:
        # otherwise, return the description list
        return descL


def remove_numbers(dStr):
    """
    splits the strings and removes any numbers. any strings that are
    contained in bracket (like trait abbreviations) are also kept
    """

    # initialisations
    cStr = [['.'], [';'], ['/'], ['\\']]

    # splits the the string by the non-alpha numeric characters
    dStrS = re.findall(r'[a-zA-Z0-9_\;\.\\\/]+', dStr)

    # removes any
    for i in range(len(dStrS)):
        for cs in cStr:
            if len(cs) == 1:
                if dStrS[i].endswith(cs[0]):
                    dStrS[i] = dStrS[i][:-1]
                elif dStrS[i].startswith(cs[0]):
                    dStrS[i] = dStrS[i][1:]
            else:
                pS, pF = dStrS[i].startswith(cs[0]), dStrS[i].endswith(cs[1])
                if (pS and pF) is False and (pS or pF) is True:
                    if pF:
                        dStrS[i] = dStrS[i][:-1]
                    else:
                        dStrS[i] = dStrS[i][1:]

    # removes any digit strings
    dStrS = [x.lower() for x in dStrS if (det_num_str(x) == False)]
    if len(dStrS) > 1:
        # removes any empty entries from the split string
        return list(filter(None, dStrS))
    else:
        # list is not > 1 in length, so return the array
        return dStrS


def det_num_str(x):
    """
    determines if a string is a full number string
    """

    if len(x) == 1:
        # allow single digits
        return False
    else:
        # otherwise, determine if the string is a number
        try:
            y = eval(x)
            return isinstance(y, float) or isinstance(y, int)
        except:
            return False
