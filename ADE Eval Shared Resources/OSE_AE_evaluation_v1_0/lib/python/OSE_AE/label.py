# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This file originally a portion of the scorer provided by NLM as part of the TAC 2017 ADR competition. See:
# https://bionlp.nlm.nih.gov/tac2017adversereactions/
# Heavily modified by MITRE.

# These classes are the documents in the corpus.

# In the ADR evaluation, there was no direct link between the mentions
# and the MedDRA codes. That won't work in this case. Each mention must be
# grounded. We don't care about positive/negative adverse reactions, as ADR
# did; in the gold standard, the elements that aren't of interest
# are mentions with different labels. Similarly, we have no canonicalized
# strings, and no relations in this label object.

# The underlying object below the submission and gold standard
# corpora is the same. That means that it has to tolerate the more
# general requirements of the gold standard: multiple mention types,
# reasons, multiple meddra PTs.

class Label:
    def __init__(self, xmlFileBasename, drug, permittedMentions):
        self.fileBasename = xmlFileBasename
        self.drug = drug
        self.sections = []
        self.mentions = []
        self.permittedMentions = permittedMentions
        self.ignoredRegions = []
        self._sectionDict = {}
        self._sectionNameDict = {}
        self._mentionDict = {}

    def clone(self):
        # This creates a new label with the appropriate sections.
        # But no annotations, at the moment. Of course,
        # I'm not sure I need this yet.
        lab = Label(self.fileBasename, self.drug, self.permittedMentions)
        for s in self.sections:
            s.clone(lab)
        for r in self.ignoredRegions:
            r.clone(lab)
        return lab

    def getSectionByID(self, sId):
        return self._sectionDict.get(sId)

    def getSectionByName(self, sName):
        return self._sectionNameDict.get(sName)

    def addSection(self, id, name, text):
        if self._sectionDict.has_key(id):
            raise Exception, "duplicate section ID"
        if self._sectionNameDict.has_key(name):
            raise Exception, "duplicate section name"
        sect = Section(self, id, name, text)
        self._sectionDict[sect.id] = sect
        self._sectionNameDict[sect.name] = sect
        self.sections.append(sect)
        return sect

    # This is ONLY used in the TAC reader for cases where
    # the NLM data had multiple sections.
    
    def removeSection(self, section):
        del self._sectionDict[section.id]
        del self._sectionNameDict[section.name]
        self.sections.remove(section)

    def getMentionByID(self, mId):
        return self._mentionDict.get(mId)

    def addMention(self, id, section, *args, **kw):
        if not self._sectionDict.has_key(section):
            raise Exception, "unknown section ID for mention"
        if self._mentionDict.has_key(id):
            raise Exception, "duplicate mention ID"
        m = Mention(self, id, section, *args, **kw)
        if m.type not in self.permittedMentions:
            raise Exception, "impermissible mention type " + m.type
        self._mentionDict[m.id] = m
        self.mentions.append(m)
        return m

    def addIgnoredRegion(self, name, section, start, rlen):
        if [r for r in self.ignoredRegions if (r.start == start) and (r.len == rlen)]:
            raise Exception, "duplicate ignored region"
        if not self._sectionDict.has_key(section):
            raise Exception, "unknown section ID for ignored region"
        rObj = IgnoredRegion(self, name, section, start, rlen)
        self.ignoredRegions.append(rObj)
        return rObj

class Section:
    def __init__(self, label, id, name, text):
        self.label = label
        self.id = id
        self.name = name
        self.text = text

    def addMention(self, mId, *args, **kw):
        return self.label.addMention(mId, self.id, *args, **kw)

    def clone(self, newLabel):
        newLabel.addSection(self.id, self.name, self.text)

    def getNonIgnoredMentions(self):
        theseRegions = [(r.start, r.start + r.len) for r in self.label.ignoredRegions if r.section == self.id]
        if not theseRegions:
            return [m for m in self.label.mentions if m.section == self.id]
        else:                
            mentions = []
            for m in self.label.mentions:
                if m.section == self.id:
                    s = m.spans[0][0]
                    e = m.spans[-1][0] + m.spans[-1][1]
                    discard = False
                    for rStart, rEnd in theseRegions:
                        # If the annotation overlaps with this region, discard it.
                        if (rStart <= s < rEnd) or (rStart < e <= rEnd):
                            discard = True
                            break
                    if not discard:
                        mentions.append(m)
            return mentions
        
    def getMentions(self):
        return [m for m in self.label.mentions if m.section == self.id]

# The evaluation ignores certain regions (headers, excerpts). These
# are recorded separately from the mentions.
    
class IgnoredRegion:

    def __init__(self, label, name, section, start, len):
        self.label = label
        self.name = name
        self.section = section
        self.start = start
        self.len = len

    def clone(self, newLabel):
        newLabel.addIgnoredRegion(self.name, self.section, self.start, self.len)

# Unlike the TAC evaluation, we track pairs of start and length rather than
# the actual start and len comma-separated strings.

# You have to have at least one normalization if you're an OSE_LabeledAE.
        
class Mention:
    def __init__(self, label, id, section, type, spans, meddra_pt, meddra_pt_id,
                 meddra_llt = None, meddra_llt_id = None, reason = None, other_meddra_info = None):
        self.label = label
        self.id = id
        self.section = section
        self.type = type
        self.spans = sorted(spans)
        if (self.type == "OSE_Labeled_AE") and (not (meddra_pt and meddra_pt_id)):
            raise Exception, "no MedDRA information"
        if meddra_pt and meddra_pt_id:
            self.meddraEntries = [(meddra_pt, meddra_pt_id, meddra_llt, meddra_llt_id)]
            if other_meddra_info:
                self.meddraEntries += other_meddra_info
        else:
            self.meddraEntries = []
        self.reason = reason
        
    def __str__(self):
        return 'Mention(id={},section={},type={},start={},len={},str="{}",meddra="{}")'.format(
            self.id, self.section, self.type, ",".join([str(p[0]) for p in self.spans]), ",".join([str(p[1]) for p in self.spans]),
            self.computeUniqueString(), ",".join([p[0] for p in self.meddraEntries]))
    
    def __repr__(self):
        return str(self)

    def eval_repr(self, type = True, **kw):
        rpr = self.section + ':' + ",".join([str(p[0]) for p in self.spans]) + ':' + ",".join([str(p[1]) for p in self.spans])
        if type:
            rpr += ':' + self.type
        return rpr

    def computeUniqueString(self):
        text = []
        sectionText = self.label._sectionDict[self.section].text
        for start, slen in self.spans:
            text += sectionText[start:start+slen].split()
        return " ".join(text).lower()

    def clone(self, newLabel, newId):
        newLabel.addMention(newId, self.section, self.type, self.spans, (self.meddraEntries and self.meddraEntries[0][0]) or None,
                            (self.meddraEntries and self.meddraEntries[0][1]) or None,
                            meddra_llt = (self.meddraEntries and self.meddraEntries[0][2]) or None,
                            meddra_llt_id = (self.meddraEntries and self.meddraEntries[0][3]) or None,
                            reason = self.reason, other_meddra_info = self.meddraEntries[1:])
