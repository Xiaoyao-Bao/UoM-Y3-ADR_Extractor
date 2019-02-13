# Copyright (C) 2018 The MITRE Corporation. See the toplevel
# file LICENSE.txt for license terms.

# The guts of this code is a massively refactored and expanded version
# of the scorer from the TAC ADR 2017 evaluation.

import random, math, csv, sys
from .corpus import GuessCorpus

#
# Pairer
#

# The algorithm uses the Kuhn-Munkres bipartite set alignment algorithm
# to determine the best match between gold and submission mentions. To optimize
# the application of K-M, we segregate the mentions by regions which are entirely
# empty of mentions (because only annotations which overlap can pair at all)
# and apply K-M to the mentions within these boundaries. This algorithm
# is a simplification of the more general K-M-based algorithm from the
# MITRE Annotation Toolkit (http://mat-annotation.sf.net).

# K-M requires a similarity measure. For this eval, first the span overlap is
# computed, as the ratio of the intersection of the set of character offsets
# to the union of the set of character offsets. This is the easiest way to
# compare potentially discontinuous mentions. If the overlap is non-zero, we
# multiply it by .8 and then compare the MedDRA PT IDs; if the submission ID
# is one of the gold IDs, we add .2, otherwise not. If the overlap is 0, the
# similarity is 0.

from munkres import Munkres, make_cost_matrix

class PairSet:

    def __init__(self, goldSection, submissionSection):
        self.goldSection = goldSection
        self.submissionSection = submissionSection
        goldAnnots = [m for m in goldSection.getNonIgnoredMentions() if m.type == "OSE_Labeled_AE"]
        subAnnots = submissionSection.getNonIgnoredMentions()
        # missing will be a list of gold mentions
        self.missing = []
        # spurious will be a list of submission
        self.spurious = []
        # pairs will be a list of (gold mention, submission mention, (sim, clash list)).
        self.pairs = []
        self._pairAnnotations(goldAnnots, subAnnots)

    def _pairAnnotations(self, goldAnnots, subAnnots):

         # Step 1: collect the ends and starts.

        idxHash = {}
        for a in goldAnnots:
            # spans are start, len
            try:
                idxHash[a.spans[0][0]]["starts"]["gold"].append(a)
            except KeyError:
                idxHash[a.spans[0][0]] = {"starts": {"gold": [a], "submission": []}, "ends": {"gold": [], "submission": []}}
            e = a.spans[-1][0] + a.spans[-1][1]
            try:
                idxHash[e]["ends"]["gold"].append(a)
            except KeyError:
                idxHash[e] = {"starts": {"gold": [], "submission": []}, "ends": {"gold": [a], "submission": []}}
        for a in subAnnots:
            # spans are start, len
            try:
                idxHash[a.spans[0][0]]["starts"]["submission"].append(a)
            except KeyError:
                idxHash[a.spans[0][0]] = {"starts": {"gold": [], "submission": [a]}, "ends": {"gold": [], "submission": []}}
            e = a.spans[-1][0] + a.spans[-1][1]
            try:
                idxHash[e]["ends"]["submission"].append(a)
            except KeyError:
                idxHash[e] = {"starts": {"gold": [], "submission": []}, "ends": {"gold": [], "submission": [a]}}

        # Now, for each region where mentions occur, call the pairer.
        # Loop through the indices in order. Remove the things that
        # are ending. If the remaining set is empty and there were annotations
        # collected, call the pairer on the region and clear the collections.
        # Then add the things that are starting. 

        curAnnotations = set()
        goldInRegion = set()
        submissionInRegion = set()
        
        for idx in sorted(idxHash.keys()):
            idxEntry = idxHash[idx]
            # First, we remove the ones that are ending.
            curAnnotations -= set(idxEntry["ends"]["gold"] + idxEntry["ends"]["submission"])
            if not curAnnotations:
                if goldInRegion or submissionInRegion:
                    self._pairRegions(goldInRegion, submissionInRegion)
                    goldInRegion = set()
                    submissionInRegion = set()
            curAnnotations |= set(idxEntry["starts"]["gold"] + idxEntry["starts"]["submission"])
            goldInRegion |= set(idxEntry["starts"]["gold"])
            submissionInRegion |= set(idxEntry["starts"]["submission"])
            
        if goldInRegion or submissionInRegion:
            raise Exception, "we should never be here: either gold or submissions has annotations left after all regions are passed"

    def _pairRegions(self, refAnnots, hypAnnots):

        def annInfo(annot):
            # We don't need the label, but we do need the
            # set of offset indices, and also the MedDRA PT IDs,
            # as a set.
            indices = set()
            for s, l in annot.spans:
                indices |= set(range(s, s + l))
            return indices, set([e[1] for e in annot.meddraEntries])
        
        # Similarity is mostly overlap, a bit label.        
        def computeSimilarity(annotAtuple, annotBtuple, cache):
            a, (aIndices, aCodes) = annotAtuple
            b, (bIndices, bCodes) = annotBtuple
            try:
                return cache[(a, b)][0]
            except KeyError:
                pass
            overlap = len(aIndices & bIndices)/float(len(aIndices | bIndices))
            clashes = {}
            # If they don't overlap, they're not a pair, period.
            if overlap == 0:
                cache[(a, b)] = (0, [])
                return 0
            if overlap < 1.0:
                clashes["spanclash"] = overlap
            meddraMatches = False
            if aCodes & bCodes:
                meddraMatches = True
            else:
                clashes["meddraclash"] = True
            if not clashes:
                sim = 1.0
            elif not meddraMatches:
                sim = .8 * overlap
            else:
                sim = .2 + (.8 * overlap)
            cache[(a, b)] = (sim, clashes)
            return sim
        
        # Now, we have to compute the similarities and use munkres to align them.
        # This is taken pretty much exactly from the MAT scorer.
        missing = []
        spurious = []
        paired = []
        simCache = {}
        if refAnnots and hypAnnots:
            
            refAnnotPairs = [(a, annInfo(a)) for a in refAnnots]
            hypAnnotPairs = [(a, annInfo(a)) for a in hypAnnots]
            
            if (len(refAnnots) == 1) and (len(hypAnnots) == 1):
                # If they overlap, they're paired. Otherwise, no.
                sim = computeSimilarity(refAnnotPairs[0], hypAnnotPairs[0], simCache)
                if sim > 0:
                    paired = [(refAnnotPairs[0], hypAnnotPairs[0])]
                else:
                    spurious = list(hypAnnots)
                    missing = list(refAnnots)
            else:
                # Here is where we need munkres.
                matrix = make_cost_matrix([[computeSimilarity(r, h, simCache) for h in hypAnnotPairs] for r in refAnnotPairs],
                                          lambda cost: 1.0 - cost)
                indexPairs = Munkres().compute(matrix)
                for row, column in indexPairs:
                    try:
                        rAnn = refAnnotPairs[row]
                    except IndexError:
                        # hyp matched with nothing.
                        spurious.append(hypAnnotPairs[column])
                        continue
                    try:
                        hAnn = hypAnnotPairs[column]
                    except IndexError:
                        # ref matched with nothing.
                        missing.append(refAnnotPairs[row][0])
                        continue
                    # So now, what's their similarity?
                    if simCache[(rAnn[0], hAnn[0])][0] == 0:
                        spurious.append(hAnn[0])
                        missing.append(rAnn[0])
                    else:
                        paired.append((rAnn, hAnn))
                # Some of the elements aren't paired. They need to be in missing
                # or spurious.
                if len(indexPairs) < max(len(refAnnotPairs), len(hypAnnotPairs)):
                    allRef = set(missing) | set([r[0] for (r, h) in paired])
                    allHyp = set(spurious) | set([h[0] for (r, h) in paired])
                    missing += list(refAnnots - allRef)
                    spurious += list(hypAnnots - allHyp)
        elif refAnnots:
            missing = list(refAnnots)
        elif hypAnnots:        
            spurious = list(hypAnnots)
        self.pairs += [(p1[0], p2[0], simCache[(p1[0], p2[0])]) for (p1, p2) in paired]
        self.missing += missing
        self.spurious += spurious

