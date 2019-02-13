# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# This file adaped from a portion of the scorer provided by NLM as part of the TAC 2017 ADR competition. See:
# https://bionlp.nlm.nih.gov/tac2017adversereactions/
# Heavily modified by MITRE.

# This file defines a reader/writer pair for the TAC format, which renders
# a Label to a file and a file to a Label.

# For the OSE evaluation, we want to be able to translate a TAC submission into
# an OSE submission. The limitation is that I need to be able to track the
# individual mentions from task 1 to task 4, which means the participants need
# to have generated the task 3 reaction strings by applying the task 2
# relation restrictions. So I have to check all of that.

from xml.etree import ElementTree
import os, re, sys

from .label import Label
from .ose_eval_format import OSESubmissionEvalFormat
from .meddra import MedDRADB

VALID_SECTION_NAMES = set(['adverse reactions', 'warnings and precautions',
                          'boxed warnings', "warnings", "precautions"])
VALID_MENTION_TYPES = set(['AdverseReaction', 'Severity', 'Factor', 'DrugClass',
                          'Negation', 'Animal'])
VALID_RELATION_TYPES = set(['Hypothetical', 'Effect', 'Negated'])

VALID_MENTION_OFFSETS = re.compile('^[0-9,]+$')

# Unfortunately, some of the NLM data, both train and test, have
# duplicate sections in them. There will be no such duplicates in the OSE
# training or test data. So WHEN THERE ARE DUPLICATES, it must be the
# output of a performer system on the TAC data inputs, which have the same
# signal as a subportion of the OSE training data. Below is a list
# of section IDs which should be kept when there are duplicates.
# For other data, the first instance will be chosen.

