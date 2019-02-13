# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# The goal here is to generate BRAT visualizations, but embed the whole thing
# in non-server HTML.

import os, sys, shutil, csv, json

def Usage():
    print >> sys.stderr, "Usage: visualize.py [ 'ose_gold' | 'ose_submission' ] ose_corpus brat_installation outdir"
    sys.exit(1)

if len(sys.argv) != 5:
    Usage()

# I can't use the QC dir to get the docs because in the most recent version,
# I removed some of the workspaces.

CORPUS_TYPE = sys.argv[1]

if CORPUS_TYPE not in ('ose_gold', 'ose_submission'):
    print >> sys.stderr, "Bad value for corpus type."
    sys.exit(1)
    
[XML_DIR, BRAT_INSTALLATION, OUTDIR] = [os.path.abspath(x) for x in sys.argv[2:]]

if os.path.exists(OUTDIR):
    shutil.rmtree(OUTDIR)
os.makedirs(OUTDIR)

ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR = os.path.join(ROOTDIR, "resources", "visualization")
sys.path.insert(0, os.path.join(ROOTDIR, "lib", "python"))

from OSE_AE.corpus import Corpus
from OSE_AE.ose_eval_format import OSEGoldEvalFormat, OSESubmissionEvalFormat
if CORPUS_TYPE == "ose_gold":
    corpus = Corpus(XML_DIR, OSEGoldEvalFormat())
else:
    corpus = Corpus(XML_DIR, OSESubmissionEvalFormat())

corpus.load()

os.makedirs(os.path.join(OUTDIR, "js"))
shutil.copy(os.path.join(RESOURCE_DIR, "labelviz.js"), os.path.join(OUTDIR, "js"))
os.makedirs(os.path.join(OUTDIR, "brat_13"))
shutil.copytree(os.path.join(BRAT_INSTALLATION, "client"), os.path.join(OUTDIR, "brat_13", "client"))
shutil.copytree(os.path.join(BRAT_INSTALLATION, "static", "fonts"), os.path.join(OUTDIR, "brat_13", "static", "fonts"))
shutil.copy(os.path.join(BRAT_INSTALLATION, "style-vis.css"), os.path.join(OUTDIR, "brat_13"))

# I'm going to generate one document per section.

# OSE_AE: "background: limegreen"
# NonOSE_AE: "background: yellow"
# Not_AE_Candidate: "background: red; color: white"

for drugName, label in corpus.labels.items():
    for section in label.sections:
        mentions = [m for m in label.mentions if section.id == m.section]
        docData = {"text": section.text,
                   "entities": [["T%d" % i, m.type, [[sp[0], sp[1] + sp[0]] for sp in m.spans]] for (i, m) in enumerate(mentions)],
                   "normalizations": [["N%d" % i, "Reference", "T%d" % i, "MedDRA", m.meddraEntries[0][1], m.meddraEntries[0][0]] for (i, m) in enumerate(mentions) if m.meddraEntries],
                   "attributes": [["A%d" % i, "Reason", "T%d" % i, m.reason] for (i, m) in enumerate(mentions) if m.reason]}
        fp = open(os.path.join(RESOURCE_DIR, "template.html"), "r")
        s = fp.read()
        fp.close()
        fp = open(os.path.join(OUTDIR, drugName + "_" + section.name.replace(" ", "_") + ".html"), "w")
        fp.write(s.replace("TPL_DOCDATA", json.dumps(docData)))
        fp.close()