#
# Aggregation of scores
#

# The idea here is that there are two types of
# scores, micro and macro. The aggregations for each
# are different, when you macro-average you essentially
# grab the micro scores and then use those scores
# as the aggregations for the next levels up.

# The aggregator wants to know the identity of the
# elements it's storing, in order to generate the detail spreadsheet.

class Aggregator:

    def __init__(self, metric):
        self.metric = metric
        self.children = []
        self.finished = False
        
    def addChild(self, aggr):
        self.children.append(aggr)

    def finish(self):
        if not self.finished:
            for c in self.children:
                c.finish()
                self.fromChild(c)
            self.finished = True

    def _prf(self, match, clash, missing, spurious):
        refTotal = clash + missing + match
        hypTotal = clash + spurious + match
        if hypTotal == 0:
            precision = 1.0
        else:
            precision = match/float(hypTotal)
        if refTotal == 0:
            recall = 1.0
        else:
            recall = match/float(refTotal)
        if (precision == 0) and (recall == 0):
            fMeasure = 0.0
        else:
            fMeasure = 2 * ((precision * recall) / float(precision + recall))
        return precision, recall, fMeasure

    def addRow(self, runName, rowPrefix, metricName, summaryWriter):
        summaryWriter.addRow(runName, rowPrefix, metricName, self.summaryRow())

class MicroAggregator(Aggregator):

    def __init__(self, metric):
        Aggregator.__init__(self, metric)
        self.match = []
        self.missing = []
        self.spurious = []
        self.clash = []

    def insert(self, match, clash, missing, spurious):
        # These are just going to be counts.
        self.match += match
        self.missing += missing
        self.spurious += spurious
        self.clash += clash

    # The child will always be a microaggregator.

    def fromChild(self, child):
        self.insert(child.match, child.clash, child.missing, child.spurious)

    # Now, how do you compute it? You're only asked for
    # this at the end.
        
    # This should return precision, recall, f-measure.
    
    def compute(self):
        return self._prf(*self.metric.compute(self))

    def writeStdout(self, metric):
        print('--------------------------------------------------')
        print('Results: %s' % metric)
        vals = self.metric.compute(self)
        p, r, f = self._prf(*vals)

        print('    Match: {}  clash: {}  missing: {}  spurious: {}'.format(*vals))
        print('    Precision: {:.2f}'.format(p))
        print('    Recall:    {:.2f}'.format(r))
        print('    F1:        {:.2f}'.format(f))

    def summaryRow(self):
        vals = self.metric.compute(self)
        p, r, f = self._prf(*vals)
        return list(vals) + [p, r, f]

class NonReportingMicroAggregator(MicroAggregator):

    # Adds nothing to the summary.
    def addRow(self, runName, rowPrefix, metricName, summaryWriter):
        pass

