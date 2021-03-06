#!/usr/bin/env python3
"""
Insight Data Engineering coding challenge:

Compute running percentile of repeat donations to 
US political campaigns based on FEC data.
"""

import sys
import csv
from collections import namedtuple
import math
import time
import datetime

def main(recFilePath = './itcont.txt', 
         pctFilePath = './percentile.txt',
         outFilePath = './repeat_donors.txt', 
         logFilePath = './log.txt', 
         logVerbose  = False, 
         strictRepeat = False
        ):
    """Carry-out the main routine, return the wall clock time passed."""

    t0wall = time.time()
    with open(pctFilePath, 'r') as pctFile, \
         open(recFilePath, 'r') as recFile, \
         open(outFilePath, 'w') as outFile, \
         open(logFilePath, 'w') as logFile:
         percentile = int(pctFile.readline().rstrip())
         divLine = '-'*79 + '\n'
         print('Processing. See process logs in {:s}'.format(logFilePath))
         logFile.write('Opened \n' 
                       '{0:s} \n' 
                       'to output the repeat donation stats in the '
                       'following format: \n'
                       '| Receipent | Donors'' Zip Code| Donation Year' 
                       '| {1:d} Percentile Amount '
                       '| Total Repeat Donation Amount' 
                       '| Number of Repeat Donations \n'
                       'The requested percentile value is read from: \n'
                       '{2:s} \n' 
                       .format(outFilePath, percentile, pctFilePath)
                      )
         records = csv.reader(recFile, delimiter='|')
         selectedColumns = ['CMTE_ID',
                            'NAME',
                            'ZIP_CODE',
                            'TRANSACTION_DT',
                            'TRANSACTION_AMT',
                            'OTHER_ID'
                           ]
         colID, nAllColumns = getColumnIDs(selectedColumns)
         donors = {}  # Maps a donorID to (years a donation made)
         repeatDonations = {}  # Maps a groupID to [donation amounts]
         repeatSum = {}  # Maps a groupID to sum([donation amounts])
         nRec = 0
         nValid = 0
         nInvalid = 0
         msg = ('Started processing records present in: \n'
                '{:s} \n'
                'See the end of this log file for a process summary. \n'
                + divLine
               ).format(recFilePath)
         logFile.write(msg)
         if not logVerbose:
             msg = ('Use command line option -v '
                    'to see verbose output here.\n'
                   )
             logFile.write(msg)
         #This is the loop where the line-by-line record inspection happens: 
         for rec in records:
             nRec += 1
             aRecord = moldRecord(rec, nRec, selectedColumns, colID,
                                  nAllColumns, logFile, logVerbose
                                 )
             if aRecord is not None and aRecord != 0:
                 if isRepeat(aRecord, donors, strictRepeat):
                     amt = aRecord.amount
                     repeatDonations.setdefault(aRecord.groupID, []
                                               ).append(amt)
                     # Also update and pass a running sum since recomputing
                     # the sum afresh would be an unnecessar O(nList) work.
                     repeatSum[aRecord.groupID] = \
                              repeatSum.setdefault(aRecord.groupID, 0) + amt
                     emitStats(aRecord, 
                               repeatDonations[aRecord.groupID],
                               repeatSum[aRecord.groupID],
                               percentile, outFile, logFile
                              )
                 if aRecord.donorID not in donors:
                     #Using a set() because it has O(1) look-up time.
                     donors[aRecord.donorID] = set() 
                 donors[aRecord.donorID].add(aRecord.year)
                 nValid += 1
             elif aRecord == 0: #Just a comment line, move on.
                 continue
             else:
                 nInvalid += 1
                 continue
         dtWall = time.time() - t0wall
         msg = (divLine +  
                'Gone through a total of {0:d} lines. \n' 
                'Processed {1:d} valid records. \n'
                'Skipped   {2:d} invalid records.\n'
                'DONE in {3:f} seconds of wall clock time '
                .format(nRec, nValid, nInvalid, dtWall))
         logFile.write(msg)
    return dtWall

def getColumnIDs(selectedColumns):
    """Read the header file and return name & number of requested columns."""

    headerFilePath = 'indiv_header_file.csv' #Downloaded from FEC website.    
    with open(headerFilePath) as headerFile:
        allColumns = next(csv.reader(headerFile, delimiter=','))
    try:  
        selectedNumbers = [allColumns.index(aColumn) 
                           for aColumn in selectedColumns]
    except ValueError:
        msg = ('The column you requested, {0}, does not exist' 
               'in the header file: {1} \n'
               'These are column names in the header file: \n'
               '{2}'.format(aColumn, headerFilePath, allColumns))
        logFile.write(msg)
        
    return dict(zip(selectedColumns, selectedNumbers)), len(allColumns)

