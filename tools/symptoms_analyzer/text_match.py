import re

import numpy as np
import scipy.spatial.distance as dist
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from tools.aggregate_conclusions.calc_scores import calc_study_score
from tools.common_func import rec_dd
from django.conf import settings

def split_user_input_string(uInput):
    """
        splits the user input string, uInput, into its unique words
    """

    # performs the initial split on the user input string
    uWords = np.array(re.split('\W+', uInput))

    # determines the unique user input words (ensures they are all lower case)
    _, idx = np.unique(uWords, return_index=True)
    uWords = uWords[np.sort(idx)]
    for i in range(len(uWords)):
        uWords[i] = uWords[i].lower()

    # returns the word list
    return uWords


def det_best_user_match(uInput, descD, N=10):
    """
    determines the best snp matching word from the user input string,
    uInput, from the description dictionary, descD.
    """

    # initialisations        
    sWords = np.array(list(descD.keys()))
    uWords = split_user_input_string(uInput)

    # memory allocation
    fuzzyWord = [None] * len(uWords)
    fuzzyScore = [None] * len(uWords)
    snpMatch = [None] * len(uWords)

    # determines the length of the search words, and resorts by length
    nLen = np.array([len(x) for x in sWords])
    iSort = np.argsort(-nLen)
    sWordsM, nLen = sWords[iSort], nLen[iSort]

    # splits the words by the white-spaces and searches each word    
    for i in range(len(uWords)):
        # determines the top N matches for the current word
        fuzzyMatch = det_top_matches([uWords[i]], sWordsM, nLen, N, 0.20)

        # stores all the match scores/words
        fuzzyWord[i] = list(fuzzyMatch.Match)
        fuzzyScore[i] = list(fuzzyMatch.Score)

        # stores all SNP matches (for each fuzzy match word found above)
        snpMatch[i] = [None] * N
        for j in range(N):
            snpMatch[i][j] = set(descD[fuzzyWord[i][j]].keys())

    # determines the overall matches from each of the fuzzy-word matches
    return det_final_matches(descD, snpMatch, fuzzyWord, fuzzyScore, N)


def det_final_matches(descD, snpMatch, fuzzyWord, fuzzyScore, N):
    """
    determines the final fuzzy word matches from the user input
    """

    # memory allocation and initialisations
    nWord, fMatch = len(snpMatch), []
    dStr = ['N/A', 'Minor', 'Major', 'Hetero']

    # determines the full word matches over all word combinations
    for i in range(N ** nWord):
        # loop initialisations
        indNw = setIndexArray(i, N, nWord)
        isOK = True
        snpGrpNw = snpMatch[0][indNw[0]]

        # determines the intersecting SNP's over all words
        for j in range(1, nWord):
            # determines the intersecting SNP's for the current word
            snpGrpNw = (snpGrpNw & snpMatch[j][indNw[j]])
            if not len(snpGrpNw):
                # if no intersecting SNP's are found, exit the loop
                isOK = False
                break

        # if there are                 
        if isOK:
            # sets the fuzzy match words/scores for the current combination
            fWord = get_list_values(fuzzyWord, indNw)
            fScore = get_list_values(fuzzyScore, indNw)

            for snp in snpGrpNw:
                dInfo = det_snp_word_dist(descD, snp, fWord, fScore)

                # appends the new row to the dictionary                    
                if len(dInfo):
                    if not len(fMatch):
                        fMatch = dInfo
                    else:
                        fMatch = np.concatenate((fMatch, dInfo))

    # reshapes the

    nMatch = np.size(fMatch, axis=0)
    if nMatch > 0:
        # if there are valid matches, then reshape the array and sort the 
        # values so that they are ordered by match score and then distance
        if nWord == 1:
            indS = np.lexsort((fMatch[:, 1], fMatch[:, 0], -fMatch[:, 4].astype(int), -fMatch[:, 3].astype(float)))
        else:
            indS = np.lexsort((fMatch[:, 1], fMatch[:, 0], fMatch[:, 4].astype(float), -fMatch[:, 3].astype(float)))

        # converts the genotype index to the full string
        fMatch = fMatch[indS, :]
        for i in range(nMatch):
            fMatch[i, 2] = dStr[int(fMatch[i, 2])]

        # removes multiple entries
        isOK = [False] * len(fMatch)
        _, indU = np.unique(fMatch[:, 0:2], axis=0, return_inverse=True)

        # only include the top matching entry in the final list
        for i in indU:
            ii = np.where(indU == i)
            isOK[ii[0][0]] = True

        # returns the sorted array (with unique entries only)
        return fMatch[isOK, :]
    else:
        # returns the empty array
        return fMatch


