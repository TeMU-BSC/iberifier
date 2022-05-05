import logging
import os
import pathlib

from collections import defaultdict

# Language detection tools
import fasttext
import wget
from langdetect import detect_langs
#from polyglot.detect import Detector
from langid.langid import LanguageIdentifier, model

# Load module for fasttext
fasttext_lib_url='https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin'
lib_dir = str(pathlib.Path(__file__).parents[1].joinpath('lib'))
lib_path = str(pathlib.Path(__file__).parents[1].joinpath('lib','lid.176.bin'))
if not os.path.exists(lib_dir):
    os.mkdir(lib_dir)
    wget.download(fasttext_lib_url, lib_dir)
else:
    if not os.path.exists(lib_path):
        wget.download(fasttext_lib_url, lib_dir)
ft_model = fasttext.load_model(lib_path)

# Instiantiate a langid language identifier object
langid_identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)


logging.basicConfig(filename=str(pathlib.Path(__file__).parents[1].joinpath('tw_coronavirus.log')),
                    level=logging.DEBUG)


def do_detect_language(text, detector):
    threshold_confidence = 0.75

    if not text:
        logging.error('Error!, text is empty.')
        return None

    if detector == 'fasttext':
        try:
            pred_fasttext = ft_model.predict(text, k=1)
            if pred_fasttext[1][0] >= threshold_confidence:
                lang_fasttext = pred_fasttext[0][0].replace('__label__','')                    
            else:
                lang_fasttext = 'undefined'
        except:
            lang_fasttext = 'undefined'
        return lang_fasttext
    elif detector == 'langid':
        try:
            pred_langid = langid_identifier.classify(text)
            if pred_langid[1] >= threshold_confidence:
                lang_langid = pred_langid[0]
            else:
                lang_langid = 'undefined' 
        except:
            lang_langid = 'undefined'
        return lang_langid
    elif detector == 'langdetect':
        try:
            pred_langdetect = detect_langs(text)[0]
            lang_langdetect, conf_langdetect = str(pred_langdetect).split(':')
            conf_langdetect = float(conf_langdetect)
            if conf_langdetect < threshold_confidence:
                lang_langdetect = 'undefined'
        except:
            lang_langdetect = 'undefined'
        return lang_langdetect
    elif detector == 'polyglot':
        try:
            poly_detector = Detector(text, quiet=True)
            lang_polyglot = poly_detector.language.code
            conf_polyglot = poly_detector.language.confidence/100
            if conf_polyglot >= threshold_confidence:
                # sometimes polyglot  returns the language 
                # code with an underscore, e.g., zh_Hant.
                # next, the underscore is removed
                idx_underscore = lang_polyglot.find('_')
                if idx_underscore != -1:
                    lang_polyglot = lang_polyglot[:idx_underscore]
            else:
                lang_polyglot = 'undefined'            
        except:
            lang_polyglot = 'undefined'
        return lang_polyglot


def detect_language(text):
    lang_detected = defaultdict(int)

    if not text:
        logging.error('Error!, text is empty.')
        return None

    lang_dict = {}

    # infer language using fasttext    
    lang_fasttext = do_detect_language(text, 'fasttext')
    lang_dict['fasttext'] = lang_fasttext
    lang_detected[lang_fasttext] += 1
    
    # infer language using langid
    lang_langid = do_detect_language(text, 'langid')
    lang_dict['langid'] = lang_langid
    lang_detected[lang_langid] += 1

    # infer language using langdetect
    lang_langdetect = do_detect_language(text, 'langdetect')
    lang_dict['langdetect'] = lang_langdetect
    lang_detected[lang_langdetect] += 1

    # infer language using polyglot
    # lang_polyglot = do_detect_language(text, 'polyglot')
    # lang_dict['polyglot'] = lang_polyglot
    # lang_detected[lang_polyglot] += 1    

    # choose language with the highest counter
    max_counter, pref_lang = -1, ''
    for lang, counter in lang_detected.items():
        if lang == 'undefined':
            continue
        if counter > max_counter:
            pref_lang = lang
            max_counter = counter
        elif counter == max_counter:
            pref_lang += '_' + lang
    
    lang_dict['pref_lang'] = pref_lang if pref_lang != '' else 'undefined'
    
    return lang_dict
