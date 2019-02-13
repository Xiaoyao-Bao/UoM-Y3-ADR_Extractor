# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This file adapted from a portion of the scorer provided by NLM as part of the TAC 2017 ADR competition. See:
# https://bionlp.nlm.nih.gov/tac2017adversereactions/
# Heavily modified by MITRE.

# This file defines a reader/writer pair for the OSE eval format, which renders
# a Label to a file and a file to a Label.

from xml.etree import ElementTree
import os, re, sys

from .label import Label
from .meddra import MedDRADB

VALID_SECTION_NAMES = set(['adverse reactions', 'warnings and precautions',
                          'boxed warnings', 'warnings', 'precautions'])

VALID_MENTION_OFFSETS = re.compile('^\d+(,\d+)*$')

# Like the TAC eval, we have the sections, but <Reactions> and <Relations> are gone.
# Also, in the original code, the validation was separate from the reading,
# and here it is not, because I want to actually store digested
# values for start and len.

# There are two formats: the gold format and the submission format. They
# are sligntly different. The object that backs them up is the same
# in each case.

class OSEGoldEvalFormat:

    ROOT_LABEL = "GoldLabel"

    VALID_MENTION_TYPES = set(['Not_AE_Candidate', 'NonOSE_AE', "OSE_Labeled_AE"])

    OPTIONAL_MENTION_ATTRS = set(["reason"])

    def __init__(self, medasciiDir = None):
        self.meddraDB = None
        if medasciiDir:
            self.meddraDB = MedDRADB(medasciiDir)

    # Reads in the XML file
    def read(self, file):
        root = ElementTree.parse(file).getroot()
        assert root.tag == self.ROOT_LABEL, 'Root is not {}: {}'.format(self.ROOT_LABEL, root.tag)
        assert root.keys() == ["drug"], "Label attributes must be 'drug'"
        label = Label(os.path.basename(file), root.attrib['drug'], self.VALID_MENTION_TYPES)
        assert len(root) == 3, 'Expected 3 Children: ' + str(list(root))
        assert set([elt.tag for elt in root]) == set(["Text", "Mentions", "IgnoredRegions"]), "First-level labels must be Text, Mentions, IgnoredRegions"
        topDict = {elt.tag: elt for elt in root}

        for elem in topDict["Text"]:
            self._validateAndCreateSection(label, elem)

        for elem in topDict["IgnoredRegions"]:
            self._validateAndCreateIgnoredRegion(label, elem)

        for elem in topDict["Mentions"]:
            self._validateAndCreateMention(label, elem)

        return label

    def _validateAndCreateMention(self, label, elem):
        assert elem.tag == 'Mention', 'Expected \'Mention\': ' + elem.tag
        mId = self._attrib("id", elem)
        assert mId is not None, "Mention missing ID attribute"
        assert set(["id", "section", "type", "start", "len"]) - set(elem.keys()) == set(), \
            "Mention {} attributes must contain at least 'section', 'type', 'start', 'len'".format(mId)
        remainingAttrs = (set(["id", "section", "type", "start", "len"]) | self.OPTIONAL_MENTION_ATTRS) - set(elem.keys())
        # assert remainingAttrs == set(), "Unknown Mention {} attributes {}".format(mId, ", ".join(["'%s'" % a for a in remainingAttrs]))
        assert mId.startswith('M'), \
            'Mention ID does not start with M: ' + mId
        assert label.getMentionByID(mId) is None, \
            'Duplicate Mention ID: ' + mId
        sId = elem.attrib['section']
        assert label.getSectionByID(sId) is not None, \
            'No such section in label: ' + sId
        mStart = elem.attrib['start']
        mLen = elem.attrib['len']
        assert VALID_MENTION_OFFSETS.match(mStart), \
            'Invalid start attribute: ' + mStart
        assert VALID_MENTION_OFFSETS.match(mLen), \
            'Invalid len attribute: ' + mLen
        mType = elem.attrib['type']
        #assert mType in self.VALID_MENTION_TYPES, \
        #    'Invalid Mention type: ' + mType
        if mType not in self.VALID_MENTION_TYPES:
            print >> sys.stderr, "Warning: mention", mId, "of invalid type", mType, "will be discarded in label", label.fileBasename
            return None
        
        if remainingAttrs:
            print >> sys.stderr, "Warning: ignoring extra attributes", ", ".join(["'"+a+"'" for a in sorted(remainingAttrs)]), "in mention", mId, "in label", label.fileBasename

        meddraEntries = []
        reason = None
        if "reason" in self.OPTIONAL_MENTION_ATTRS:
            reason = self._attrib("reason", elem)
        for elem2 in elem:
            assert elem2.tag == 'Normalization', 'Expected \'Normalization\': ' + elem2.tag
            assert set(['meddra_pt', 'meddra_pt_id']) - set(elem2.keys()) == set(), \
                "Mention {} normalization attributes must be at least 'meddra_pt', 'meddra_pt_id'".format(mId)
            remainingAttrs = set(elem2.keys()) - set(["meddra_pt", "meddra_pt_id", "meddra_llt", "meddra_llt_id"])
            assert remainingAttrs == set(), \
                "Unknown Normalization attributes {} for mention {}".format(", ".join(["'%s'" % a for a in remainingAttrs]), mId)                
            meddraEntries.append((self._attrib('meddra_pt', elem2), \
                                 self._attrib('meddra_pt_id', elem2), \
                                 self._attrib('meddra_llt', elem2), \
                                 self._attrib('meddra_llt_id', elem2)))
            if self.meddraDB:
                self.meddraDB.checkWFC(label.fileBasename, mId, *meddraEntries[-1])
        if mType == "OSE_Labeled_AE":
            assert len(meddraEntries) > 0, "No Normalizations for Mention " + mId

        return label.getSectionByID(sId).addMention(mId, mType,
                                                    zip([int(ist.strip()) for ist in mStart.split(",")], [int(ist.strip()) for ist in mLen.split(",")]),
                                                    meddraEntries[0][0], meddraEntries[0][1],
                                                    meddra_llt = meddraEntries[0][2], meddra_llt_id = meddraEntries[0][3],
                                                    reason = reason, other_meddra_info = meddraEntries[1:])

    def _validateAndCreateSection(self, label, elem):
        assert elem.tag == 'Section', 'Expected \'Section\': ' + elem.tag
        assert set(elem.keys()) == set(["id", "name"]), "Section attributes must be 'id', 'name'"
        sId = elem.attrib['id']
        assert sId.startswith('S'), \
            'Section ID does not start with S: ' + sId
        assert label.getSectionByID(sId) is None, \
            'Duplicate Section ID: ' + sId
        sName = elem.attrib['name']
        assert sName in VALID_SECTION_NAMES, \
            'Invalid Section name: ' + sName
        label.addSection(sId, sName, elem.text)

    def _validateAndCreateIgnoredRegion(self, label, elem):
        assert elem.tag == 'IgnoredRegion', 'Expected \'IgnoredRegion\': ' + elem.tag
        assert set(elem.keys()) == set(["section", "start", "len", "name"]), "IgnoredRegion attributes must be 'section', 'start', 'len', 'name'"
        try:
            start = int(elem.attrib["start"])
        except ValueError:
            raise AssertionError, "IgnoredRegion start is not an integer: " + elem.attr["start"]
        try:
            rLen = int(elem.attrib["len"])
        except ValueError:
            raise AssertionError, "IgnoredRegion len is not an integer: " + elem.attr["len"]
        sId = elem.attrib['section']
        assert label.getSectionByID(sId) is not None, \
            'No such section in label: ' + sId
        label.addIgnoredRegion(elem.attrib["name"], sId, start, rLen)

    def _attrib(self, name, elem):
        if name in elem.attrib:
            return elem.attrib[name]
        else:
            return None
    
    def write(self, label, path):
        root = ElementTree.Element(self.ROOT_LABEL, drug = label.drug)
        root.text = "\n  "
        texts = ElementTree.SubElement(root, "Text")
        texts.text = "\n    "
        # Every one besides the last will be indented.
        prevS = None
        for section in label.sections:
            sec = ElementTree.SubElement(texts, "Section", attrib = {"id": section.id}, name = section.name)
            sec.text = section.text
            if prevS is not None:
                prevS.tail = "\n    "
            prevS = sec
        if prevS is not None:
            prevS.tail = "\n  "
        texts.tail = "\n  "

        ignoredRegions = ElementTree.SubElement(root, "IgnoredRegions")
        ignoredRegions.text = "\n    "
        lastR = None
        for ignoredRegion in sorted(label.ignoredRegions, key = lambda r: r.start):
            thisR = ElementTree.SubElement(ignoredRegions, "IgnoredRegion", name = ignoredRegion.name, start = str(ignoredRegion.start), len = str(ignoredRegion.len), section = ignoredRegion.section)
            if lastR is not None:
                lastR.tail = "\n    "
            lastR = thisR
        if lastR is not None:
            lastR.tail = "\n  "
        ignoredRegions.tail = "\n  "
        
        mentions = ElementTree.SubElement(root, "Mentions")
        mentions.text = "\n    "

        lastM = None
        for mention in sorted(label.mentions, key = lambda m: (m.section, m.spans[0][0])):
            attrs = self._mentionAttributesForWrite(mention)
            attrs.update({"id": mention.id, "type": mention.type, "section": mention.section,
                          "start": ",".join([str(p[0]) for p in mention.spans]),
                          "len": ",".join([str(p[1]) for p in mention.spans])})
            thisM = ElementTree.SubElement(mentions, "Mention", attrib = attrs)
            thisM.text = "\n      "
            lastN = None
            for norm in mention.meddraEntries:
                nAttrs = {"meddra_pt": norm[0], "meddra_pt_id": norm[1]}
                if norm[2] is not None:
                    nAttrs["meddra_llt"] = norm[2]
                if norm[3] is not None:
                    nAttrs["meddra_llt_id"] = norm[3]
                thisN = ElementTree.SubElement(thisM, "Normalization", attrib = nAttrs)
                if lastN is not None:
                    lastN.tail = "\n      "
                lastN = thisN
            if lastN is not None:
                lastN.tail = "\n    "
            if lastM is not None:
                lastM.tail = "\n    "
            lastM = thisM

        if lastM is not None:
            lastM.tail = "\n  "
        mentions.tail = "\n"

        s = '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(root, encoding = "utf-8")
        fp = open(path, "w")
        fp.write(s)
        fp.close()

    def _mentionAttributesForWrite(self, m):
        if m.reason:
            return {"reason": m.reason}
        else:
            return {}

# This differs from its parent in that:
# - its valid labels are only OSE_Labeled_AE
# - it accepts no reasons
# - it accepts only one MedDRA entry
        
class OSESubmissionEvalFormat(OSEGoldEvalFormat):

    ROOT_LABEL = "SubmissionLabel"

    VALID_MENTION_TYPES = set(["OSE_Labeled_AE"])

    OPTIONAL_MENTION_ATTRS = set()

    def _validateAndCreateMention(self, label, elem):
        m = OSEGoldEvalFormat._validateAndCreateMention(self, label, elem)
        #assert len(m.meddraEntries) == 1, "Mention {} has other than 1 normalization".format(m.id)
        if (m is not None) and (len(m.meddraEntries) > 1):
            print >> sys.stderr, "Warning: extra MedDDRA entries", m.meddraEntries[1:], "will be discarded for mention", m.id, "in label", label.fileBasename
            m.meddraEntries[1:] = []
        return m
    
    def _mentionAttributesForWrite(self, m):
        return {}
