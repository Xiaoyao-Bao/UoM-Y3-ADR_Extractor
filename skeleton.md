First version of my project
-------------------------------------------------------
### Pre-processing
**1. What is my gold standard format?**

    <?xml version="1.0" encoding="UTF-8"?> <GoldLabel drug="ANORO">
    <Text>
    <Section id="S1" name="adverse reactions">...</Section> ...
      </Text>
      <IgnoredRegions>
    <IgnoredRegion len="19" name="heading" section="S1" start="4" />
        ...
      </IgnoredRegions>
      <Mentions>
    <Mention id="M49" len="6" reason="class_effect" section="S1" start="122" type="OSE_Labeled_AE">
    <Normalization meddra_llt="Asthma aggravated" meddra_llt_id="10003554" meddra_pt="Asthma" meddra_pt_id="10003553" />
    </Mention>
    ...
    <Mention id="M5" len="15,8" reason="general_term" section="S1"
    start="4798,4836" type="NonOSE_AE">
          <Normalization
    </Mention>
        ...
      </Mentions>
    </GoldLabel>
   
**2. How many steps are there for pre-processing?**

   Separate text into different sections,    
   Sentence segmentation, word tokenisation.
   
**3. what tools are you going to use?**

   NLTK tokenizer, Element tree.
   
**4. What are the difficulties you have met?**

   1. Dealing with nested entities  
      • repetitive labelling in single_existence mentions  
      • repetitive labelling in multi_existence mentions  
      • nested entities with overlapped part (i.e. completion of the first line of labelling is behind the start of later one)  
   Solution: I **deleted all** embedded entities occurred later.
   2. Dealing with ignored regions while writing back to exact position is desired

**5. What are the things to attend?**
   1. When tokenizing, words are hard to be fully separated from non-alphanumerical characters. This is important because word vectors consider only words, it may cause inaccuracy when words are mixed with other characters.


**5. What would the data be like after pre-processing?**
    
   Pretty much like CoNLL 2003 data format, where each word is followed by its label in BIO labelling scheme, and each line is separated with a new line.
### Model selection
**1. What model am I using?**

   • CNN + BiLSTM + CRF  
   • BERT
   
**2. Why choosing this model?**

**3. What are the resources to build this model?**
### Model implementation
**1. What are the parameters there to set?**

**2. What techniques to train the model?**

**3.**

**4. What will the output be like?**
### Evaluation
**1. How are you going to evaluate the result?**