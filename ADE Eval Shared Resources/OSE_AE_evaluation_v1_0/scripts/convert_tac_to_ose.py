# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This script converts TAC 2017 output into an OSE submission, given an OSE gold corpus for
# file matching.

import os, sys, shutil, argparse

parser = argparse.ArgumentParser()
parser.add_argument('tac_xml_dir', type=str,
                    help='TAC submission directory of XML files in TAC format')
parser.add_argument('ose_gold_xml_dir', type=str,
                    help='OSE gold standard directory of XML files in OSE gold standard format')
parser.add_argument('ose_submission_output_xml_dir', type=str,
                    help='output directory where converted XML files in OSE submission format will be placed (directory will be created if necessary')
parser.add_argument("--strict", action="store_true",
                    help="If present, TAC format reader will fail rather than warn for certain inconsistencies")
parser.add_argument("--medascii_dir", dest="medascii_dir",
                    help = "the MedAscii directory of your MedDRA 20.1 data distribution. When provided, the corpus reader will perform MedDRA wellformedness checking.")
args = parser.parse_args()

TAC_DIR = os.path.abspath(args.tac_xml_dir)
OSE_GOLD_DIR = os.path.abspath(args.ose_gold_xml_dir)
OUT_DIR = os.path.abspath(args.ose_submission_output_xml_dir)

THISDIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(os.path.dirname(THISDIR), "lib", "python"))
from OSE_AE.corpus import Corpus, GuessCorpus
from OSE_AE.ose_eval_format import OSEGoldEvalFormat, OSESubmissionEvalFormat
from OSE_AE.tac_format import TACFormat

print "### Loading TAC corpus..."
tacCorpus = Corpus(TAC_DIR, TACFormat(strict = args.strict, medasciiDir = ((args.medascii_dir and os.path.abspath(args.medascii_dir)) or None)))
tacCorpus.load(warn_and_continue = True)

print "### Loading OSE gold corpus..."
oseGoldCorpus = Corpus(OSE_GOLD_DIR, OSEGoldEvalFormat())
oseGoldCorpus.load(warn_and_continue = True)

print "### Converting..."
# So first, we discard documents which don't match.

keep = set()
for lName, label in tacCorpus.labels.items():
    try:
        goldLabel = oseGoldCorpus.labels[lName]
    except KeyError:
        continue
    # Make sure the sections match. I won't have imposed the restrictions
    # imposed by the OSESubmissionEvalFormat, but that's just a single
    # bundle of MedDRA info.
    if len(label.sections) != len(goldLabel.sections):
        print "WARNING: Discarding", lName, "because number of sections don't match"
        continue
    
    if set([s.name for s in label.sections]) != set([s.name for s in goldLabel.sections]):
        print "WARNING: Discarding", lName, "because names of sections don't match"
        continue

    # Now, map the indices.
    idMap = {}
    fail = False
    for s in goldLabel.sections:
        tacS = label.getSectionByName(s.name)
        if tacS.text != s.text:
            print "WARNING: Discarding", lName, "because texts of", s.name, "don't match"
            fail = True
            break
        if tacS.id != s.id:
            label._sectionDict[s.id] = tacS
            idMap[tacS.id] = s.id
            tacS.id = s.id
    
    if fail:
        continue
            
    if idMap:
        # There aren't going to be any ignored regions.
        for m in label.mentions:
            m.section = idMap.get(m.section, m.section)

    # Make sure the ignored regions are copied over.
    for r in goldLabel.ignoredRegions:
        r.clone(label)

    for m in label.mentions:
        if len(m.meddraEntries) > 1:
            print "WARNING: discarding extra MedDRA entries", lName, m.meddraEntries[1:]
            m.meddraEntries[1:] = []

    keep.add(lName)
    
# Now, I have all the keeps.

print "Kept", len(keep), "labels:", ", ".join(sorted(keep))

if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR)

tacCorpus.labels = {lName: label for (lName, label) in tacCorpus.labels.items() if lName in keep}
tacCorpus.dir = OUT_DIR
tacCorpus.format = OSESubmissionEvalFormat()
tacCorpus.write()