def findPercentileValue(sortedList, percentile):
    """
    Return the value in sortedList corresponding to a given percentile
    using the nearest-rank method.
    """
    if percentile <= 0 or percentile > 100:
        # I have this check because percentile values out of this range 
        # will silently give wrong results.
        # This check could have been done only once soon after reading in 
        # the percentile value.
        # Checking for this condition each time this function is called will
        # make some hit on overall performance.
        # But It it is safer to have the check contained here, in case the 
        # function gets used somewhere else in the future.  
        raise ValueError('percentile must be greater than 0. '
                         'You gave {}'.format(percentile)
                        )
    else:    
        n = len(sortedList)
        idx = math.ceil((percentile/100.0)*n) - 1 #-1 since the list is 0-based.
        return sortedList[idx]

def emitStats(record, donations, tot, percentile, outFile, logFile):
    """Write the current repeat donations stats in the outFile."""
    
    donations.sort()
    #This list comes sorted except for the last item.
    #But .sort() is smart enough to use Insertion Sort if the 
    #list is almost sorted, so this re-sort is not a big hit to overall cost.
    cnt  = len(donations)  # This is O(1), not a hit on overall cost, either.
    pctl = findPercentileValue(donations, percentile)
    rcpt = record.recipient
    zipCode = record.zipCode
    year    = record.year
    emit = '{}|{}|{}|{}|{}|{}\n'.format(rcpt, zipCode, year, pctl, tot, cnt)
    outFile.write(emit)

def moldRecord(record, lineNumber, selectedColumns, colID,
               nAllColumns, logFile, logVerbose):
    """Mold a record in a datastructure and return it if it is valid."""
    
    #Some pre-validations before even trying isValid.
    #See if you can gracefully move these in isValid.
    if not record:
       # Measure how much impact logVerbose checks have on speed.
       # Is there a way to bypass the logVerbose check if logVerbose is False? 
       if logVerbose:
           msg = ('Skipping line {:<15d} ' 
                  'because it is a blank line: {} ... \n'
                 ).format(lineNumber, str(record))
           logFile.write(msg)
       return None

    if record[0] and (not record[0].isspace()) and (record[0][0] == '#'):
       if logVerbose:
           msg = ('Skipping line {:<15d} ' 
                  'because it is commented out: {} ... \n'
                 ).format(lineNumber, str(record[0]))
           logFile.write(msg)
       return 0 
   
    if len(record) != nAllColumns:
        if logVerbose:
            msg = ('Skipping line {:<15d} ' 
                   'because it has some missing fields.\n'
                  ).format(lineNumber)
            logFile.write(msg)
        return None
   
    Record = namedtuple('Record', ['lineNumber', 'length', 'otherID', 
                                   'name', 'fullZipCode', 'date',  
                                   'recipient', 'amount'
                                  ]
                       )

    checkRecord = Record(lineNumber  = lineNumber,
                         length      = len(record),
                         otherID     = record[colID['OTHER_ID']],
                         name        = record[colID['NAME']],
                         fullZipCode = record[colID['ZIP_CODE']],
                         date        = record[colID['TRANSACTION_DT']],
                         recipient   = record[colID['CMTE_ID']],
                         amount      = record[colID['TRANSACTION_AMT']]
                         )
    
    if isValid(checkRecord, logFile, logVerbose):
         
        zipCode = checkRecord.fullZipCode[0:5]
        year = checkRecord.date[4:8]
        amount = int(checkRecord.amount)  # Round the nearest Dollar amount.
        donorID = checkRecord.name + zipCode  # A unique donor key.
        groupID = checkRecord.recipient + zipCode + year # A unique group key.
        molded = namedtuple('ValidRecord', ['donorID', 'groupID', 'recipient',
                                            'zipCode', 'amount', 'year'
                                           ]
                           )
        return molded(donorID, groupID, checkRecord.recipient, 
                      zipCode, amount, year
                     )

def isRepeat(record, donors, strictRepeat):
    """Return True if a donation is repear, False otherwise.""" 

    # For this challenge, a donor is considered a repeat donor if 
    # she/he donated to any recipient at any PRIOR* year.
    # I check for this explicitly by not using setdefault 
    # for donor dict so that I can start repeatDonations only after 
    # donors[donorID] list receives its first element.
    #
    # *This means that, if a donor has donated multiple times only 
    # within the current year, those donations are NOT counted as repeat 
    # donations. However, multiple donations within a prior year gets 
    # counted as repeat. This does not really make much sense. 
    # Nevertheless, I devised the command line option -s (which sets 
    # strictRepeat == True) to allow for this type of an accounting, 
    # just in case.
    #
    # The default behavior is strictRepeat == False and it considers 
    # contributions made in any year (prior as well as the current one) 
    # as repeat contributions -- which makes more sense.
    if record.donorID in donors:
        currentYear = set((record.year, )) 
        priorYears  = donors[record.donorID] - currentYear
        if strictRepeat and not priorYears :  
            return False
        else:
            return True
    else:
        return False

