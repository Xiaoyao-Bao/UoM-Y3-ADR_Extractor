# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

import os, sys, argparse

parser = argparse.ArgumentParser()
parser.add_argument("--medascii_dir", dest="medascii_dir",
                    help = "the MedAscii directory of your MedDRA 20.1 data distribution. When provided, the corpus reader will perform MedDRA wellformedness checking.")
parser.add_argument("--raise_error", action="store_true",
                    help = "if present, raise a Python error rather than warning and continuing when an error is encountered")
parser.add_argument("corpus_type", choices = ["ose_gold", "ose_submission"],
                    help = "the type of the corpus")
parser.add_argument("xml_dir", 
                    help = "a directory of XML documents in the format appropriate to the corpus type")
args = parser.parse_args()

CORPUS_TYPE = args.corpus_type

XML_DIR = os.path.abspath(args.xml_dir)

THISDIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(os.path.dirname(THISDIR), "lib", "python"))
from OSE_AE.corpus import Corpus
from OSE_AE.ose_eval_format import OSEGoldEvalFormat, OSESubmissionEvalFormat
from OSE_AE.tac_format import TACFormat
if CORPUS_TYPE == "ose_gold":
    corpus = Corpus(XML_DIR, OSEGoldEvalFormat(medasciiDir = args.medascii_dir))
else:
    corpus = Corpus(XML_DIR, OSESubmissionEvalFormat(medasciiDir = args.medascii_dir and os.path.abspath(args.medascii_dir)))

corpus.load(warn_and_continue = not args.raise_error)
