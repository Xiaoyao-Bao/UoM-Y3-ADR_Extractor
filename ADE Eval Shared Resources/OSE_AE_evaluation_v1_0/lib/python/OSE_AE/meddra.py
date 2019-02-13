# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# Here, we load the contents of the MedAscii directory for optional wellformedness checking.
# I'm going to do this as a case insensitive lookup for the names, because
# when we convert TAC submissions, LOTS of them have lowercase MedDRA names.

import os, sys

class MedDRADB:

    def __init__(self, medasciiDir):

        # I want, specifically, pt.asc and llt.asc.

        ptFile = os.path.join(medasciiDir, "pt.asc")
        if not os.path.exists(ptFile):
            raise Exception, ("MedAscii directory %s doesn't contain pt.asc" % medasciiDir)
        lltFile = os.path.join(medasciiDir, "llt.asc")
        if not os.path.exists(lltFile):
            raise Exception, ("MedAscii directory %s doesn't contain llt.asc" % medasciiDir)

        self.lltNameToCode = {}
        self.lltCodeToName = {}
        self.lltCodeToPTCode = {}
        self.ptCodeToName = {}
        self.ptNameToCode = {}
        
        # First, read in the low level terms.
        # The first fields are llt code and name, and then PT code.
        fp = open(os.path.join(lltFile), "r")
        for line in fp.readlines():
            toks = line.strip().split("$")[:-1]
            lltCode, lltName, ptCode = toks[:3]
            lltName = lltName.lower()
            self.lltNameToCode[lltName] = lltCode
            self.lltCodeToName[lltCode] = lltName
            self.lltCodeToPTCode[lltCode] = ptCode
        fp.close()

        # Now, read in the preferred terms. The first two fields are all I want: code and name.
        fp = open(os.path.join(lltFile), "r")
        for line in fp.readlines():
            toks = line.strip().split("$")[:-1]
            ptCode, ptName = toks[:2]
            ptName = ptName.lower()
            self.ptCodeToName[ptCode] = ptName
            self.ptNameToCode[ptName] = ptCode
        fp.close()

    def checkWFC(self, labelName, mentionID, ptName, ptCode, lltName, lltCode, raiseError = False):
        
        def _raiseOrWarn(msg):
            if raiseError:
                raise Exception, msg
            else:
                print >> sys.stderr, "Warning:", msg
                
        lookupLLTName = lltName
        if lookupLLTName:
            lookupLLTName = lookupLLTName.lower()
        lookupPTName = ptName
        if lookupPTName:
            lookupPTName = lookupPTName.lower()

        if lltName and (not self.lltNameToCode.has_key(lookupLLTName)):
            _raiseOrWarn("unknown low-level term '%s' for mention %s in label %s" % (lltName, mentionID, labelName))
        if lltCode:
            if not self.lltCodeToPTCode.has_key(lltCode):
                _raiseOrWarn("unknown low-level term code '%s' for mention %s in label %s" % (lltCode, mentionID, labelName))                
            elif self.lltCodeToPTCode[lltCode] != ptCode:
                _raiseOrWarn("low-level term code '%s' does not map to preferred term code '%s' for mention %s in label %s" % (lltCode, ptCode, mentionID, labelName))
        if lltCode and lltName and self.lltNameToCode.has_key(lookupLLTName) and (self.lltNameToCode[lookupLLTName] != lltCode):
            _raiseOrWarn("low-level term '%s' does not match code '%s' for mention %s in label %s" % (lltName, lltCode, mentionID, labelName))
        if not self.ptCodeToName.has_key(ptCode):
            _raiseOrWarn("unknown preferred term code '%s' for mention %s in label %s" % (ptCode, mentionID, labelName))
        if ptName:
            if not self.ptNameToCode.has_key(lookupPTName):
                _raiseOrWarn("unknown preferred term '%s' for mention %s in label %s" % (ptName, mentionID, labelName))
            elif self.ptNameToCode[lookupPTName] != ptCode:
                _raiseOrWarn("preferred term '%s' does not match code '%s' for mention %s in label %s" % (ptName, ptCode, mentionID, labelName))