class MacroAggregator(Aggregator):
    
    def __init__(self, metric):
        Aggregator.__init__(self, metric)
        self.precisions = []
        self.recalls = []
        self.fmeasures = []

    # insert is never called on a regular MacroAggregator; only fromChild.

    def fromChild(self, child):
        self.precisions += child.precisions
        self.recalls += child.recalls
        self.fmeasures += child.fmeasures

    # Pretty sure this is always the same for macro.
    def compute(self):
        prec = sum(self.precisions)/float(len(self.precisions))
        rec = sum(self.recalls)/float(len(self.recalls))
        f = sum(self.fmeasures)/float(len(self.fmeasures))
        return prec, rec, f

    def writeStdout(self, metric):
        print('--------------------------------------------------')
        print('Results: %s' % metric)
        p, r, f = self.compute()

        print('    Macro-Precision: {:.2f}'.format(p))
        print('    Macro-Recall:    {:.2f}'.format(r))
        print('    Macro-F1:        {:.2f}'.format(f))

    def summaryRow(self):
        return ([None] * 4) + list(self.compute())
    
# I'd like to be able to capture the match/clash/missing/spurious
# at the level of conversion, so I can report them in the summary.
# This has to be a combination of a microaggregator and a macroaggregator.
# You shouldn't populate the p/r/f until finish() is called.

class ConvertingMacroAggregator(MacroAggregator):

    def __init__(self, metric, macroConvertor):
        MacroAggregator.__init__(self, metric)
        self.macroConvertor = macroConvertor
        self.microAggregator = MicroAggregator(self.metric)
        self.matchCount = self.clashCount = self.missingCount = self.spuriousCount = 0

    def insert(self, match, clash, missing, spurious):
        self.microAggregator.insert(match, clash, missing, spurious)

    def fromChild(self, child):
        self.microAggregator.fromChild(child)

    def finish(self):
        if not self.finished:
            MacroAggregator.finish(self)
            match, clash, missing, spurious = self.macroConvertor(self.microAggregator.match, self.microAggregator.clash,
                                                                  self.microAggregator.missing, self.microAggregator.spurious)
            # This is the output of the importer. So there will be
            # a macroConvertor and it must be applied.
            self.matchCount = match
            self.clashCount = clash
            self.missingCount = missing
            self.spuriousCount = spurious
            p, r, f = self._prf(match, clash, missing, spurious)
            self.precisions.append(p)
            self.recalls.append(r)
            self.fmeasures.append(f)

    # It makes no sense for this to be at the root.
    # So let's assume that writeStdout() isn't called.
    
    def summaryRow(self):
        return [self.matchCount, self.clashCount, self.missingCount, self.spuriousCount] + list(self.compute())
    
#
# Metrics
#

# Each metric defines a stack of aggregators, working
# up from the leaf, which is always a MicroAggregator. It may
# have multiple paths. The aggregators have children. The 
# computations are computed lazily; each level asks its
# children, and the metric will specialize the promotor
# to know when the computation needs to happen.

# Actually, maybe a bit more than this. Each metric has
# an importer that takes the pair state. Then, it has a
# convertor to macro, maybe. At what level the macro
# convertor happens is defined in the level list.

# E.g., [("section", self.sectId), ("label", self.labelId, self.convert), ("corpus", lambda *args: None)]
# defines a stack where we import to section, then
# convert on the way to the label level, and then
# aggregate to corpus as a macro aggregator. each level
# has a method that extracts the ID for that level from
# the base section.

# That's not enough, because the counter for the aggregator
# has to be able to weight the contributions, and that's
# not happening yet.

class LevelStack:

    def __init__(self, metric, stack):
        self.metric = metric
        self.stackCache = {}
        self.stack = []
        self.hasConvertor = False
        for entry in stack:
            if entry.macroConvertor or (entry.aggregatorClass and issubclass(entry.aggregatorClass, ConvertingMacroAggregator)):
                if self.hasConvertor:
                    raise Exception, ("too many macro convertors", stack)
                self.hasConvertor = True
            self.stack.append(entry)

    def climbStack(self, impResult, pairSet):

        # At the bottom, if the index is already found,
        # it's an error. If there's a macro convertor, we
        # apply the importer and then the macro convertor
        # and then build a MacroAggregator. Otherwise, we just apply
        # the importer and build a MicroAggregator.

        # Because we're not actually pushing the scores up here, but
        # merely setting up the parent/child links, we should stop
        # as soon as a parent aggregator is found (because if it's
        # found, the rest of the hierarchy above has alraedy been set up).

        # So we need a bit more granularity for reporting. The
        # macro aggregator will have a subtype which is the converting
        # aggregator, and everything below that should be a nonreporting micro aggregator.

        first = True
        childAggregator = None
        
        for entry in self.stack:
            level = entry.name
            idExtractor = entry.levelIndex
            macroConvertor = entry.macroConvertor
            levelId = idExtractor(pairSet.goldSection)
            try:
                cache = self.stackCache[level]
            except KeyError:
                cache = {}
                self.stackCache[level] = cache
            if first:
                if cache.has_key(levelId):
                    raise Exception, "no index duplication permitted at task leaves"
                if entry.aggregatorClass:
                    childAggregator = entry.aggregatorClass(self.metric)
                elif macroConvertor:
                    childAggregator = ConvertingMacroAggregator(self.metric, macroConvertor)
                elif self.hasConvertor:
                    childAggregator = NonReportingMicroAggregator(self.metric)
                else:
                    childAggregator = MicroAggregator(self.metric)
                childAggregator.insert(*impResult)
                childAggregator.finish()
                cache[levelId] = childAggregator
            else:
                try:
                    parentAggregator = cache[levelId]
                    # Add the child and break.
                    parentAggregator.addChild(childAggregator)
                    break
                except KeyError:
                    # What kind of parent?
                    if entry.aggregatorClass:
                        parentAggregator = entry.aggregatorClass(self.metric)
                    elif macroConvertor:
                        parentAggregator = ConvertingMacroAggregator(self.metric, macroConvertor)
                    elif isinstance(childAggregator, MacroAggregator):
                        parentAggregator = MacroAggregator(self.metric)
                    else:
                        parentAggregator = MicroAggregator(self.metric)                        
                    cache[levelId] = parentAggregator
                    parentAggregator.addChild(childAggregator)
                    childAggregator = parentAggregator
            first = False

        def finish(self):
            try:
                self.stackCache[self.stack[-1][0]].finish()
            except KeyError:
                pass        