def det_user_snp_match(uInput, uMatch, snpUserD, snpD, gwasD):
    """
    determines the matches between the user's search query against the
    results from their SNP datafile
    """

    # determines the unique snps from the search query matches
    snpU = np.unique(uMatch[:, 0])
    uSnpD = rec_dd()
    nSNP = len(snpU)
    sKey = list(snpD.keys())
    sTol = 99

    # splits the user input string into the constituent words
    nWords = len(split_user_input_string(uInput))

    # memory allocation and other initialisations
    uSnpD = [None] * nSNP

    # lambda function types
    uFcn = lambda x: np.array([y[x] for y in uSnpD])
    gFcn = {
        'Min': lambda x, y, z: int((x == 'Minor') and (y == z)),
        'Maj': lambda x, y, z: int((x == 'Major') and (y == z))
    }

    # loops through all the snp determining if there are any matches between
    # the user's snp file and that from the user query matches
    for i in range(nSNP):
        # determines the query matches belonging to the current snp
        ii = np.where(uMatch[:, 0] == snpU[i])[0]

        # sets the base rank score
        mScore = float(uMatch[ii[0], 3])
        rScore0 = 89 * float(mScore > sTol) + mScore / 100
        #        rScore0 = float(uMatch[ii[0],3])

        # further ranking increment if inter-word distance = 0 (phrases only)
        if nWords > 1:
            wDist = float(uMatch[ii[0], 4])
            if (wDist < nWords):
                rScore0 = 10 * (1 - wDist / 10000) + rScore0
        else:
            rScore0 = rScore0 + 10

        # initalises the user snp match dictionary fields          
        uSnpD[i] = set_match_fields(uMatch[ii, :], snpD[snpU[i]])
        uSnpD[i]['rScore'] = rScore0

        # determines if current snp is within the user's snp file
        if snpU[i] in snpUserD:
            # if so, retrieve the user's corresponding snp genotype
            snpG = snpUserD[snpU[i]]['gene']
            uSnpD[i]['hasSnp'] = True
            uSnpD[i]['ugType'] = snpG
            isHomo = len(set(snpG)) == 1

            # retrieves the minor/major allele keys
            if snpU[i] in sKey:
                minAl = snpD[snpU[i]]['Minor']
                majAl = snpD[snpU[i]]['Major']
            else:
                minAl = '?'
                majAl = '?'

            # sets the matches fields based on the user/database snp details 
            for j in range(len(ii)):
                isInf = (uMatch[ii[j], 4] == 'inf')
                if int(uMatch[ii[j], 1]) <= 0 or isInf:
                    # penalises the score for infinite word distance                    
                    if j == 0:
                        uSnpD[i]['rScore'] = uSnpD[i]['rScore'] - 1000 * float(isInf)
                else:
                    # set the match type based on the user's data and the
                    # user query match results
                    if uMatch[ii[j], 2] == 'Hetero':
                        # case is a heterzygous query match
                        mType = int(not isHomo)
                    elif isHomo:
                        # else, if the genotype is homozygous then determine
                        # if the minor/major allele matches
                        mType = (gFcn['Min'](uMatch[ii[j], 2], snpG[0], minAl) +
                                 gFcn['Maj'](uMatch[ii[j], 2], snpG[0], majAl))
                    else:
                        # otherwise, there are no overall matches
                        mType = 0

                    # appends the new information to the list                    
                    uSnpD[i]['mType'][j] = 1 + int(mType > 0)
                    uSnpD[i]['rScore'] = uSnpD[i]['rScore'] + (1 + 9 * int(mType > 0))

                    if mType > 0:
                        if uSnpD[i]['rsID'] in gwasD:
                            # calculates the gwas scores (if not calculated)
                            if (not uSnpD[i]['hasGWAS']):
                                uSnpD[i]['gScore'] = calc_snp_gwas_scores(gwasD, uSnpD[i])

                            # sets the other flags
                            uSnpD[i]['hasGWAS'] = True
                            uSnpD[i]['mType'][j] = 3 + (len(uSnpD[i]['gScore']) > 1)

            # if there are any 
            uSnpD[i]['rScore'] = (uSnpD[i]['rScore'] +
                                  200 * int(uSnpD[i]['hasGWAS']) +
                                  500 * (len(uSnpD[i]['gScore']) - 1))
        else:
            # sets empty results if no match
            uSnpD[i]['hasSnp'] = False
            uSnpD[i]['rScore'] = uSnpD[i]['rScore'] - 2000 + 10 * len(uSnpD[i]['mType'])

    # sorts the match list by the rank scores and then rsID strings
    indS = np.lexsort((uFcn('rsID'), -uFcn('Imp'), uFcn('wDist'), -uFcn('rScore')))
    AA = np.array(uSnpD)

    # returns the sorted list
    return AA[indS].tolist()


