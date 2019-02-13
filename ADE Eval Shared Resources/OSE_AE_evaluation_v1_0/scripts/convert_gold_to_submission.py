# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This script creates an empty submission corpus from a gold standard corpus.

import os, sys, shutil

def Usage():
    print >> sys.stderr, "Usage: convert_gold_to_submission.py ose_gold_xml_dir ose_submission_output_xml_dir"
    sys.exit(1)

if len(sys.argv) != 3:
    Usage()

[OSE_GOLD_DIR, OUT_DIR] = [os.path.abspath(x) for x in sys.argv[1:]]

THISDIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(os.path.dirname(THISDIR), "lib", "python"))
from OSE_AE.corpus import Corpus
from OSE_AE.ose_eval_format import OSEGoldEvalFormat, OSESubmissionEvalFormat

print "### Loading OSE gold corpus..."
oseGoldCorpus = Corpus(OSE_GOLD_DIR, OSEGoldEvalFormat())
oseGoldCorpus.load(warn_and_continue = True)

print "### Removing mentions..."
# So first, we discard documents which don't match.

for lName, goldLabel in oseGoldCorpus.labels.items():

    goldLabel.mentions = []
    goldLabel._mentionDict = {}

if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR)

oseGoldCorpus.dir = OUT_DIR
oseGoldCorpus.format = OSESubmissionEvalFormat()
oseGoldCorpus.write()