BRAND_KEEPS = {
    'SIVEXTRO': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'SAVELLA': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'ERIVEDGE': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'FOLOTYN': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'PREPOPIK': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'MEKINIST': [('adverse reactions', 'S2'), ('warnings and precautions', 'S4')],
    'LUZU': [('adverse reactions', 'S1')],
    'TRADJENTA': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'IMPAVIDO': [('adverse reactions', 'S2'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'LINZESS': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'RAPIVAB': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'CAPRELSA': [('adverse reactions', 'S2'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'ASCLERA': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'OFEV': [('adverse reactions', 'S1'), ('warnings and precautions', 'S4')],
    'ADEMPAS': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'LASTACAFT': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'LATUDA': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'BELVIQ': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'AUBAGIO': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'OSPHENA': [('adverse reactions', 'S1'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S5')],
    'ORBACTIV': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'ONGLYZA': [('adverse reactions', 'S2'), ('warnings and precautions', 'S4')],
    'HARVONI': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'RELISTOR': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'ICLUSIG': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'VOTRIENT': [('adverse reactions', 'S2'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S6')],
    'SYNRIBO': [('adverse reactions', 'S2'), ('warnings and precautions', 'S3')],
    'OPSUMIT': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'BELSOMRA': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'MOVANTIK': [('adverse reactions', 'S2'), ('warnings and precautions', 'S4')],
    'ANORO': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'DALIRESP': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'VIIBRYD': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'EDURANT': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'STIVARGA': [('adverse reactions', 'S2'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'EGRIFTA': [('adverse reactions', 'S2'), ('warnings and precautions', 'S4')],
    'POMALYST': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S6')],
    'BRILINTA': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'SOVALDI': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'KERYDIN': [('adverse reactions', 'S1')],
    'VIBATIV': [('adverse reactions', 'S2'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S6')],
    'KYNAMRO': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'XOFIGO': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'BANZEL': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'ISTODAX': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'ZIOPTAN': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'LUMASON': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'JUXTAPID': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'AKYNZEO': [('adverse reactions', 'S1'), ('warnings and precautions', 'S4')],
    'XARELTO': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'XELJANZ': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'EFFIENT': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'SAMSCA': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'ZONTIVITY': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'ELLA': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'ELELYSO': [('adverse reactions', 'S2'), ('warnings and precautions', 'S3')],
    'LEXISCAN': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'VICTOZA': [('adverse reactions', 'S2'), ('boxed warnings', 'S4'), ('warnings and precautions', 'S6')],
    'HETLIOZ': [('adverse reactions', 'S1'), ('warnings and precautions', 'S4')],
    'GATTEX': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'ZELBORAF': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'LIVALO': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'MYRBETRIQ': [('adverse reactions', 'S2'), ('warnings and precautions', 'S4')],
    'JAKAFI': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')],
    'STRIVERDI': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S5')],
    'FYCOMPA': [('adverse reactions', 'S1'), ('boxed warnings', 'S3'), ('warnings and precautions', 'S6')],
    'OLYSIO': [('adverse reactions', 'S1'), ('warnings and precautions', 'S3')]}

# The rule is that an AdverseReaction mention is non-positive if 
# it's (a) negated, or (b) hypothetical due to a drug class or animal.
# Hypotheticals with Factor dependencies count as positive.

class TACFormat:

    def __init__(self, strict = False, medasciiDir = None):
        self.strict = strict
        self.meddraDB = None
        if medasciiDir:
            self.meddraDB = MedDRADB(medasciiDir)
    
    # Reads in the XML file
    def read(self, file):
        root = ElementTree.parse(file).getroot()
        assert root.tag == 'Label', 'Root is not Label: ' + root.tag
        assert set(root.keys()) == set(["drug", "track"]), "Label attributes must be 'drug', 'track'"
        label = Label(os.path.basename(file), root.attrib['drug'], OSESubmissionEvalFormat.VALID_MENTION_TYPES)
        assert len(root) == 4, 'Expected 4 Children: ' + str(list(root))
        assert set([elt.tag for elt in root]) == set(["Text", "Mentions", "Relations", "Reactions"]), "First-level labels must be Text, Mentions, Relations, Reactions"
        topDict = {elt.tag: elt for elt in root}        
        pathBase = os.path.splitext(os.path.basename(file))[0]
        
        sectionIdsToIgnore = set()
        sectionNamesToIgnore = set()
        
        for elem in topDict["Text"]:
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
            existingSection = label.getSectionByName(sName)
            # If there's an existing section, and the file is in BRAND_KEEPS,
            # only keep the section which is listed there. Those documents will have
            # been the product of running performer systems on the NLM outputs, because
            # the OSE documents have no duplicate sections (and there are no guarantees
            # about what the section IDs are).
            if existingSection:
                # First, let's see if it's in BRAND_KEEPS.
                bEntry = BRAND_KEEPS.get(pathBase)
                # If it's not in BRAND_KEEPS, just discard the current one.
                if not bEntry:
                    print >> sys.stderr, "WARNING: for %s: discarding section '%s' (%s) due to NLM duplication (kept first)" % (pathBase, sName, sId)
                    sectionIdsToIgnore.add(sId)
                    sectionNamesToIgnore.add(sName)
                else:
                    # Otherwise, if there IS a BRAND_KEEPS entry,
                    # make sure that the section you keep is the right one.
                    if (sName, existingSection.id) not in bEntry:
                        print >> sys.stderr, "WARNING: for %s: discarding section '%s' (%s) due to NLM duplication (kept recorded)" % (pathBase, sName, existingSection.id)
                        label.removeSection(existingSection)
                        sectionIdsToIgnore.add(existingSection.id)
                        sectionNamesToIgnore.add(sName)
                    if (sName, sId) in bEntry:
                        label.addSection(sId, sName, elem.text)
                    else:
                        print >> sys.stderr, "WARNING: for %s: discarding section '%s' (%s) due to NLM duplication (kept first)" % (pathBase, sName, sId)
                        sectionIdsToIgnore.add(sId)
                        sectionNamesToIgnore.add(sName)
            else:
                label.addSection(sId, sName, elem.text)

        # If skipping sections meant we missed some names, that's a problem.
        for sName in sectionNamesToIgnore:
            if not label.getSectionByName(sName):
                raise Exception, "ignored section named '%s' without a replacement" % sName

        # So I won't RECORD the mentions until I know which ones are
        # positive and which ones aren't, and I can't know that until
        # after I collect both the mentions and the relations. If there
        # are no relations, we can assume that the document can't be
        # digested. Ditto if there are no mentions.

        # Belay that. If there are no relations, then
        # there's the chance that the tool didn't actually
        # filter any mentions. So if all the mentions are
        # accounted for in the reactions, then we should be
        # OK. The problem comes if they applied the filter without
        # having relations, or if the set of unique reaction strings
        # isn't identical to the set of mention unique strings.

        if (len(topDict["Mentions"]) == 0) and (len(topDict["Reactions"]) > 0):
            raise Exception, "reactions but no mentions for label '{}'; can't interpret as OSE submission".format(label.drug)

        mentions = set()
        ignoredUniqueStrings = set()
        arCandidates = {}
        peripheralCandidates = {}
        
        for elem in topDict["Mentions"]:
            assert elem.tag == 'Mention', 'Expected \'Mention\': ' + elem.tag
            mId = self._attrib("id", elem)
            assert mId is not None, "Mention missing ID attribute"
            assert set(["id", "section", "type", "start", "len"]) - set(elem.keys()) == set(), \
              "Mention {} attributes must contain at least 'section', 'type', 'start', 'len'".format(mId)
            remainingAttrs = set(["id", "section", "type", "start", "len", "str"]) - set(elem.keys())
            assert remainingAttrs == set(), "Unknown Mention {} attributes {}".format(mId, ", ".join(["'%s'" % a for a in remainingAttrs]))
            assert mId.startswith('M'), \
                'Mention ID does not start with M: ' + mId
            assert mId not in mentions, \
                'Duplicate Mention ID: ' + mention.id
            sId = elem.attrib['section']
            mStart = elem.attrib["start"]
            assert VALID_MENTION_OFFSETS.match(mStart), \
                'Invalid start attribute: ' + mStart
            mLen = elem.attrib["len"]
            assert VALID_MENTION_OFFSETS.match(mLen), \
                'Invalid len attribute: ' + mLen
            mType = elem.attrib["type"]
            assert mType in VALID_MENTION_TYPES, \
                'Invalid Mention type: ' + mType

            mStr = self._attrib('str', elem)
            mentions.add(mId)
            if sId in sectionIdsToIgnore:
                # Just record the mStr if it's available.
                if mStr:
                    ignoredUniqueStrings.add(mStr.lower())
            else:
                assert label.getSectionByID(sId) is not None, \
                  'No such section in label: ' + sId

                # This isn't quite getUniqueString(). It preserves peripheral whitespace
                # in the individual spans.
                text = ''
                for sstart, slen in zip(mStart.split(','), mLen.split(',')):
                    start = int(sstart)
                    end = start + int(slen)
                    if len(text) > 0:
                        text += ' '
                    span = label.getSectionByID(sId).text[start:end]
                    span = re.sub('\s+', ' ', span)
                    text += span
                if mStr is not None:
                    assert text == mStr, 'Mention has wrong string value.' + \
                        '  From \'str\': \'' + mStr + '\'' + \
                        '  From offsets: \'' + text + '\''
                else:
                    # Unlike the original WFC checker, I always want to have the
                    # mention string, because I want to make sure that the inventory
                    # of positive unique strings doesn't contain anything that
                    # isn't here.
                    mStr = text
                if mType == "AdverseReaction":
                    # The last position is for the relations.
                    arCandidates[mId] = (mId, sId, mStart, mLen, mStr.lower(), [])
                else:
                    peripheralCandidates[(mId, sId)] = mType

        relations = set()
        
        for elem in topDict["Relations"]:
            assert elem.tag == 'Relation', 'Expected \'Relation\': ' + elem.tag
            rId = self._attrib("id", elem)
            assert rId is not None, "Relation missing ID attribute"
            assert set(["id", "type", "arg1", "arg2"]) == set(elem.keys()), \
              "Relation {} attributes must be 'id', 'type', 'arg1', 'arg2'".format(rId)
            assert rId.startswith('RL'), \
                'Relation ID does not start with RL: ' + rId
            assert rId not in relations, \
                'Duplicate Relation ID: ' + rId
            relations.add(rId)
            rType = elem.attrib["type"]
            assert rType in VALID_RELATION_TYPES, \
                'Invalid Relation type: ' + rType
            rArg1 = elem.attrib["arg1"]
            rArg2 = elem.attrib["arg2"]
            assert rArg1 in mentions, \
                'Relation ' + rId + ' arg1 not in mentions: ' + rArg1
            assert rArg2 in mentions, \
                'Relation ' + rId + ' arg2 not in mentions: ' + rArg2
            assert rArg1 != rArg2, \
                'Relation arguments identical (self-relation)'
            m = arCandidates.get(rArg1)
            if m is not None:
                argType = peripheralCandidates.get((rArg2, m[1]))
                if argType is not None:
                    # argType is now the mention type of the argument.
                    # Accumulate the relation and argument type; that's all we really need
                    # to do the mentions.
                    m[-1].append((rType, argType))

        # At this point, I should be able to look through the arCandidates and see
        # which ones are positive.

        arMentions = {}
        uniqueStrs = {}

        for (mId, sId, mStart, mLen, mStr, rels) in arCandidates.values():

            # The rule is that an AdverseReaction mention is non-positive if 
            # it's (a) negated, or (b) hypothetical due to a drug class or animal.
            # Hypotheticals with Factor dependencies count as positive.

            relNames = set([r[0] for r in rels])
            if ("Negated" not in relNames) and \
               (("Hypothetical", "DrugClass") not in rels) and \
               (("Hypothetical", "Animal") not in rels):
               
                arMentions[mId] = (mId, sId, mStart, mLen)
                try:
                    uniqueStrs[mStr].add(mId)
                except KeyError:
                    uniqueStrs[mStr] = set([mId])

        # Can't make the mentions quite yet, because now I have to look at the reactions
        # and find the normalizations. If there's a unique string that doesn't
        # correspond to a mention, this label can't be digested. And if there is,
        # save the normalization.

        reactions = set()
        reStrs = set()
        discardedReactions = set()

        for elem in topDict["Reactions"]:
            assert elem.tag == 'Reaction', 'Expected \'Reaction\': ' + elem.tag
            reId = self._attrib("id", elem)
            assert reId is not None, "Reaction missing ID attribute"
            assert set(["id", "str"]) == set(elem.keys()), \
              "Reaction {} attributes must be 'id', 'str'".format(reId)
            assert reId.startswith('AR'), \
                'Reaction ID does not start with AR: ' + reId
            assert reId not in reactions, \
                'Duplicate Reaction ID: ' + reId
            reStr = elem.attrib["str"]
            assert reStr.lower() == reStr, \
                'Reaction str is not lower-case: ' + reStr
            reStrs.add(reStr)
            try:
                mentionIds = uniqueStrs[reStr]
            except KeyError:
                if reStr not in ignoredUniqueStrings:
                    discardedReactions.add(reStr)
                continue

            # OK, so now we have the candidate mentions. Now we collect
            # the normalizations and apply all of them to each mention.

            meddraEntries = []

            unmapped = False

            for elem2 in elem:
                assert elem2.tag == 'Normalization', 'Expected \'Normalization\': ' + elem2.tag
                nId = self._attrib("id", elem2)
                assert nId is not None, "Normalizationmissing ID attribute"                
                assert nId.startswith('AR'), \
                    'Normalization ID does not start with AR: ' + nId
                assert nId.find('.N') > 0, \
                    'Normalization ID does not contain .N: ' + nId
                remainingAttrs = set(elem2.keys()) - set(["id", "meddra_pt", "meddra_pt_id", "meddra_llt", "meddra_llt_id", "flag"])
                assert remainingAttrs == set(), "Unknown Normalization {} attributes {}".format(mId, ", ".join(["'%s'" % a for a in remainingAttrs]))
                mPt = self._attrib("meddra_pt", elem2)
                nFlag = self._attrib("flag", elem2)
                assert mPt or nFlag == 'unmapped', \
                    'Normalization does not contain meddra_pt and is not unmapped: ' + \
                    label.drug + ':' + nId

                mPtId = self._attrib('meddra_pt_id', elem2)
                mLLT = self._attrib('meddra_llt', elem2)
                mLLTId = self._attrib('meddra_llt_id', elem2)

                # OSE label requires MedDRA PT and PT ID.

                if mPt and mPtId:
                    meddraEntries.append((mPt, mPtId, mLLT, mLLTId))
                    if self.meddraDB:
                        # I don't want to raise an error when I check the WFC, because we know that we're using
                        # a different version of MedDRA.
                        self.meddraDB.checkWFC(label.fileBasename, mId, mPt, mPtId, mLLT, mLLTId, raiseError = False)
                elif nFlag == "unmapped":
                    unmapped = True

            if unmapped:
                continue
            
            assert len(meddraEntries) > 0, "No Normalizations for Mentions {}".format(", ".join(mentionIds))

            for mId in mentionIds:
                mId, sId, mStart, mLen = arMentions[mId]
                label.getSectionByID(sId).addMention(mId, "OSE_Labeled_AE",
                                                     zip([int(ist.strip()) for ist in mStart.split(",")], [int(ist.strip()) for ist in mLen.split(",")]),
                                                     meddraEntries[0][0], meddraEntries[0][1],
                                                     meddra_llt = meddraEntries[0][2], meddra_llt_id = meddraEntries[0][3],
                                                     other_meddra_info = meddraEntries[1:])

        if set(uniqueStrs.keys()) - reStrs:
            if relations:
                msg = "discarded positive mentions found which aren't among unique strings: " + ", ".join(['"' + s + "'" for s in sorted(set(uniqueStrs.keys()) - reStrs)])
                if self.strict:
                    raise Exception, msg
                else:
                    print "WARNING:", msg
            else:
                raise Exception, "positive mentions found which aren't among unique strings (no relations found to filter the mentions)"

        if discardedReactions:

            msg = "discarded reaction strings because they don't correspond to any positive mention: " + ", ".join(['"'+s+'"' for s in sorted(discardedReactions)])
            if self.strict:
                raise Exception, msg
            else:
                print "WARNING:", msg
                
        return label

    def _attrib(self, name, elem):
        if name in elem.attrib:
            return elem.attrib[name]
        else:
            return None
    
    def write(self, label, path):
        raise Exception, "Writing not supported for the TAC format"
