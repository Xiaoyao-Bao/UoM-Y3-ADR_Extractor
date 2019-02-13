# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This file adapted from a portion of the scorer provided by NLM as part of the TAC 2017 ADR competition. See:
# https://bionlp.nlm.nih.gov/tac2017adversereactions/
# Heavily modified by MITRE.

import argparse
import os
import sys

THISDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(THISDIR), "lib", "python"))

from OSE_AE.ose_eval_format import OSEGoldEvalFormat, OSESubmissionEvalFormat
from OSE_AE.corpus import Corpus
from OSE_AE.score import DetailRowFormatter, ResultsSet, ALL_METRICS

NAMES_TO_METRICS = {t.name: t for t in ALL_METRICS}

parser = argparse.ArgumentParser()
parser.add_argument('gold_dir', metavar='GOLD', type=str,
                    help='path to directory containing gold labels')
parser.add_argument('guess_dir', metavar='RUN GUESSDIR', type=str, nargs="+", 
                    help='run name and path to directory containing system output')
parser.add_argument("--medascii_dir", dest="medascii_dir",
                    help = "the MedAscii directory of your MedDRA 20.1 data distribution. When provided, the corpus reader will perform MedDRA wellformedness checking.")
parser.add_argument("--metrics", help="comma-separated list of metric names to restrict the evaluation to. Legal names are: " + ", ".join(NAMES_TO_METRICS.keys()))
parser.add_argument("--csv_outdir", dest="csv_outdir",
                    help="when present, write all data to the CSV directory. The directory will be created if it doesn't exist.")
parser.add_argument("--suppress_score_output", action="store_true",
                    help="if specified, results will not be printed to standard output")
parser.add_argument("--detail_spreadsheets", action = "store_true",
                    help = "if specified, detail spreadsheets will be saved")
parser.add_argument("--significant_digits", dest="significant_digits", type=int,
                    help="if specified, changes the number of significant digits presented in the CSV output (default is 2). 0 will eliminate any limitation. The standard output is not affected.")
parser.add_argument("--compute_confidence_data", action="store_true",
                    help = "if specified, use thousandfold bootstrapping to compute mean, variance, standard deviation. Currently unimplemented (hopefully in a future update).")
args = parser.parse_args()

metricList = None

if args.metrics:
    metricNames = [s.strip() for s in args.metrics.split(",")]
    metricList = []
    for tName in metricNames:
        try:
            metricList.append(NAMES_TO_METRICS[tName])
        except KeyError:
            print("Value for --metrics must be a comma-separated set of metric names")
            parser.print_help()
            sys.exit(1)

goldFmt = OSEGoldEvalFormat(medasciiDir = args.medascii_dir and os.path.abspath(args.medascii_dir))
submissionFmt = OSESubmissionEvalFormat(medasciiDir = args.medascii_dir and os.path.abspath(args.medascii_dir))

if len(args.guess_dir) % 2 != 0:
    print("Guess dir arguments are not a multiple of 2.")
    parser.print_help()
    sys.exit(1)

print('Gold Directory:  ' + args.gold_dir)
goldCorpus = Corpus(args.gold_dir, goldFmt)
goldCorpus.load()
print("  %d labels." % len(goldCorpus.files))

writers = []
summaryWriterHash = detailWriter = None

outDir = None
if args.csv_outdir:
    summaryWriterHash = {}
    outDir = os.path.abspath(args.csv_outdir)
    if os.path.exists(outDir):
        if not os.path.isdir(outDir):
            print("CSV outdir exists, but it isn't a directory")
            parser.print_help()
            sys.exit(1)
    else:
        os.makedirs(outDir)

else:
    if args.suppress_score_output:
        print("No score outputs are enabled. Exiting.")
        parser.print_help()
        sys.exit(1)
        
    if args.detail_spreadsheets:
        print("Warning: detail spreadsheets requested, but no CSV outdir provided. Ignoring.")
        args.detail_spreadsheets = False        

if args.detail_spreadsheets:
    detailWriter = DetailRowFormatter()

pairs = []
i = 0
while i < len(args.guess_dir):
    pairs.append(args.guess_dir[i:i+2])
    i += 2

rSet = ResultsSet(goldCorpus, pairs)
rSet.score(submissionFmt, metrics = metricList,
           write_stdout = not args.suppress_score_output,
           write_details = detailWriter,
           write_summaries = summaryWriterHash,
           significant_digits = args.significant_digits,
           compute_confidence_data = args.compute_confidence_data)

if summaryWriterHash or detailWriter:

    if summaryWriterHash:
        for k, summaryWriter in summaryWriterHash.items():
            summaryWriter.write_csv(os.path.join(outDir, "%s_summary_scores.csv" % k))

    if detailWriter:
        detailWriter.write_csv(os.path.join(outDir, "detail_scores.csv"))
