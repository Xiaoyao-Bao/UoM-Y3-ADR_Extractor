# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This is a corpus object.

import os

class Corpus:

    def __init__(self, corpusDir, fmt):
        self.dir = corpusDir
        self.labels = {}
        self.format = fmt
        self.files = [p for p in os.listdir(self.dir) if p.endswith('.xml')]

    def load(self, warn_and_continue = False):
        for p in self.files:
            try:
                self.labels[os.path.splitext(p)[0]] = self._load(os.path.join(self.dir, p))
            except Exception, e:
                if warn_and_continue:
                    print "Error for file %s: %s" % (p, str(e))
                else:
                    raise

        totalAnnots = 0
        for l in self.labels.values():
            for s in l.sections:
                totalAnnots += len([m for m in s.getNonIgnoredMentions() if m.type == "OSE_Labeled_AE"])
        print "Total annots", totalAnnots

    def _load(self, path, **kw):
        return self.format.read(path, **kw)

    def add(self, label):
        if label.fileBasename in self.files:
            raise Exception, "file for label is already present"
        self.files.append(label.fileBasename)
        self.labels[os.path.splitext(label.fileBasename)[0]] = label

    def write(self):
        for label in self.labels.values():
            self.format.write(label, os.path.join(self.dir, label.fileBasename))

class GuessCorpus(Corpus):

    def __init__(self, corpusDir, runName, fmt, goldCorpus):
        Corpus.__init__(self, corpusDir, fmt)
        self.runName = runName
        self.files = list(set(goldCorpus.files) & set(self.files))