def set_match_fields(uMatch, snpD):
    """
    sets the query match fields for the snp dictionary, uSnpD
    """

    # initialisations
    nMatch, uSnpD = np.size(uMatch, axis=0), rec_dd()

    # sets the minor allele
    sDMin = snpD['Minor'] if snpD['Minor'] else '?'

    # sets the major allele       
    sDMax = snpD['Major'] if snpD['Major'] else '?'

    # sets the default dictionary field values
    uSnpD['rsID'], uSnpD['rScore'], uSnpD['ugType'] = uMatch[0, 0], 0, '??'
    uSnpD['mType'] = np.matlib.repmat(0, nMatch, 1)
    uSnpD['gwScore'], uSnpD['hasGWAS'] = None, False

    # set values from the query match
    uSnpD['wMatch'] = uMatch[0, -1]
    uSnpD['cID'] = uMatch[:, 1]
    uSnpD['mgType'] = uMatch[:, 2]
    uSnpD['mScore'] = uMatch[0, 3]
    uSnpD['wDist'] = uMatch[0, 4]

    # sets the values from the snp dictionary
    uSnpD['Gene'] = snpD['Gene']
    uSnpD['Imp'] = snpD['Imp']
    uSnpD['mmAll'] = sDMin + '-' + sDMax

    # returns the dictionary
    return uSnpD


def det_snp_word_dist(descD, snp, fWord, fScore):
    """
    determines the relative location of the search words within the
    SNP descriptions.
    """

    # memory allocation and initialisations
    nWord, ind = len(fScore), [None] * len(fScore)
    fSP, nCol = round(100 * np.prod(fScore) / (100 ** nWord), 1), 6

    # determines the union sets of the categories/group that contain the 
    # matching words
    for i in range(nWord):
        ind[i] = descD[fWord[i]][snp]['Index']
        if not i:
            indC = set(ind[i][:, 0])
            indG = set(ind[i][:, 1])
        else:
            indC = indC or set(ind[i][:, 0])
            indG = indG or set(ind[i][:, 1])

    # memory allocation
    indC = list(indC)
    indG = list(indG)
    nC = len(indC)
    nG = len(indG)
    isOK = np.array([False] * (nC * nG))
    dInfo = np.array([None] * (nC * nG))

    # for each category/group, then 
    for i in range(nC):
        for j in range(nG):
            # determines the indices which match the category/group combination
            indGC = get_matching_indices(ind, indC[i], indG[j], nWord)

            # if there are valid lines to search, then calculate the minimum
            # distance between all word combinations within the current
            # category/group 
            nLine = len(indGC)
            if nLine > 0:
                # initialisations
                k = i * nG + j

                # sets the count/avg distance based on the word count
                if nWord == 1:
                    # if only one word, then set the match count
                    mDist = nLine
                else:
                    # if more than one word calculate the minimum distance                
                    mDist = float('inf')
                    indR, indL = get_line_indices(list(ind), indGC, nWord)
                    for ii in indL:
                        mDist = min(mDist, calc_word_dist(indR, ii, nWord))

                # updates the distance information entry
                isOK[k] = True
                dInfo[k] = [snp, indC[i], indG[j], fSP, mDist, ' '.join(fWord)]

    if any(isOK):
        # if there are valid matches, then return the match information
        dInfo = sum(dInfo[isOK], [])
        return np.reshape(dInfo, (int(len(dInfo) / nCol), nCol))
    else:
        # if no valid matches, then return an empty list
        return []