#
# Stack levels embody the information that needs to be reported.
#

class StackLevel:

    name = None

    def __init__(self, macroConvertor = None, aggregatorClass = None):
        self.macroConvertor = macroConvertor
        self.aggregatorClass = aggregatorClass

    # The index has to be the row prefix for the summary.
    def levelIndex(self, section):
        raise Exception, "not implemented"

    def rowHeaderPrefix(self, section):
        raise Exception, "not implemented"

class SectionStackLevel(StackLevel):

    name = "section"

    def levelIndex(self, sect):
        return (sect.label.fileBasename, sect.name)

    def rowHeaderPrefix(self):
        return ["file_basename", "section_type"]

class LabelStackLevel(StackLevel):

    name = "label"

    def levelIndex(self, sect):
        return (sect.label.fileBasename,)

    def rowHeaderPrefix(self):
        return ["file_basename"]

class SectionTypeStackLevel(StackLevel):

    name = "section_type"

    def levelIndex(self, sect):
        return (sect.name,)

    def rowHeaderPrefix(self):
        return ["section_type"]

class CorpusStackLevel(StackLevel):

    name = "corpus"

    def levelIndex(self, sect):
        return ()

    def rowHeaderPrefix(self):
        return []

class Metric:
    
    name = None

    def __init__(self, results, levelStacks):
        # There may be only one sequence; i.e., levelStacks may
        # be levelStack.
        
        if type(levelStacks[0]) not in (tuple, list):
            levelStacks = [levelStacks]
        self.results = results
        self.levelStacks = [LevelStack(self, e) for e in levelStacks]

    # This is pretty much all you should need, I think.

    def eval_section(self, pairSet):
        impResult = self.importFromPairSet(pairSet)
        for stack in self.levelStacks:
            stack.climbStack(impResult, pairSet)

    # Returns lists of match, clash, missing, spurious.
    
    def importFromPairSet(self, pairSet):
        raise Exception, "not defined"

    # This is only called when the aggregator is a microaggregator.
    def compute(self, aggregator):
        raise Exception, "not defined"

    def writeStdout(self):
        # Only write the corpus scores.
        for stack in self.levelStacks:
            if isinstance(stack.stack[-1], CorpusStackLevel) and stack.stackCache.has_key(stack.stack[-1].name):
                # The label "corpus" is significant. There will be only one.
                corpusAggregator = stack.stackCache[stack.stack[-1].name].values()[0]
                corpusAggregator.finish()
                corpusAggregator.writeStdout(self.name)
        #for stack in self.levelStacks:
        #    try:
        #        labelCache = stack.stackCache["label"]
        #        for key, aggr in labelCache.items():
        #            goldCorpus = self.results.goldCorpus
        #            import os
        #            goldLabel = goldCorpus.labels[os.path.splitext(key)[0]]
        #            guessCorpus = self.results.guessCorpus
        #            guessLabel = guessCorpus.labels[os.path.splitext(key)[0]]
        #            pairSets = [ps for (l1, l2, ignore, ignore, ps) in self.results.pairSets if (goldLabel is l1) and (guessLabel is l2)]
        #            print key
        #            print "  Gold annots:", sum([len([m for m in s.getNonIgnoredMentions() if m.type == "OSE_Labeled_AE"]) for s in goldLabel.sections])
        #            print "  Guess annots:", sum([len([m for m in s.getNonIgnoredMentions() if m.type == "OSE_Labeled_AE"]) for s in guessLabel.sections])
        #            print "  Aggregation:", "match", len(aggr.match), "clash", len(aggr.clash), "missing", len(aggr.missing), "spurious", len(aggr.spurious)
        #            print "  Pairs:", "pairs", sum([len(ps.pairs) for ps in pairSets]), "missing", sum([len(ps.missing) for ps in pairSets]), "spurious", sum([len(ps.spurious) for ps in pairSets])
        #    except KeyError:
        #        raise

    def writeSummaries(self, runName, summaryHash, significant_digits = None,
                       compute_confidence_data = False):
        levelsCovered = set()
        for stack in self.levelStacks:
            for entry in stack.stack:
                level = entry.name
                if level not in levelsCovered:
                    levelsCovered.add(level)
                    try:
                        cache = stack.stackCache[level]
                    except KeyError:
                        continue
                    # OK, now what? Each key is the row prefix.
                    try:
                        summary = summaryHash[level]
                    except KeyError:
                        summary = SummaryRowFormatter(header_prefix = entry.rowHeaderPrefix(), significant_digits = significant_digits,
                                                      compute_confidence_data = compute_confidence_data)
                        summaryHash[level] = summary
                    for rowPrefix, aggregator in cache.items():
                        aggregator.finish()
                        aggregator.addRow(runName, rowPrefix, self.name, summary)

