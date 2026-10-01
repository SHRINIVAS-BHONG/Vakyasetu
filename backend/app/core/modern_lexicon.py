"""
Central Sanskrit University (Rashtriya Sanskrit Sansthan) Curated Modern Sanskrit Lexicon.
Provides standard contemporary Sanskrit terms and transliterated loanwords across:
1. Technology & Computing (तन्त्रज्ञानम् / सङ्गणकम्)
2. Daily Life & Household (दैनिक-व्यवहारः / गृहम्)
3. Transportation (यातायातम् / वाहनानि)
4. Office & Education (कार्यालयः / शिक्षा)
5. Media & Communication (सञ्चार-माध्यमम्)
"""

from typing import Dict, Tuple

# Mapping: Token / Stem -> (Canonical Lemma, Meaning in English, Sanskrit Category, Default Gender)
MODERN_SANSKRIT_TERMS: Dict[str, Tuple[str, str, str, str]] = {
    # -------------------------------------------------------------------------
    # 1. Technology, Computing & Internet (तन्त्रज्ञानम्)
    # -------------------------------------------------------------------------
    "सङ्गणकम्": ("सङ्गणकम्", "computer", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "सङ्गणक": ("सङ्गणकम्", "computer", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "कम्प्यूटरम्": ("कम्प्यूटरम्", "computer (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "कम्प्यूटर": ("कम्प्यूटरम्", "computer (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "चलदूरभाषः": ("चलदूरभाषः", "mobile phone", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),
    "चलदूरभाष": ("चलदूरभाषः", "mobile phone", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),
    "मोबाइल्": ("मोबाइल्", "mobile phone (loanword)", "Modern Loanword (ऋणपदम्)", "Masculine / पुंल्लिङ्गम्"),
    "मोबाइल": ("मोबाइल्", "mobile phone (loanword)", "Modern Loanword (ऋणपदम्)", "Masculine / पुंल्लिङ्गम्"),
    "अन्तर्जालम्": ("अन्तर्जालम्", "internet", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "अन्तर्जाल": ("अन्तर्जालम्", "internet", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "इण्टरनेटम्": ("इण्टरनेटम्", "internet (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "इण्टरनेट": ("इण्टरनेटम्", "internet (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "विद्युत्-पत्रम्": ("विद्युत्-पत्रम्", "email (electronic mail)", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "विद्युत्पत्रम्": ("विद्युत्-पत्रम्", "email (electronic mail)", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "ईमेल्": ("ईमेल्", "email (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "ईमेल": ("ईमेल्", "email (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "जालपुटम्": ("जालपुटम्", "web page / website", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "जालपुट": ("जालपुटम्", "web page / website", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "वेबसाइट्": ("वेबसाइट्", "website (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "तन्त्रांशः": ("तन्त्रांशः", "software", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),
    "तन्त्रांश": ("तन्त्रांशः", "software", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),
    "सॉफ्टवेयर्": ("सॉफ्टवेयर्", "software (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "यन्त्रांशः": ("यन्त्रांशः", "hardware", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),
    "यन्त्रांश": ("यन्त्रांशः", "hardware", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),
    "हार्डवेयर्": ("हार्डवेयर्", "hardware (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "मुद्रकम्": ("मुद्रकम्", "printer", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "मुद्रक": ("मुद्रकम्", "printer", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "प्रिण्टर्": ("प्रिण्टर्", "printer (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "दृश्यपटलम्": ("दृश्यपटलम्", "monitor / display screen", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "कीलफलकम्": ("कीलफलकम्", "keyboard", "Technology (तन्त्रज्ञानम्)", "Neuter / नपुंसकलिङ्गम्"),
    "मूषकः": ("मूषकः", "computer mouse / mouse", "Technology (तन्त्रज्ञानम्)", "Masculine / पुंल्लिङ्गम्"),

    # -------------------------------------------------------------------------
    # 2. Transportation & Vehicles (यातायातम् / वाहनानि)
    # -------------------------------------------------------------------------
    "धूमशकटम्": ("धूमशकटम्", "train / railway train", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "धूमशकट": ("धूमशकटम्", "train / railway train", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "रेलयानम्": ("रेलयानम्", "train / rail vehicle", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "रेलयान": ("रेलयानम्", "train / rail vehicle", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "ट्रेन": ("रेलयानम्", "train (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "लोहपथगामिनी": ("लोहपथगामिनी", "train / railway", "Transportation (वाहनानि)", "Feminine / स्त्रीलिङ्गम्"),
    "विमानम्": ("विमानम्", "aeroplane / aircraft", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "विमान": ("विमानम्", "aeroplane / aircraft", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "एयरोप्लेन्": ("विमानम्", "aeroplane (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "द्विचक्रिका": ("द्विचक्रिका", "bicycle", "Transportation (वाहनानि)", "Feminine / स्त्रीलिङ्गम्"),
    "साइकल्": ("द्विचक्रिका", "bicycle (loanword)", "Modern Loanword (ऋणपदम्)", "Feminine / स्त्रीलिङ्गम्"),
    "बसयानम्": ("बसयानम्", "bus / omnibus", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "बसयान": ("बसयानम्", "bus / omnibus", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "बस्": ("बसयानम्", "bus (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "कारयानम्": ("कारयानम्", "motorcar / automobile", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "कारयान": ("कारयानम्", "motorcar / automobile", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "कार्": ("कारयानम्", "car (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "कार": ("कारयानम्", "car (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "नौका": ("नौका", "boat / ship", "Transportation (वाहनानि)", "Feminine / स्त्रीलिङ्गम्"),
    "जलयानम्": ("जलयानम्", "ship / vessel", "Transportation (वाहनानि)", "Neuter / नपुंसकलिङ्गम्"),
    "हेलिकॉप्टर्": ("उड्डयनयन्त्रम्", "helicopter (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),

    # -------------------------------------------------------------------------
    # 3. Media, Communication & Entertainment (सञ्चार-माध्यमम्)
    # -------------------------------------------------------------------------
    "दूरदर्शनम्": ("दूरदर्शनम्", "television", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "दूरदर्शन": ("दूरदर्शनम्", "television", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "टेलीविजन्": ("दूरदर्शनम्", "television (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "टी-वी": ("दूरदर्शनम्", "TV (abbreviation)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "आकाशवाणी": ("आकाशवाणी", "radio / radio broadcast", "Media (सञ्चार-माध्यमम्)", "Feminine / स्त्रीलिङ्गम्"),
    "रेडियो": ("आकाशवाणी", "radio (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "चलचित्रम्": ("चलचित्रम्", "cinema / movie / film", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "चलचित्र": ("चलचित्रम्", "cinema / movie / film", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "सिनेमा": ("चलचित्रम्", "cinema (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "फिल्म": ("चलचित्रम्", "film / movie (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "वार्तापत्रम्": ("वार्तापत्रम्", "newspaper", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "समाचारपत्रम्": ("समाचारपत्रम्", "newspaper", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "पत्रिका": ("पत्रिका", "magazine / journal", "Media (सञ्चार-माध्यमम्)", "Feminine / स्त्रीलिङ्गम्"),
    "ध्वनिवर्धकम्": ("ध्वनिवर्धकम्", "loudspeaker / amplifier", "Media (सञ्चार-माध्यमम्)", "Neuter / नपुंसकलिङ्गम्"),
    "स्पीकर्": ("ध्वनिवर्धकम्", "speaker (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),

    # -------------------------------------------------------------------------
    # 4. Office, Education & Institutions (कार्यालयः / शिक्षा)
    # -------------------------------------------------------------------------
    "कार्यालयः": ("कार्यालयः", "office", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "कार्यालय": ("कार्यालयः", "office", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "ऑफिस": ("कार्यालयः", "office (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "विश्वविद्यालयः": ("विश्वविद्यालयः", "university", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "विश्वविद्यालय": ("विश्वविद्यालयः", "university", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "महाविद्यालयः": ("महाविद्यालयः", "college", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "महाविद्यालय": ("महाविद्यालयः", "college", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "कॉलेज्": ("महाविद्यालयः", "college (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "पुस्तकालयः": ("पुस्तकालयः", "library", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "पुस्तकालय": ("पुस्तकालयः", "library", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "प्रयोगशाला": ("प्रयोगशाला", "laboratory", "Institution (संस्था)", "Feminine / स्त्रीलिङ्गम्"),
    "चिकित्सालयः": ("चिकित्सालयः", "hospital", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "हॉस्पिटल्": ("चिकित्सालयः", "hospital (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "न्यायालयः": ("न्यायालयः", "court of law", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "वित्तकोषः": ("वित्तकोषः", "bank", "Institution (संस्था)", "Masculine / पुंल्लिङ्गम्"),
    "बैङ्क्": ("वित्तकोषः", "bank (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "बैंक": ("वित्तकोषः", "bank (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),

    # -------------------------------------------------------------------------
    # 5. Daily Life & Modern Objects (दैनिक-व्यवहारः)
    # -------------------------------------------------------------------------
    "शीतकम्": ("शीतकम्", "refrigerator / fridge", "Household (दैनिक-वस्तूनि)", "Neuter / नपुंसकलिङ्गम्"),
    "शीतक": ("शीतकम्", "refrigerator / fridge", "Household (दैनिक-वस्तूनि)", "Neuter / नपुंसकलिङ्गम्"),
    "फ्रिज्": ("शीतकम्", "fridge (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "वातानुकूलकम्": ("वातानुकूलकम्", "air conditioner (AC)", "Household (दैनिक-वस्तूनि)", "Neuter / नपुंसकलिङ्गम्"),
    "एसी": ("वातानुकूलकम्", "AC (abbreviation)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "विद्युत्-दीपः": ("विद्युत्-दीपः", "electric bulb / lamp", "Household (दैनिक-वस्तूनि)", "Masculine / पुंल्लिङ्गम्"),
    "बल्ब्": ("विद्युत्-दीपः", "electric bulb (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "व्यजनम्": ("व्यजनम्", "fan / electric fan", "Household (दैनिक-वस्तूनि)", "Neuter / नपुंसकलिङ्गम्"),
    "घटी": ("घटी", "clock / wristwatch", "Household (दैनिक-वस्तूनि)", "Feminine / स्त्रीलिङ्गम्"),
    "अङ्कनी": ("अङ्कनी", "pencil", "Stationery (लेखन-सामग्री)", "Feminine / स्त्रीलिङ्गम्"),
    "लेखनी": ("लेखनी", "pen", "Stationery (लेखन-सामग्री)", "Feminine / स्त्रीलिङ्गम्"),
    "पेन्": ("लेखनी", "pen (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "सञ्चिका": ("सञ्चिका", "file / folder", "Stationery (लेखन-सामग्री)", "Feminine / स्त्रीलिङ्गम्"),
    "मार्जनम्": ("मार्जनम्", "eraser / duster", "Stationery (लेखन-सामग्री)", "Neuter / नपुंसकलिङ्गम्"),
    "मापिका": ("मापिका", "ruler / scale", "Stationery (लेखन-सामग्री)", "Feminine / स्त्रीलिङ्गम्"),
    "कन्दुकम्": ("कन्दुकम्", "ball (sports)", "Sports (क्रीडा)", "Neuter / नपुंसकलिङ्गम्"),
    "पादकन्दुकम्": ("पादकन्दुकम्", "football / soccer", "Sports (क्रीडा)", "Neuter / नपुंसकलिङ्गम्"),
    "हस्तकन्दुकम्": ("हस्तकन्दुकम्", "volleyball / handball", "Sports (क्रीडा)", "Neuter / नपुंसकलिङ्गम्"),
    "क्रिकेट्": ("क्रिकेट्", "cricket (loanword)", "Modern Loanword (ऋणपदम्)", "Neuter / नपुंसकलिङ्गम्"),
    "क्रीडाक्षेत्रम्": ("क्रीडाक्षेत्रम्", "playground / sports field", "Sports (क्रीडा)", "Neuter / नपुंसकलिङ्गम्"),
}
