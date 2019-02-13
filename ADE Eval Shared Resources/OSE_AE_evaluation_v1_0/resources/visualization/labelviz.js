// Copyright (C) 2018 The MITRE Corporation. See the toplevel
// file LICENSE.txt for license terms.

// The brat stuff has all been imported. The variable docData
// contains the document material in Brat format.

var bratLocation = "brat_13";
head.js(
    // External libraries
    bratLocation + '/client/lib/jquery.min.js',
    bratLocation + '/client/lib/jquery.svg.min.js',
    bratLocation + '/client/lib/jquery.svgdom.min.js',

    // brat helper modules
    bratLocation + '/client/src/configuration.js',
    bratLocation + '/client/src/util.js',
    bratLocation + '/client/src/annotation_log.js',
    bratLocation + '/client/lib/webfont.js',

    // brat modules
    bratLocation + '/client/src/dispatcher.js',
    bratLocation + '/client/src/url_monitor.js',
    bratLocation + '/client/src/visualizer.js'
);

var webFontURLs = [
    bratLocation + '/static/fonts/Astloch-Bold.ttf',
    bratLocation + '/static/fonts/PT_Sans-Caption-Web-Regular.ttf',
    bratLocation + '/static/fonts/Liberation_Sans-Regular.ttf'
];


// I have to define the attribute types. For reasons I don't understand,
// the only way to have a non"warning" attribute value is to declare
// the value, and have its value be a non-empty Javascript object.
// AND it has to have the name attribute.

var collData = {
    entity_types: [ {
      type   : 'OSE_Labeled_AE',
      /* The labels are used when displaying the annotion, in this case
                we also provide a short-hand "Per" for cases where
                abbreviations are preferable */
      labels : ['OSE_Labeled_AE'],
      // Blue is a nice colour for a person?
      bgColor: 'limegreen',
      // Use a slightly darker version of the bgColor for the border
      borderColor: 'darken'
    }, {
      type   : 'NonOSE_AE',
      /* The labels are used when displaying the annotion, in this case
                we also provide a short-hand "Per" for cases where
                abbreviations are preferable */
      labels : ['NonOSE_AE'],
      // Blue is a nice colour for a person?
      bgColor: 'yellow',
      // Use a slightly darker version of the bgColor for the border
      borderColor: 'darken'
    }, {
      type   : 'Not_AE_Candidate',
      /* The labels are used when displaying the annotion, in this case
                we also provide a short-hand "Per" for cases where
                abbreviations are preferable */
      labels : ['Not_AE_Candidate'],
      // Blue is a nice colour for a person?
      bgColor: 'red',
      fgColor: "white",
      // Use a slightly darker version of the bgColor for the border
      borderColor: 'darken'
    }],
  entity_attribute_types: [ {
    type: "Reason",
    name: "Reason", // Bug which requires both of these.
    values: {
      indication: {name: "indication"},
      contraindication: {name: "contraindication"},
      preexisting_condition_or_risk_factor: {name: "preexisting_condition_or_risk_factor"},
      manifestation_or_complication: {name: "manifestation_or_complication"},
      AE_rate_lteq_placebo: {name: "AE_rate_lteq_placebo"},
      AE_animal: {name: "AE_animal"},
      AE_from_drug_interaction: {name: "AE_from_drug_interaction"},
      general_term: {name: "general_term"},
      AE_from_off_label: {name: "AE_from_off_label"},
      AE_only_as_instruction: {name: "AE_only_as_instruction"},
      hypothetical_AE: {name: "hypothetical_AE"},
      AE_for_another_drug_in_class: {name: "AE_for_another_drug_in_class"},
      OD_or_withdrawal: {name: "OD_or_withdrawal"},
      from_drug_use: {name: "from_drug_use"},
      from_drug_component: {name: "from_drug_component"},
      class_effect: {name: "class_effect"},
      positive_dechallenge: {name: "positive_dechallenge"},
      other: {name: "other"}
    }
  } ]
};

head.ready(function() {
    // There's a timeout related to the Web font loading. 
    // The only way to disable it, because it's a private variable, is to
    // tell the visualizer that the fonts are already loaded. If your browser
    // respects @font-face in the CSS, then this is irrelevant.
    // one of the fonts that's used doesn't seem to load, but
    // which one it is seems to differ across browsers.
    Visualizer.areFontsLoaded = true;
    var dispatcher = Util.embed(
        // id of the div element where brat should embed the visualisations
        'vizdiv',
        // object containing collection data
        collData,
        // object containing document data
        docData,
        // Array containing locations of the visualisation fonts
        webFontURLs
    );
  // If I want to display a normalization, which I do, I have to
  // do with with hovers here. Someday.
  dispatcher.on('displaySpanComment',
                function(event, target, id, spanType, spanAttributeText, spanText, spanComment, spanCommentType, spanNormalizations) {
                  // Normalizations are [db, id, text]
                  // spanAttributeText is a list of text strings.
                  var t = [spanText + ":"];
                  for (var i = 0; i < spanAttributeText.length; i++) {
                    t.push(spanAttributeText[i] + ",");
                  }
                  if (spanNormalizations.length > 0) {
                    t.push("MeddDRA info:");
                    for (var i = 0; i < spanNormalizations.length; i++) {
                      if (i > 0) {
                        t.push("or");
                      }
                      t.push(spanNormalizations[i][2] + " (" + spanNormalizations[i][1] + ")");
                    }
                  }
                  $("#meddraCode").empty().show().text(t.join(" "));
                });
  dispatcher.on('hideComment', 
                function() {
                  $("#meddraCode").hide();
                });
});