# Identical to TAC Metric1 for the moment, except that it's just ARs.
    
class OSEMetric1(Metric):

    name = "Exact mention match - unweighted"

    def __init__(self, results):
        levels = [[SectionStackLevel(), LabelStackLevel(), CorpusStackLevel()],
                  [SectionStackLevel(), SectionTypeStackLevel()]]
        Metric.__init__(self, results, levels)                        

    def importFromPairSet(self, pairSet):

        # Match is perfect, clash is everything else.
        matches = []
        clashes = []
        for goldA, subA, (weight, clashInfo) in pairSet.pairs:
            if weight == 1.0:
                matches.append((goldA, subA))
            else:
                clashes.append((goldA, subA, (weight, clashInfo)))
        return matches, clashes, pairSet.missing, pairSet.spurious

    def compute(self, aggregator):
        return len(aggregator.match), len(aggregator.clash), len(aggregator.missing), len(aggregator.spurious)

class OSEMetric1Overlap(Metric):

    name = "Overlap mention match - unweighted"

    def __init__(self, results):
        levels = [[SectionStackLevel(), LabelStackLevel(), CorpusStackLevel()],
                  [SectionStackLevel(), SectionTypeStackLevel()]]
        Metric.__init__(self, results, levels)                        

    def importFromPairSet(self, pairSet):

        # Match is perfect, clash is everything else.
        matches = []
        clashes = []
        for goldA, subA, (weight, clashInfo) in pairSet.pairs:
            if (weight == 1.0) or (clashInfo.keys() == ["spanclash"]):
                matches.append((goldA, subA))
            else:
                clashes.append((goldA, subA, (weight, clashInfo)))
        return matches, clashes, pairSet.missing, pairSet.spurious

    def compute(self, aggregator):
        return len(aggregator.match), len(aggregator.clash), len(aggregator.missing), len(aggregator.spurious)

            
class OSEMetric1Weighted(OSEMetric1):

    name = "Exact mention match - weighted"

    def compute(self, aggregator):
        # So how is this weighted? Well, a missing annotation
        # counts as a full error. A spurious annotation is 
        # a cheap error. A clashing annotation is a half error.
        # But how do we feed PRF computation properly? Easy. 
        # The spurious is weighted directly. The clash
        # is apportioned between match and clash.
        m, c, miss, spur = OSEMetric1.compute(self, aggregator)
        spuriousWeight = .25
        clashWeight = .5
        spur = spur * spuriousWeight
        m, c = (m + c - (clashWeight * c), clashWeight * c)
        return m, c, miss, spur
            
# Adding this to check performance on discontinuous and continous.
            
class OSEMetric1WeightedContinuous(OSEMetric1Weighted):

    name = "Exact mention match, continuous - weighted"

    def importFromPairSet(self, pairSet):
        matches, clashes, missing, spurious = OSEMetric1Weighted.importFromPairSet(self, pairSet)
        # Now that we have them, get rid of every mention that
        # has multiple spans.
        return [(a, b) for (a, b) in matches if (len(a.spans) == 1) and (len(b.spans) == 1)], \
               [(a, b, details) for (a, b, details) in clashes if (len(a.spans) == 1) and (len(b.spans) == 1)], \
               [a for a in missing if len(a.spans) == 1], \
               [a for a in spurious if len(a.spans) == 1]

# Now, we need the front-office metrics. First, the MedDRA finding
# metric, which is a macro-averaged metric per section.

class FrontOfficeMedDRARetrievalBase(Metric):

    # The split here is identical to the overlap split.
    # Every mention that counts as a match is one that matches in MedDRA code.
    
    def importFromPairSet(self, pairSet):

        # Match is perfect, clash is everything else.
        matches = []
        clashes = []
        for goldA, subA, (weight, clashInfo) in pairSet.pairs:
            if (weight == 1.0) or (clashInfo.keys() == ["spanclash"]):
                matches.append((goldA, subA))
            else:
                clashes.append((goldA, subA, (weight, clashInfo)))
        return matches, clashes, pairSet.missing, pairSet.spurious

    # Next, the macro convertor. What I want is the set of MedDRA codes
    # mentioned in the gold and mentioned in the submission. There are
    # no clashes here.
    
    def macroConvert(self, match, clash, missing, spurious):
        # So how do we compute this? The matches are the gold MedDRA
        # codes in the match pairs. Everything that isn't there
        # is either missing or spurious.
        meddraMatch = set()
        for goldA, subA in match:
            meddraMatch.update([m[1] for m in goldA.meddraEntries])
        # These will be everything we find in the clash, missing, spurious.
        # We will subtract the meddraMatch set from them to get the final.        
        meddraMissing = set()
        meddraSpurious = set()
        for goldA, subA, ignore in clash:
            meddraMissing.update([m[1] for m in goldA.meddraEntries])
            meddraSpurious.add(subA.meddraEntries[0][1])
        for goldA in missing:
            meddraMissing.update([m[1] for m in goldA.meddraEntries])
        meddraSpurious.update([subA.meddraEntries[0][1] for subA in spurious])
        meddraMissing -= meddraMatch
        meddraSpurious -= meddraMatch
        return len(meddraMatch), 0, len(meddraMissing), len(meddraSpurious)