def isValid(record, logFile, logVerbose=False):
    """Take a record, return True if it's valid or False otherwise

       A record is considered invalid unless it successfully percolates 
       down through these all until else: -- and more. :/
    """
    result = False  
    
    # Consider using a try-except for all the tests below. 
    if (len(record.otherID) != 0 and not record.otherID.isspace()):
        if logVerbose:
            msg = ('Skipping line {:<15d} ' 
                   'because "OTHER_ID" field is not empty: {} \n'
                  ).format(record.lineNumber, record.otherID)
            logFile.write(msg)

    elif (record.recipient is None or 
          len(record.recipient) == 0 or 
          record.recipient.isspace() or
          not record.recipient.isalnum()):
        if logVerbose:
            msg = ('Skipping line {:<15d} '
                   'because "CMTE_ID" field is missing or empty \n'
                  ).format(record.lineNumber)
            logFile.write(msg)

    elif (record.name is None or 
          len(record.name) == 0 or 
          record.name.isspace()
         ):
        #Doing only a loose check on names on purpose.
        #If an aggressive check is needed a validator package can be used.
        if logVerbose:
            msg = ('Skipping line {:<15d} ' 
                   'because "NAME" field is blank. \n'
                  ).format(record.lineNumber)
            logFile.write(msg)

    elif (record.fullZipCode is None or 
          len(record.fullZipCode) < 5 or
          not record.fullZipCode[0:5].isdecimal()
         ): 
        #This will let in an entry like "02895-DONTKNOW", which I thought is 
        #not not-OK.
        if logVerbose:
            msg = ('Skipping line {:<15d} ' 
                   'because "ZIP_CODE" field does not exits, ' 
                   'it is empty, or malformed: {} \n'
                  ).format(record.lineNumber, record.fullZipCode)
            logFile.write(msg)

    elif (record.date is None or 
          len(record.date) == 0 or 
          record.date.isspace()
         ):
        if logVerbose:
            msg = ('Skipping line {:<15d} ' 
                   'because "TRANSACTION_DT" field is empty '
                   'or it does not exist. \n'
                  ).format(record.lineNumber)
            logFile.write(msg)
        # Also see the final check on record.date in else: clause below.

    elif (record.amount is None or 
          record.amount.isspace() or
          len(record.amount) == 0 or
          not isRealNumber(record.amount)
          or int(record.amount) <= 0
         ): 
        if logVerbose:
            msg = ('Skipping line {:<15d} ' 
                   'because "TRANSACTION_AMT" field is malformed ' 
                                                  'or non-positive: {} \n'
                  ).format(record.lineNumber, record.amount)
            logFile.write(msg)

    else:
        try:  # One more check on date to catch it if date is malformed.
            date=datetime.datetime.strptime(record.date, '%m%d%Y')
        except ValueError:
            if logVerbose:
                msg = ('Skipping line {:<15d} ' 
                       'because "TRANSACTION_DT" field is malformed: {} \n'
                      ).format(record.lineNumber, record.date)
                logFile.write(msg)
        else:
            result = True

    return result

def isRealNumber(s):
    """Return True if s (probably) represents a real number."""

    try:
        if math.isnan(float(s)):
            return False
        else:
            return True
    except ValueError:
        return False

def test_isRealNumber():
    '''Test if isRealNumber works as expected'''

    fails = ['Hello', 'NaN', 'NAN', 'nan', '0e', '0.0e']
    for anInput in fails:
        result = isRealNumber(anInput) 
        assert result == False, ('FAIL: Returned {} for {}'
                                ).format(result, anInput)

    passes = ['0', '0.0', '.0', '0.', '0.0e0', '0e0']
    for anInput in passes:
        result = isRealNumber(anInput) 
        assert result == True, ('FAIL: Returned {} for {}'
                               ).format(result, anInput)
     
if __name__ == '__main__':
    """Command-line execution for donation-analytics.py"""

    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recFilePath', 
                        help='Path to the record file provided by FEC'
                       )
    parser.add_argument('pctFilePath', 
                        help='Path to the file that holds the desired '
                             'percentile value between 0 and 100.'
                       )
    parser.add_argument('outFilePath', 
                        help='Path to the file where the repeat donation '
                             'results are written to.'
                       )
    parser.add_argument('logFilePath', 
                        help='Path to the file where a log of process '
                             '(stats, skipped lines, etc.) are written to.'
                       )
    parser.add_argument('-v','--v', action='store_true', 
                        help='Outputs any skipped records in the log file.'
                       )
    parser.add_argument('-s','--s', action='store_true', 
                        help='Modifies isRepeat so that the donations '
                             'done within the current calendar year are NOT '
                             'counted as repeat donation.'
                       )
    args = parser.parse_args()
    #Add some input checks here:
    recFilePath = args.recFilePath
    pctFilePath = args.pctFilePath
    outFilePath = args.outFilePath
    logFilePath = args.logFilePath
    logVerbose = args.v 
    strictRepeat = args.s 
    dtWall = main(recFilePath, pctFilePath, outFilePath, logFilePath,
                  logVerbose, strictRepeat)
    print('DONE in {0:10g} seconds of wall clock time'.format(dtWall))

    test_isRealNumber()