def calc_word_dist(ind, indL, nWord):
    """
        calculates the average distance between the words on a given line
    """

    # memory allocation
    indW, dSum = [None] * nWord, 0
    cdist, npmin, npabs = dist.cdist, np.min, np.abs

    # retrieves the indices of the words corresponding to the matching line
    for i in range(nWord):
        ind0 = np.array(ind[i][(ind[i][:, 2] == indL), 3])
        indW[i] = np.reshape(ind0, (len(ind0), 1))

    for j in range(1, nWord):
        dSum += (npabs(npmin(cdist(indW[j - 1], indW[j]))) - 1)

    # returns the average distance
    return dSum / (nWord - 1)


def det_top_matches(wordC, wordS, nLen, nWord=1, pWord=0.2):
    """
    determines the top nWord matches of the candidate words in the list,
    wordC, against the search word list wordS. the search word list is
    sorted by word length (which is given in the list, nLen). other
    function inputs are whether a single query is being made (i.e., if
    a user is submitting a query from the search words) and the
    proportional word length that is to be searched (i.e., +/- pWord
    time the length of the search word(s))
    """

    # memory allocation
    N = len(wordC)
    wM, wS = [None] * N, [None] * N

    # determines the candidate matches against the search list   
    for i in range(N):
        wM[i], wS[i] = calc_word_matches(wordS, nLen, wordC[i], nWord, pWord)

        # case is for a single query, so
    nS = np.size(wM, axis=0)
    wM, wS = np.reshape(wM, (nWord * nS, 1)), np.reshape(wS, (nWord * nS, 1))
    wMU = np.unique(wM)

    # calculates the average score and sorts in descending order
    wSU = np.array([np.sum(wS[np.where(wM == x)]) / nS for x in wMU])
    iSort = np.argsort(-wSU)[:nWord]

    # combines the matches/scores into a single array    
    return np.rec.fromarrays((wMU[iSort], wSU[iSort]), names=('Match', 'Score'))


def calc_word_matches(wordSD, nLen, wordC, nWord, pWord):
    """
    calculates the nWord matches of the candidate word, wordC, from the
    sorted search word list, wordSD, which have lengths nLen. the value
    pWord is the proportional search word length (i.e., searching only
    words that have length +/- that of the candidate word)
    """

    # sets the fuzzy search values
    #    eFcn = {0: fuzz.ratio,
    #            1: fuzz.partial_ratio,
    #            2: fuzz.partial_token_set_ratio,
    #            3: fuzz.partial_token_sort_ratio}
    eFcn = {0: fuzz.ratio}

    # initialisations and memory allocation
    wMatch, wScore, nScore, iOfs = [], [], len(eFcn.keys()), 0

    # local funcion handles
    appendM, appendS, repmat = wMatch.append, wScore.append, np.matlib.repmat
    extract, where, reshape = process.extract, np.where, np.reshape

    # determines the lower/upper word length limits
    nLenC = len(wordC)
    dN = max([1, round(pWord * nLenC)])
    nLo, nHi = (nLenC - dN), (nLenC + dN)

    # determines which search words are within the length limits
    isOK = [((x >= nLo) and (x <= nHi)) for x in nLen]
    if any(isOK):
        # reduces the search array to the valid words
        wordSD = wordSD[np.where(isOK)]

        # determines if there is an exact match
        totMatch = where(wordSD == wordC)
        if np.size(totMatch):
            # if so, then set the parameters based on the number of words
            # that are being searched            
            if nWord == 1:
                # if only one word, then return the candidate word and 100%
                wM = repmat(wordC, 1, nScore)
                wS = repmat('100', 1, nScore)
                return wM, wS
            else:
                # otherwise, set the word search offset to 1 and remove
                # the exact match from the search list
                iOfs, wordSD = 1, np.delete(wordSD, totMatch[0])

        # if there are valid words, then                       
        for i in range(nScore):
            # determines the fuzzy match and reshapes the result    
            A = extract(wordC, wordSD, limit=(nWord - iOfs), scorer=eFcn[i])
            A = reshape([list(t) for t in A], ((nWord - iOfs), 2))

            # retrieves the new matching words/scores
            wSnw = [min(99, int(x)) for x in A[:, 1]]
            wMnw = A[:, 0].tolist()
            if iOfs == 1:
                # if there is a perfect match, then append them to the 
                # front of the matching word/score lists
                wMnw, wSnw = ([wordC] + wMnw), ([100] + wSnw)

            # appends the matching words/scores to the overall arrays
            appendM(wMnw)
            appendS(wSnw)
    else:
        # no valid words, so return the 
        return repmat('', nWord, nScore), repmat(0, nWord, nScore)

    # returns the word match/scores
    return reshape(wMatch, (nScore, nWord)).T, reshape(wScore, (nScore, nWord)).T