class FrontOfficeMedDRARetrieval(FrontOfficeMedDRARetrievalBase):

    name = "MedDRA retrieval - macro-averaged by section"

    def __init__(self, results):
        levels = [SectionStackLevel(macroConvertor = self.macroConvert), CorpusStackLevel()]
        FrontOfficeMedDRARetrievalBase.__init__(self, results, levels)

class FrontOfficeMedDRARetrievalLabelLevel(FrontOfficeMedDRARetrievalBase):

    name = "MedDRA retrieval - macro-averaged by label"

    def __init__(self, results):
        levels = [SectionStackLevel(), LabelStackLevel(macroConvertor = self.macroConvert), CorpusStackLevel()]
        FrontOfficeMedDRARetrievalBase.__init__(self, results, levels)

# Finally, the quality metric is something that we need. What we want
# is for each matching MedDRA code, look at all the mentions associated with it.
# First, what percentage of the submission mentions that are linked to this code
# are linked to a matching gold code; the error value is 1, and the match value
# is the percent overlap between the mentions.

# What will I be aggregating? I don't need the missing annotations.

# This is only a precision measure. How do I set things up
# so that we only report precision? It all passes through
# the aggregator, not the metric, sadly. So I'm just
# going to have to assign an aggregator class to the level explicitly.

# It's actually more complicated than I thought, because the
# macro-averaging happens internally, and then I macro-average AGAIN.

# The model for how this all fits together has kind of fallen apart
# for this metric. Perhaps the actual configuration will become clear eventually.

class FrontOfficeQualityBase(Metric):

    def importFromPairSet(self, pairSet):

        # Match is perfect, clash is everything else. If the
        # clash is only spanclash, we can pick that up later.
        matches = []
        clashes = []
        for goldA, subA, (weight, clashInfo) in pairSet.pairs:
            if weight == 1.0:
                matches.append((goldA, subA))
            else:
                clashes.append((goldA, subA, (weight, clashInfo)))
        return matches, clashes, [], pairSet.spurious

# Here's the custom aggregators.

class PrecisionOnlyMacroAggregator(MacroAggregator):

    def fromChild(self, child):
        self.precisions += child.precisions    

    # Pretty sure this is always the same for macro.
    def compute(self):
        prec = sum(self.precisions)/float(len(self.precisions))
        return prec, None, None

    def writeStdout(self, metric):
        print('--------------------------------------------------')
        print('Results: %s' % metric)
        p, r, f = self.compute()

        print('    Macro-Precision: {:.2f}'.format(p))

# There's no harm in computing the other metrics, but we do NOT want to see them.

class PrecisionOnlyConvertingMacroAggregator(ConvertingMacroAggregator):

    def __init__(self, metric):
        # I need a dummy function in there. It will count as being a convertor,
        # so the nonreporting convertors will appear below it in the level stack,
        # but it will never be called because I override finish().
        ConvertingMacroAggregator.__init__(self, metric, lambda *args: None)

    def compute(self):
        if self.precisions:
            prec = sum(self.precisions)/float(len(self.precisions))
        else:
            prec = 0
        return prec, None, None
    
    def finish(self):            
        if not self.finished:
            MacroAggregator.finish(self)
            meddraScores = self._meddraScores(self.microAggregator.match, self.microAggregator.clash,
                                              self.microAggregator.missing, self.microAggregator.spurious)
            # This is the output of the importer. So there will be
            # a macroConvertor and it must be applied.
            if meddraScores:
                self.precisions.append(sum(meddraScores)/float(len(meddraScores)))

    def summaryRow(self):
        return ([None] * 4) + list(self.compute())

    def _meddraScores(self, match, clash, missing, spurious):
        # Collect the MedDRA codes from the submission side. The spurious
        # annotations may be linked. We're only interested in the 
        # MedDRA codes which have at least one matching pair, including
        # span clashes.
        meddraMap = {}
        for goldA, subA in match:
            try:
                entry = meddraMap[subA.meddraEntries[0][1]]
            except KeyError:
                # Match, spanclash, spurious
                entry = [[], [], []]
                meddraMap[subA.meddraEntries[0][1]] = entry
            entry[0].append((goldA, subA))
            
        for goldA, subA, (weight, clashInfo) in clash:            
            if clashInfo.keys() == ["spanclash"]:
                # This is the case where there's a MedDRA match
                # but not a span match. This goes in the spanclash list.
                # But it counts as an entry.
                try:
                    entry = meddraMap[subA.meddraEntries[0][1]]
                except KeyError:
                    # Match, spanclash, spurious
                    entry = [[], [], []]
                    meddraMap[subA.meddraEntries[0][1]] = entry
                entry[1].append((goldA, subA, clashInfo["spanclash"]))

        # Now, we have all the MedDRA codes we will ever regard.
        for goldA, subA, (weight, clashInfo) in clash:
            if clashInfo.has_key("meddraclash"):
                try:
                    entry = meddraMap[subA.meddraEntries[0][1]]
                except KeyError:
                    # This isn't one of the MedDRA codes we're looking for.
                    continue
                # So what do we do with this one? It goes in
                # the spurious pot. And it doesn't matter what the
                # overlap is; it's a full error.
                entry[2].append(subA)

        for subA in spurious:
            # These are the mentions which match nothing.
            try:
                entry = meddraMap[subA.meddraEntries[0][1]]
            except KeyError:
                # This isn't one of the MedDRA codes we're looking for.
                continue
            # So what do we do with this one? It goes in
            # the spurious pot. And it doesn't matter what the
            # overlap is; it's a full error.
            entry[2].append(subA)

        # So now, we've accounted for all the submission mentions.
        allScores = []
        for [spanMatch, spanClash, meddraClash] in meddraMap.values():
            allScores.append((len(spanMatch) + sum([overlap for (goldA, subA, overlap) in spanClash])) / float(len(spanMatch) + len(spanClash) + len(meddraClash)))

        # We'll use the average of these, but 
        # If there are no samples, do I include this in the
        # macro average? No.
        return allScores


