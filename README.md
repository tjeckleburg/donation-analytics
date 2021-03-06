# Insight Data Engineering Coding Challenge: Donation Analytics

## Table of Contents
1. [Summary of the Challenge](README.md#summary-of-the-challenge)
1. [Summary of the Algorithm and the Implementation](README.md#summary-of-the-algorithm-and-the-implementation)
1. [Performance and Scalability](README.md#performance-and-scalability)
1. [Extra Features](README.md#extra-features)
1. [Usage](README.md#usage)
1. [Tests](README.md#tests)

## Summary of the Challenge:
A series of donation records stream in from a file, line-by-line. 
Each record lists some information about the donor, the recipient and the donation. 
As each record comes in, emit the following as a new line in a file if the donor is a repeat donor: 

    Recipient|Zip|Year|Repeat Donation x-Percentile Amt.|Repeat Donation Total Amt.|# Rep. Donations 

The percentile value used when finding `x-Percentile Amt.` will be read from a file. 
Assume that the records can have missing or malformed data so do some validity checks to skip such 
records.

See [the full description of the challenge](https://github.com/InsightDataScience/donation-analytics/blob/master/README.md).

[Back to Table of contents](README.md#table-of-contents)


## Summary of the Algorithm and the Implementation
The following algorithm is implemented using Python 3.6 came in Anaconda 3 distribution. 
Although I used an Anaconda distribution, I have only used modules that are present in standard 
Python 3.6 library.

1. Read the next available record and check if it is valid.
   1. If the record is valid mold it to `namedtuple` and return that data structure. 
      In this data structure, define each donor with a key (i.e. `donorID`) which is composed of 
      the donor's name and zip code.
      In addition, define each donation group with key (i.e. `groupID`) which is composed of the 
      recipient, donor's zip code and the donation year.
   1. If the record is not valid return null.
1. If a valid record is returned proceed to the next step. Otherwise loop back to Step 1.
1. Check if the donor is a repeat donor.
   A donor is a repeat donor if its `donorID` is found as a key in  a `dict` called `donors`, which 
   hash-maps each `donorID` to a `set` of years<sup id="a1">[1](#f1)</sup> that the donor donated within.
   1. If the donor is a repeat donor, 
      1. Append the donation amount to a `list` hash-mapped to this `groupID` in a `dict`.
      1. Accordingly, increment a running sum which is hash-mapped to this `groupID` in another `dict`. 
      1. Compute the desired percentile value and emit the updated values in the format requested.
   1. If the donor is not a repeat donor, add that donor to the `donors` `dict`.
1. Add the donation year of that donor to its corresponding `set` of donation years<sup id="a2">[2](#f2)</sup>. 
1. Loop back to Step 1.

I used hashable data structures (i.e. `set`, `tuple` and `dict`) to contain all immutable data, since 
these data structures allow looking-up and setting in O(1) on average.
The donations mentioned in Step 3.i.a are stored in a `list` so that it could be summed, sorted and 
index-accessed for the percentile computations.
While these operations are performed for every repeat donation, it does not make a super-linear 
impact on overall run time because
1. The length of a typical `list` is much smaller than total number of records, i.e. `k` << `n` 
1. The sum of this `list` is not recomputed; instead, it is updated as a running total within the loop
   one-level outside.
   This avoids the O(k) impact of a `sum()` operation within the innermost loop.
1. The `list` comes pre-sorted from a previous update except for its last element which is just appended.
   The `.sorted()` method, which implements Timsort algorithm takes O(k), not O(klogk), time by adapting
   to insert sort if the list is almost sorted like this.
1. The other operations done on this `list` in this algorithm (i.e. `len()`, look-up and .append()) require 
    O(1) time.   

As shown in [Performance and Scalability](Readme.md#performance-and-scalability) all these 
considerations made the per-record time complexity about O(1) time, making the overall run time 
comlexity about O(n) where n is the number of records in the file. Since each record must be examined
this scaling is as good as it gets for this problem.

Footnotes:

<b id="f1">1.</b> *Dealing with ambiguity*:
By default, this set of years include all the years donor has made any donation to any recipient. 
The challenge rules, however, state that
  
>... if a donor had previously contributed to any recipient listed in the `itcont.txt` file 
 in any *prior* calendar year, that donor is considered a repeat donor.

(*emphasis* is mine). 
This means that, multiple donations within the current year are *not* counted as repeat donations.
This did not really make much sense to me, also due to the fact that the records can come in
non-chronological order.
Nevertheless, I devised the command line option `-s`, which sets `strictRepeat = True`, to allow for 
this type of an accounting, if needed. 
When this option is turned-on, the current year is excluded from that `set` of donation years. 
 [↩](#a1)

<b id="f2">2.</b>
 As per the challenge rules, there is no distiction made here as to what recipient the 
donor donates -- a subsequent donation to *any* recipent qualifies as a repeat donation.
 [↩](#a2)
  
[Back to Table of contents](README.md#table-of-contents)

## Performance and Scalability
Since my implementation does almost a constant-time (O(1)) work per each record, the overall
run time per n records should scale linarly (O(n)). 
This plot demonstrates that my approach indeed scales up linearly.
I generated this data by running my script for the first n = 1, 10, 100, 1k, 10k, 100k, 1M and 10M
records grabbed from the `itcont.txt` file provided in FEC web site for the year 2016. 
My algorithm and implementation scales up nearly linearly to at least 10M records.
Note that the complete year-2016 file, which is currently the largest one provided in FEC website, 
has slighly more than 20M records. According to this scaling, my algorithm can process this many 
records in about 3:30 hours -- and it did, I've tested it).

![Performance and Scalability](./scaleUp.png)

Since each record must be examined this scaling is as good as it gets for this problem.

[Back to Table of contents](README.md#table-of-contents)

## Extra Features

My code automatically finds out the column numbers of the requested fields from a header 
file `indiv_header_file.csv` provided by FEC.
This increases the robustness of the program by eliminating the need for manually finding out and 
hard-coding the column numbers of the requested fields. 

In addition, my code writes a log file that lists what files were read in or written out, how many records were 
processes or skipped and how long the whole process took. 
If the command line option `-v` is provided, the output becomes more verbose by listing what records 
were skipped and why. The following is a sample from my `test_2` with option `-v`. The part within the dashed
lines disappears if `-v` is not provided.

```
Opened
./test_2/output/repeat_donors-v.txt
to output the repeat donation stats in the following format:
| Receipent | Donors Zip Code| Donation Year| 30 Percentile Amount | Total Repeat Donation Amount| Number of Repeat Donations
The requested percentile value is read from:
./test_2/input/percentile.txt
Started processing records present in:
./test_2/input/itcont.txt
See the end of this log file for a process summary.
-------------------------------------------------------------------------------
Skipping line 1               because it is commented-out: #A truncated record: ...
Skipping line 2               because it has some missing fields.
Skipping line 3               because it is commented-out: #A blank record: ...
Skipping line 4               because it is a blank line: [] ...
Skipping line 5               because it is commented-out: #A lone delimiter record: ...
Skipping line 6               because it has some missing fields.
Skipping line 7               because it is commented-out: #Non-empty OtherID ...
Skipping line 8               because "OTHER_ID" field is not empty: AB12
Skipping line 9               because it is commented-out: #Missing Recipient ...
Skipping line 10              because "CMTE_ID" field is missing or empty
Skipping line 11              because it is commented-out: #Missing Name ...
Skipping line 12              because "NAME" field is blank.
Skipping line 13              because it is commented-out: #Missing Zip Code ...
Skipping line 14              because "ZIP_CODE" field does not exits, it is empty, or malformed:
Skipping line 15              because it is commented-out: #Truncated Zip Code ...
Skipping line 16              because "ZIP_CODE" field does not exits, it is empty, or malformed: 0289
Skipping line 17              because it is commented-out: #Missing Date ...
Skipping line 18              because "TRANSACTION_DT" field is empty or it does not exist.
Skipping line 19              because it is commented-out: #Blank date ...
Skipping line 20              because "TRANSACTION_AMT" field is malformed or non-positive:
Skipping line 21              because it is commented-out: #Malformed Date #1 ...
Skipping line 22              because "TRANSACTION_DT" field is malformed: 123
Skipping line 23              because it is commented-out: #Impossible Date ...
Skipping line 24              because "TRANSACTION_DT" field is malformed: 13012018
Skipping line 25              because it is commented-out: #A good record: ...
Skipping line 27              because it is commented-out: #Blank OtherID: This is OK ...
Skipping line 29              because it is commented-out: #Partially-true Zip Code: This is OK ...
-------------------------------------------------------------------------------
Gone through a total of 30 lines.
Processed 3 valid records.
Skipped   12 invalid records.
DONE in 0.010658 seconds of wall clock time
```
[Back to Table of contents](README.md#table-of-contents)

## Usage
```
usage: donation-analytics.py [-h] [-v] [-s]
                             recFilePath pctFilePath outFilePath logFilePath

Insight Data Engineering coding challenge: Compute running percentile of
repeat donations to US political campaigns based on FEC data.

positional arguments:
  recFilePath  Path to the record file provided by FEC
  pctFilePath  Path to the file that holds the desired percentile value
               between 0 and 100.
  outFilePath  Path to the file where the repeat donation results are written
               to.
  logFilePath  Path to the file where a log of process (stats, skipped lines,
               etc.) are written to.

optional arguments:
  -h, --help   show this help message and exit
  -v, --v      Outputs any skipped records in the log file.
  -s, --s      Modifies isRepeat so that the donations done within the current
               calendar year are NOT counted as repeat donation.
```
## Tests

I added input validation tests and algorithm correctness tests inside the test suite directory.
I also added a custom `bash` script to run these tests. 
Here is a sample output:

```
-----------------------------------------------------------------------------------------
INSIGHT'S DEMO TEST:
PASS: ./test_1/output/repeat_donors.txt
PASS: ./test_1/output/repeat_donors-v.txt
PASS: ./test_1/output/repeat_donors-s.txt
PASS: ./test_1/output/repeat_donors-s-v.txt
-----------------------------------------------------------------------------------------
INPUT VALIDATION TESTS:
PASS: ./test_2/output/repeat_donors.txt
PASS: ./test_2/output/repeat_donors-v.txt
PASS: ./test_2/output/log-v.txt
PASS: ./test_2/output/repeat_donors-s.txt
PASS: ./test_2/output/repeat_donors-s-v.txt
PASS: ./test_2/output/log-s-v.txt
-----------------------------------------------------------------------------------------
ALGORITHM CORRECTNESS TESTS:
PASS: ./test_3/output/repeat_donors.txt
PASS: ./test_3/output/repeat_donors-v.txt
PASS: ./test_3/output/repeat_donors-s.txt
PASS: ./test_3/output/repeat_donors-s-v.txt
-----------------------------------------------------------------------------------------
PERFORMANCE and SCALE-UP TEST:
Processing. See process logs in ./test_2016/output/log_1.txt
DONE in 0.00356817 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_10.txt
DONE in  0.0111852 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_100.txt
DONE in   0.086674 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_1k.txt
DONE in   0.772814 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_10k.txt
DONE in    7.96312 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_100k.txt
DONE in    82.4028 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_1M.txt
DONE in    751.422 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_10M.txt
DONE in    6563.69 seconds of wall clock time
Processing. See process logs in ./test_2016/output/log_all20M.txt
DONE in    12714.6 seconds of wall clock time
```

In addition to these program tests, I added assertion-based unit tests in isRealNumber(s) 
function for demonstration purposes.

[Back to Table of contents](README.md#table-of-contents)