def get_line_indices(ind, indGC, nWord):
    """
    determines the indices of the lines that match between words
    """

    # sets the reduced index array
    for i in range(nWord):
        ind[i] = ind[i][indGC[i], :]

    # determines the lines that correspond to the current group
    indL = set(ind[0][:, 2])
    if len(indL) > 0:
        # if there are other valid lines in the group, search the other 
        # word to determine the matching lines
        for j in range(1, nWord):
            # determines the intersection of the line indices between
            # the current line index set and the new word
            indL = indL & set(ind[j][:, 2])
            if not len(indL):
                # if there is no intersection, then exit the loop
                return [], []
    else:
        # otherwise, return empty lists
        return [], []

    # returns the reduces/line index lists
    return ind, list(indL)


def get_matching_indices(ind, indC, indG, nWord):
    """
    determines the word indices that match the current category/group
    """

    # initialisations
    lAnd, nArr, indGC = np.logical_and, np.array, [None] * nWord
    intFcn = lambda x, y: lAnd(nArr(x == indC), nArr(y == indG))

    # if there are other valid lines in the group, search the other 
    # word to determine the matching lines
    for j in range(0, nWord):
        # determines the intersection of the line indices between
        # the current line index set and the new word
        isM = intFcn(ind[j][:, 0], ind[j][:, 1])
        if any(isM):
            A = np.array(range(len(isM)))
            indGC[j] = A[np.where(isM)].tolist()
        else:
            # if there is no matches, then exit the loop
            return []

    # returns the line indices
    return indGC


def get_list_values(A, ind):
    """
    retrieves the list values given the index array, ind
    """

    # memory allocation
    B = [None] * len(ind)

    # sets the values for each index item
    for i in range(len(ind)):
        B[i] = A[i][ind[i]]

    # returns the list
    return B


def calc_snp_gwas_scores(gwasD, uSnpD):
    # intialisations and memory allocation
    uGType, gScore = ''.join(set(uSnpD['ugType'])) + 'X', []
    gw = dict(gwasD[uSnpD['rsID']])
    isHetero = len(uGType) == 3

    # retrieves the gwas dictionary entry for the current snp
    for gK in list(gw.keys()):
        # determines if the allele is located in the user's genotype string
        if gK in uGType:
            # is so, copy the dictionary and set the risk-allele
            for gTr in list(gw[gK].keys()):
                # creates a copy of the local dictionary
                gwTr = dict(gw[gK][gTr])

                # sets the genotype match score
                if gK == 'X':
                    # case is for a missing allele
                    gwTr['mType'] = 3
                else:
                    # case is for the homo/heterozygous genotype
                    gwTr['mType'] = 1 + isHetero

                # calculates the new score and appends it to the overall list
                nwScore = calc_study_score(gwTr)
                gScore.append([gTr, round(100 * nwScore)])

    # returns the gwas score list
    if len(gScore) > 0:
        # if scores calculated, then reshape the array
        gScore = np.reshape(sum(gScore, []), (len(gScore), 2))
        indS = np.argsort(-gScore[:, 1].astype(float))
        return gScore[indS, :]
    else:
        # no scores, so return empty list
        return gScore


def setIndexArray(n, b, nW):
    # memory allocation
    digits, i = [0] * nW, 0

    # if the number is zero, then exit the function
    if n == 0:
        return digits

    # keep looping until there are no more values
    while n:
        digits[i] = int(n % b)
        n //= b
        i += 1

    # returns the array
    return digits[::-1]