# Now that we have those aggregators, here we go:
    
class FrontOfficeQuality(FrontOfficeQualityBase):

    name = "Front office quality - section scope"

    def __init__(self, results):
        levels = [SectionStackLevel(aggregatorClass = PrecisionOnlyConvertingMacroAggregator),
                  CorpusStackLevel(aggregatorClass = PrecisionOnlyMacroAggregator)]
        FrontOfficeQualityBase.__init__(self, results, levels)

class FrontOfficeQualityLabelLevel(FrontOfficeQualityBase):

    name = "Front office quality - label scope"

    def __init__(self, results):
        levels = [SectionStackLevel(),
                  LabelStackLevel(aggregatorClass = PrecisionOnlyConvertingMacroAggregator),
                  CorpusStackLevel(aggregatorClass = PrecisionOnlyMacroAggregator)]
        FrontOfficeQualityBase.__init__(self, results, levels)


ALL_METRICS = [OSEMetric1, OSEMetric1Weighted, OSEMetric1Overlap, OSEMetric1WeightedContinuous, FrontOfficeMedDRARetrieval, FrontOfficeMedDRARetrievalLabelLevel, FrontOfficeQuality, FrontOfficeQualityLabelLevel]

# Formatters.

class ScoringCSVWriter:

    def __init__(self, significant_digits = None):
        if significant_digits is None:
            self.significant_digits = 2
        else:
            self.significant_digits = significant_digits
        self._fp = None
        self._w = None

    def open(self, out_csv):
        self._fp = open(out_csv, "wb")
        self._w = csv.writer(self._fp)
        return self

    def writeheader(self, r):
        if self._w is None:
            raise Exception
        self._w.writerow(r)

    def writerow(self, row):
        if self._w is None:
            raise Exception
        if self.significant_digits > 0:
            row = [((type(elt) is float) and (("%%.%df" % self.significant_digits) % elt)) or elt for elt in row]
        self._w.writerow(row)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

    def close(self):
        if self._fp:
            fp = self._fp
            self._w = self._fp = None
            fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            self.close()
        except:
            pass        

    def write_csv(self, out_csv, headers, rows):
        with self.open(out_csv) as w:
            w.writeheader(headers)
            w.writerows(rows)
            
class SummaryRowFormatter:

    def __init__(self, header_prefix = None, compute_confidence_data = False, confidence_samples = 1000, significant_digits = None, cache_confidence_data = False):
        self.compute_confidence_data = compute_confidence_data
        self.confidence_samples = confidence_samples
        self.cache_confidence_data = cache_confidence_data
        self.confidence_data_cache = []
        self.rows = []
        self.header_prefix = header_prefix or []
        self.csvWriter = ScoringCSVWriter(significant_digits = significant_digits)

    def getHeaders(self):
        return ["run"] + self.header_prefix + self.NORMAL_HEADERS

    # EXTENDED_HEADERS = ['run', "metric", "condition", "TP", "FP", "FN", "metric", "value", "mean", "variance", "stddev",
    #                    "95% bottom", "95% top"]
    NORMAL_HEADERS = ["metric", "match", "clash", "missing", "spurious", "precision", "recall", "f1"]

    def addRow(self, runName, rowPrefix, metricName, summaryRow):
        self.rows.append([runName] + list(rowPrefix) + [metricName] + summaryRow)

    def write_csv(self, out_csv):
        self.csvWriter.write_csv(out_csv, self.getHeaders(), self.rows)

class DetailRowFormatter():

    def __init__(self):
        self.csvWriter = ScoringCSVWriter()
        self.rows = []

    def format_results_scores(self, results):
        run = results.runName
        def gEntry(sect, a):
            spans = [(s, s + l) for (s, l) in a.spans]
            return [a.spans[0][0], a.spans[-1][0] + a.spans[-1][1], ";".join(["%d-%d" % (s, e) for (s, e) in spans]), " ".join([sect.text[s:e] for (s, e) in spans]), "|".join(sorted([m[0] for m in a.meddraEntries]))]
        for goldLabel, guessLabel, goldSection, guessSection, ps in results.pairSets:
            basename = goldLabel.fileBasename
            prefix = [run, basename, goldSection.name]            
            for goldA, subA, (weight, clashInfo) in ps.pairs:
                if weight == 1.0:
                    self.rows.append(prefix + ["match", None] + gEntry(goldSection, goldA) + gEntry(goldSection, subA))
                else:
                    clashVal = []
                    if clashInfo.has_key("meddraclash"):
                        clashVal.append("meddraclash")
                    if clashInfo.has_key("spanclash"):
                        clashVal.append("spanclash:" + str(clashInfo["spanclash"]))
                    self.rows.append(prefix + ["clash", "|".join(sorted(clashVal))] + gEntry(goldSection, goldA) + gEntry(goldSection, subA))
            self.rows += [prefix + ["missing", None] + gEntry(goldSection, goldA) + ([None] * 5) for goldA in ps.missing]
            self.rows += [prefix + ["spurious", None] + ([None] * 5) + gEntry(goldSection, subA) for subA in ps.spurious]
            self.rows += [prefix + ["ignored", None] + ([None] * 5) + gEntry(goldSection, subA) for subA in set(guessSection.getMentions()) - set(guessSection.getNonIgnoredMentions())]

    def getHeaders(self):
        return self.HEADERS

    HEADERS = ["run", "basename", "section", "match_type", "clashes", "gold_start", "gold_end", "gold_spans", "gold_text", "gold_PTs", "hyp_start", "hyp_end", "hyp_spans", "hyp_text", "hyp_PT"]

    def write_csv(self, p):
        self.csvWriter.write_csv(p, self.getHeaders(), self.rows)
    
class Results:

    def __init__(self, runName, gold_corpus, guess_corpus, metrics = None):
        if metrics is None:
            metrics = ALL_METRICS
        self.runName = runName
        self.metrics = [t(self) for t in metrics]
        self.pairSets = []
        self.guessCorpus = guess_corpus
        self.goldCorpus = gold_corpus

    def eval_section(self, goldSection, guessSection):
        ps = PairSet(goldSection, guessSection)
        for t in self.metrics:
            t.eval_section(ps)
        self.pairSets.append((goldSection.label, guessSection.label, goldSection, guessSection, ps))
        
    # Compares the two files
    # Somewhere in here we need to account for what we do with warnings and precautions
    # in non-PLR. Probably, we have a special aggregator at some point.
    def compare_files(self, gold_label, guess_label):
        sectionPairs = self.validate_pair(gold_label, guess_label)
        for goldSection, submissionSection in sectionPairs:
            self.eval_section(goldSection, submissionSection)
        
    def compare(self):
        gold_corpus = self.goldCorpus
        guess_corpus = self.guessCorpus
        for key in sorted(guess_corpus.labels.keys()):
            self.compare_files(gold_corpus.labels[key], guess_corpus.labels[key])

    # Validates that the two Labels are similar enough to merit comparing
    # performance metrics, mainly just comparing the sections/text to make sure
    # they're identical
    def validate_pair(self, l1, l2):
        assert len(l1.sections) == len(l2.sections), \
            'Different number of sections: ' + str(len(l1.sections)) + \
            ' vs. ' + str(len(l2.sections))
        goldSections = l1.sections
        sectionPairs = []
        namesFound = set()
        for sect in goldSections:
            subSection = l2.getSectionByName(sect.name)
            if not subSection:
                raise AssertionError, ("no submission section named " + sect.name)
            namesFound.add(sect.name)
            assert sect.id == subSection.id, \
                'Different section IDs: ' + sect.id + \
                ' vs. ' + subSection.id
            assert sect.text == subSection.text, 'Different section texts'
            sectionPairs.append((sect, subSection))
        namesRemaining = set([s.name for s in l2.sections]) - namesFound
        if namesRemaining:
            raise AssertionError, ("unknown submission section names: " + ", ".join(namesRemaining))
        return sectionPairs

    # Output.

    def writeStdout(self):
        print("For run ID %s:" % self.runName)
        for t in self.metrics:
            t.writeStdout()

    def writeSummaries(self, summaryHash, significant_digits = None,
                       compute_confidence_data = False):
        for t in self.metrics:
            t.writeSummaries(self.runName, summaryHash, significant_digits = significant_digits,
                             compute_confidence_data = compute_confidence_data)
        

class ResultsSet:

    def __init__(self, goldCorpus, runsAndDirs):
        self.runsAndDirs = runsAndDirs
        self.goldCorpus = goldCorpus

    def score(self, fmt, metrics = None, write_stdout = False,
              write_details = None, write_summaries = None, significant_digits = None,
              compute_confidence_data = False):
        summaryWriterHash = write_summaries
        detailWriter = write_details
        
        for [run, guess_dir] in self.runsAndDirs:
            print('Run: ' + run + ' Guess Directory: ' + guess_dir)

            results = self.compare_dirs(guess_dir, run, fmt, metrics = metrics)

            # How to save the results? For each run, write the
            # stdout results if asked. Also, aggregate the summary
            # and details if present. Well, for the summary
            # writer we need to write a summary at each level. So
            # we need a summary writer for each level, and we don't
            # know what the levels are, so we need to pass in a hash.

            if write_stdout:
                results.writeStdout()
            if summaryWriterHash is not None:
                results.writeSummaries(summaryWriterHash, significant_digits = significant_digits,
                                       compute_confidence_data = compute_confidence_data)
            if detailWriter:
                detailWriter.format_results_scores(results)
                
    # Compares the files in the two directories using compare_files.
    # SAM: changed to accept a gold standard corpus object instead of
    # the directory of files, since we don't want to keep reading the gold
    # standard for each guess directory. We also don't care about how many
    # guess files are superfluous; we only care how many of the gold files we found.

    def compare_dirs(self, guess_dir, runName, fmt, metrics = None):
        gold_corpus = self.goldCorpus
        guess_corpus = GuessCorpus(guess_dir, runName, fmt, gold_corpus)
        for key in sorted(set(gold_corpus.files) - set(guess_corpus.files)):
            print('WARNING: gold label file not found in guess directory: ' + key)
        guess_corpus.load()
        results = Results(runName, gold_corpus, guess_corpus, metrics = metrics)
        results.compare()
        return results
