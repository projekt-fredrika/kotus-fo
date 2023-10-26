#!/usr/bin/python3

# Parse and output words from wordlist of Finland Swedish dialects published by Institute for the Languages of Finland, see https://kaino.kotus.fi/fo/
# Ordbok över Finlands svenska folkmål
import xml.etree.ElementTree as ET
import pandas as pd
import os
import requests
import json
import ast 
import re
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

loadlexemesflag = True
stylefilter = "fin" # will not read grov-dialect descriptions from XML
getwikidatalexemeflag = True
loadcacheflag = True
usecacheflag = True
savetopickeflag = True
# To create cache file and pickle file for faster processing - turn above to True and place downloaded xml-files in directory fo/. 
# Download zip file from https://www.kotus.fi/aineistot/tietoa_aineistoista/sahkoiset_aineistot_kootusti)
readpickleflag = True
savetoexcelflag = False
countcharsflag = True
bulkconvertflag = True

# to run single xml files instead of all in directory, change to True 
singlexml = False
xml_file = ["Band1-01-abb.xml", "Band1-02-all.xml"]
xml_file = ["Band1-01-abb.xml"]

# import parameters from config.py
from config import PATH
xmlfilepath = PATH+"fo/"
outputpath = PATH
cachefile = PATH+"cache.json"

chars = {}
cached_lexemes = {}
catconvert = {"sub":"substantiv", "verb":"verb", "adj":"adjektiv", "adv":"adverb", "interj":"interjektion","konj":"konjunktion","prep":"preposition","pron":"pronomen","räkn":"räkneord","ortn.":"ortnamn"}
conversiontable = pd.DataFrame()
conversion_dict = {}
patterns = {}

# first function
def loadwords():
    print("Reading XML-file")
    filelist = listxmlfiles(xmlfilepath)
    df = pd.DataFrame()
    i = 0
    for file in filelist:
        i += 1
        data =  readxml_dialects(xmlfilepath,file)
        #df2 =  readxml_basics(filepath,file)
        #print(f"Read XML-file: {file}, length {df2.shape[0]}")
        df2 = pd.DataFrame(data)
        df = pd.concat([df, df2], ignore_index=True)

    if getwikidatalexemeflag == False:
        print("lexeme = False. Not fetching data from Wikidata API.\n")
    else:  
        print("Collecting lexeme stats")
        for index, row in df.iterrows():
            word = row["FO_oneword"].strip()
            category_fo = row["FO_PartOfSpeech_class_first"]
            category_fo_homonum = row["FO_hg"]
            cache_or_api_or_error,hits,lexeme_id,value,language,category,url = search_lexeme(word, category_fo, category_fo_homonum)
            df.at[index, "WD_hits"] = hits
            df.at[index, "WD_lexeme_id"] = lexeme_id
            df.at[index, "WD_value"] = value
            df.at[index, "WD_language"] = language
            df.at[index, "WD_category"] = category
            df.at[index, "WD_url"] = url
            print(f"Row {index + 1}/{len(df)}\t{cache_or_api_or_error}\t{word}\t{hits}\t{lexeme_id}\t{value}\t{language}\t{category}\t{url}")
        print("Done collecting lexeme stats")

    print(f"Total amount of rows: {len(df)}")
    return df

# gets XML files to process, called from first function
def listxmlfiles(directory_path):
    # Get a list of all files in the directory and filter to only .xml files
    file_list = os.listdir(directory_path)
    xml_files = [file for file in file_list if file.endswith(".xml")]
    if singlexml == True:
        xml_files = xml_file
    print(f"Found {len(xml_files)} XML-files")
    return sorted(xml_files)

# parse XML-files, called from first function
def readxml_dialects(xmlfilepath,file):
    tree = ET.parse(xmlfilepath+file)
    root = tree.getroot()
    data = []
    i = 0
    j = 1
    for dictionaryentry in tree.findall('DictionaryEntry'):
        id = dictionaryentry.get('id')
        homographnumber = dictionaryentry.get('homographNumber')
        homographnumber_class = ""
        abbr = {"s":"substantiv", "v":"verb", "a":"adjektiv/adverb", "i":"interjektion","k":"konjunktion","pron":"pronomen","p":"preposition","r":"räkneord",}
        if homographnumber != None:
            for key, value in abbr.items():
                if homographnumber.startswith(key):
                    homographnumber_class = value
        headword = dictionaryentry.find('./HeadwordCtn/Headword').text.strip()
        compound = False
        if headword.startswith('-') or headword.endswith('-'):
            oneword = headword
            compound = True
        elif "-" in headword:
            oneword = headword.replace("-","")
            compound = True
        elif "-" not in headword:
            oneword = headword
            compound = False
        else:
            print("error with hyphen")
            exit()
        url_kotus = "https://kaino.kotus.fi/fo/?p=article&fo_id="+id
        #searchform = dictionaryentry.find('./HeadwordCtn/SearchForm').text
        #description = ET.tostring(dictionaryentry, encoding='utf-8', method='text').decode('utf-8')
        raw_xml = ET.tostring(dictionaryentry, encoding='utf-8').decode('utf-8').replace("\n", " ")
        raw_xml_length = len(raw_xml)
        variant_tags = {}
        partofspeeches_tags = {}
        seealso_tags = []
        example_tags = []
        sensegrp_tags = []
        partofspeech_first = ""
        partofspeech_class_first = ""
        d = "not set"
        style = "not set"
        active = "not set"
        print(headword)
        for child in dictionaryentry:
            if child.tag == "Variant":
                style = child.get('style')
                if style == stylefilter: #e.g. only fin
                    active = "Variant"
                    d = child.text.strip()
                    if d not in variant_tags:
                        variant_tags[d] = {"Style": style, "Regions": []}
            if child.tag == "PartOfSpeech":
                active = "PartOfSpeech"
                if child.text:
                    d = child.text.strip()
                else:
                    d = "no PartOfSpeech text"
                partofspeech_freevalue = child.get("freeValue")
                if d not in partofspeeches_tags:
                    partofspeeches_tags[d] = {"freeValue": partofspeech_freevalue, "Regions": []}
                if partofspeech_first == "":
                    partofspeech_first = d
                if partofspeech_class_first == "":
                    partofspeech_class_first = partofspeech_freevalue.split("_")[0]
                    if partofspeech_class_first == "":
                        partofspeech_class_first = d
                    for key, value in catconvert.items():
                        if partofspeech_class_first == key:
                            partofspeech_class_first = value
            if child.tag == "SenseGrp":
                active = "SenseGrp"
                sensegrp_tags.append(ET.tostring(child, encoding='utf-8', method='text').decode('utf-8'))
            if child.tag == "Example":
                active = "Example"
                example_tags.append(ET.tostring(child, encoding='utf-8', method='text').decode('utf-8'))
            if child.tag == "SeeAlso":
                active = "SeeAlso"
                seealso_tags.append(ET.tostring(child, encoding='utf-8', method='text').decode('utf-8'))
            if child.tag == "GeographicalUsage" and active != "not set" and d != "not set":
                if child.text:
                    geousage = child.text.strip()
                else:
                    geousage = "no geousage text"
                if active == "Variant":
                    if style == stylefilter: #e.g. only fin
                        if "-" in geousage:
                            variant_tags[d]["Regions"].append(geousage.split("-")[0])
                            variant_tags[d]["Regions"].append(geousage.split("-")[1])
                        else:
                            variant_tags[d]["Regions"].append(geousage)
                if active == "PartOfSpeech":
                    if "-" in geousage:
                        partofspeeches_tags[d]["Regions"].append(geousage.split("-")[0])
                        partofspeeches_tags[d]["Regions"].append(geousage.split("-")[1])
                    else:
                        partofspeeches_tags[d]["Regions"].append(geousage)
            if child.tail and (len(child.tail)>3 or child.tail.strip().startswith(";")):
                active = "not set"
            else:
                continue
        data.append({"FO_url":url_kotus, "FO_id":id, "FO_Headword":headword, "FO_compound":compound, "FO_hg": homographnumber_class, "FO_oneword":oneword, "FO_hg":homographnumber, "FO_PartOfSpeech": partofspeeches_tags,  "FO_Variants": variant_tags, "FO_PartOfSpeech_first": partofspeech_first, "FO_PartOfSpeech_class_first": partofspeech_class_first, "SenseGrp_tags" : sensegrp_tags, "Example_tags": example_tags, "SeeAlso_tags": seealso_tags , "FO_raw_xml":raw_xml, "FO_raw_xml_length":raw_xml_length})
    #for row in data:
        #print(row['FO_Headword'], row['FO_oneword'], row['FO_PartOfSpeech_class'])
        #print(row)
    return data

# search for corresponding lexeme from Wikidata, called from first function
def search_lexeme(query, category_fo, category_fo_homonum):
    global cached_lexemes
    cache_or_api_or_error = "none"
    if usecacheflag is False or query not in cached_lexemes: 
        cache_or_api_or_error ="api"
        base_url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "sv", 
            "uselang":'sv',
            "type": "lexeme",
            "search": query
        }
        response = requests.get(base_url, params=params)
        data = response.json()
        cached_lexemes[query] = data
        with open(cachefile, 'w') as json_file:
            json.dump(cached_lexemes, json_file, indent=4)
    else: 
        cache_or_api_or_error = "cache"
        data = cached_lexemes[query]
    results = []
    try:
        lexeme_entries = data["search"]
        if len(lexeme_entries)>0:
            for entry in lexeme_entries:
                #print(entry)
                lexeme_id = entry["id"]
                value = entry["display"]["label"]["value"]
                language = entry["display"]["label"]["language"]
                category = entry["display"]["description"]["value"].split(", ")[1]
                results.append([lexeme_id,value,language,category])
                url_wd = ""
                url_wd = "https://www.wikidata.org/wiki/Lexeme:"+lexeme_id
                if category_fo == "":
                    category_fo = category_fo_homonum
                if value == query and language == "sv" and category_fo == category: 
                    return cache_or_api_or_error, len(lexeme_entries),lexeme_id,value,language,category,url_wd
        return cache_or_api_or_error, len(lexeme_entries),"","","","",""
    except KeyError:
        print("KeyError")
        cache_or_api_or_error = "error"
    return cache_or_api_or_error, None,"","","","",""

# load chache used when searching for lexeme in Wikidata, used in function search_lexeme, called from main script
def loadcache():
    global cached_lexemes
    if not os.path.exists(cachefile):
        with open(cachefile, "w") as file:
            file.write("{}")
        print(f"'{cachefile}' was created")
    with open(cachefile, 'r') as json_file:
        cached_lexemes = json.load(json_file)
        print(f"Loaded cache file: {cachefile}")

# saves dataframe to pickle, called from main script
def savetopickle(df, outputpath):
    output_pickle_file = outputpath+"dataframe.pkl"
    df.to_pickle(output_pickle_file)
    print(f"saved pickle file {output_pickle_file}")

# loads dataframe from pickle, called from main script
def readpickle(path):
    pickle_file = path+"dataframe.pkl"
    loaded_df = pd.read_pickle(pickle_file)
    print(f"\nLoaded pickle file {pickle_file} with {len(loaded_df)} rows")
    return loaded_df

# manipulates and filters dataframe, and outputs as excel file
def savetoexcel(df, outputpath):
    # Create a Pandas Excel writer object
    #output_excel_file = outputpath+"output_data.xlsx"
    #excel_writer = pd.ExcelWriter(output_excel_file, engine='xlsxwriter')

    # Write each DataFrame to a separate sheet
    print("\nAnalytics")

    print(f"All: Total rows in dataframe: {df.shape[0]}")
    #print(df)
    #filtered_df = df[['FO_id', 'FO_Headword', 'FO_compound', 'FO_hg', 'FO_oneword', 'WD_lexeme_id']]
    #filtered_df.to_excel(excel_writer, sheet_name='All', index=False)
    #df.to_excel(excel_writer, sheet_name='All', index=False)

    #filtered_df = df[df['FO_compound'] == False].copy()
    #print(f"Non-compound: Simplex words (FO_compound == False): {filtered_df.shape[0]}")
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Non-compound', index=False)

    #filtered_df = df[df['FO_Headword'].str.endswith('-')].copy()
    #print(f"Förled: Headword ends with hyphen (-), prefix in FO: {filtered_df.shape[0]}")
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Förled', index=False)

    #print("\nMatched to Wikidata lexemes")
    #filtered_df = df[df['WD_lexeme_id'].notnull() & (df['WD_lexeme_id'].astype(str).str.len() > 0)].copy()
    #print(f"Lexeme_id: Matched lexemes: {filtered_df.shape[0]}")
    #for index, row in filtered_df.iterrows():
    #    lexeme_id = filtered_df.at[index, "WD_lexeme_id"]
    #    if filtered_df.at[index, "WD_lexeme_id"] != "":
    #        filtered_df.at[index, "QS_L"] = lexeme_id
    #        filtered_df.at[index, "QS_desc_src"] = "P12032"
    #        filtered_df.at[index, "QS_id"] = '"'+filtered_df.at[index, "FO_id"].replace("FO_", "")+'"'
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Lexeme_id', index=False)

    #print("\nNew lexeme candidates")
    #filtered_df = df.copy()
    #values_to_keep = ['havs','båt','fisk','is']
    #filtered_df['First_Part'] = filtered_df['FO_Headword'].str.split('-').str[0]
    #filtered_df = filtered_df[filtered_df['First_Part'].isin(values_to_keep)]
    #count = filtered_df['First_Part'].value_counts()
    #count = filtered_df['First_Part'].value_counts().reset_index()
    #count.columns = ['First_Part', 'Count']
    #merged_df = filtered_df.merge(count, on='First_Part')
    #merged_df = merged_df.sort_values(by='Count', ascending=False)
    #merged_df = merged_df.head(1000)
    #print(f"Förled Limited: Words starting with {values_to_keep} in total: {merged_df.shape[0]}")    
    #print(merged_df)
    #merged_df.to_excel(excel_writer, sheet_name='Förled Limited', index=True)

    #filtered_df = df.sort_values(by='FO_raw_xml_length', ascending=False).copy()
    #filtered_df = filtered_df.head(500)
    #print(f"Top by explanation length: {filtered_df.shape[0]}")
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Top by explanation length', index=False) 

    #df = df.sort_values(by='FO_Headword', ascending=True)
    #filtered_df = df[(df['FO_Headword'] >= 'abbal') & (df['FO_Headword'] <= 'alg')]
    print(filtered_df)

    #excel_writer.save()
    #print(f"Saved selected dataframes to file: {output_excel_file}")

# main function for counting characters
def countchars(df):
    global chars
    for index, row in df.iterrows():
        for key, value in row['FO_Variants'].items():
            if value['Style'] == "fin":
                key = key.lower().strip()
                addchar(key, row['FO_oneword'], value['Regions'], row['FO_hg'])
                #print(key, value['Style'])
    for key in chars: 
        chars[key]["ascii"] = [ord(c) for c in key]
    print(f"Amount of chars total: {len(chars)}")

# counts characters in single word, called from countchars
def addchar(dialectword, actualword, region, homonum):
    global chars
    i = 0
    uniqueword = None
    while i < len(dialectword):
        char = dialectword[i]
        combination = None

        # Check for three-character combinations
        if i + 2 < len(dialectword) and True:
            three_char_comb = char + dialectword[i + 1] + dialectword[i + 2]
            if three_char_comb in ["ddj", "ddz", "ttj", "tts"]:
                combination = three_char_comb
                i += 2  # Skip next two characters

        # Check for two-character combinations
        if not combination and i + 1 < len(dialectword) and True:
            two_char_comb = char + dialectword[i + 1]
            if two_char_comb in ["dj", "dz", "tj", "ts"]:
                combination = two_char_comb
                i += 1  # Skip next character

        # Check for characters that are double
        if not combination and i + 1 < len(dialectword) and char == dialectword[i + 1] and True:
            combination = char * 2
            i += 1  # Skip next character

        # Check for characters followed by "̣", e.g. ḍ, ḷ, ɺ̣, ṇ, ṣ och ṭ
        elif i + 1 < len(dialectword) and dialectword[i + 1] == "̣" and True:
            combination = char + "̣"
            i += 1  # Skip next character

        # Check for characters followed by ':'
        elif i + 1 < len(dialectword) and dialectword[i + 1] == ':' and True:
            combination = char + ":"
            i += 1  # Skip next character

        # Check for characters followed by 'ː'
        elif i + 1 < len(dialectword) and dialectword[i + 1] == 'ː' and True:
            combination = char + "ː"
            i += 1  # Skip next character

        # Check for characters followed by 'ʼ', muljering
        elif i + 1 < len(dialectword) and dialectword[i + 1] == 'ʼ' and True:
            combination = char + "ʼ"
            i += 1  # Skip next character

        # Check for characters followed by 'ʽ', tonlöshet
        elif i + 1 < len(dialectword) and char == 'ʽ' and True:
            combination = "ʽ" + dialectword[i+1]
            i += 1  # Skip next character

        i += 1

        # Check for double combinations immedietly: lʼlʼ, ḷḷ, nʼnʼ, ṭṭ, ṇṇ, ḍḍ, dʼdʼ, tʼtʼ, ṣṣ
        if combination and i + 1 < len(dialectword) and combination+dialectword[i]+dialectword[i+1] in ["lʼlʼ", "ḷḷ", "nʼnʼ", "ṭṭ", "ṇṇ", "ḍḍ", "dʼdʼ", "tʼtʼ", "ṣṣ"] and True:
            combination = combination+dialectword[i]+dialectword[i+1]
            i += 2 # Skip two characters

        # Update the chars dictionary with the combination
        if combination:
            chars[combination] = chars.get(combination, {"count":0})
            chars[combination]["count"] = chars[combination]["count"] + 1
            chars[combination].setdefault("ord_exempel", actualword)
            chars[combination].setdefault("ord_hg", homonum)
            chars[combination].setdefault("fin_uttal", dialectword)
            chars[combination].setdefault("fin_uttal_region", region)
        # If there's no combination, treat as individual char
        else:
            chars[char] = chars.get(char, {"count":0})
            chars[char]["count"] = chars[char]["count"] + 1
            chars[char].setdefault("ord_exempel", actualword)
            chars[char].setdefault("ord_hg", homonum)
            chars[char].setdefault("fin_uttal", dialectword)
            chars[char].setdefault("fin_uttal_region", region)


def loadconversiontable():
    global conversiontable
    conversiontable = pd.read_csv('fin2ipa.tsv', delimiter='\t')
    conversiontable = conversiontable[conversiontable['fin'].notna()]
    conversiontable = conversiontable.fillna("")
    conversiontable = conversiontable.sort_values(by='fin', key=lambda x: x.str.len(), ascending=False)
    global conversion_dict
    conversion_dict = conversiontable.set_index('fin')['IPA'].to_dict()
    global patterns 
    patterns = {fin: re.compile("^" + re.escape(fin)) for fin in conversion_dict.keys()}

# saves character count to excel file
def savechars(outputpath):
    df_counted = pd.DataFrame(chars).T
    df_counted = df_counted.sort_values(by='count', ascending=False)
    df_fin2ipa = pd.read_csv('fin2ipa.tsv', delimiter='\t')
    df = df_counted.merge(df_fin2ipa, left_index=True, right_on='fin', how='left')
    df['IPA_uttal_konverterad'] = df['fin_uttal'].apply(fin2ipa)
    desired_order = ['fin', 'IPA', 'status', 'count', 'ord_exempel', 'ord_hg', 'fin_uttal', 'IPA_uttal_konverterad', 'fin_uttal_region']
    df = df.reindex(columns=desired_order)
    print(df)
    output_excel_file = outputpath+"output_chars.xlsx"
    df.to_excel(output_excel_file)
    print(f"Saved chars to file: {output_excel_file}")

#convert fin to IPA
def fin2ipa(word):
    #global conversiontable
    global conversion_dict
    global patterns
    #print(word)
    
    #ipa_converted = ""
    # Continuously check the start of the word for any matches
    #while word:
    #    match_found = False
    #    for _, entry in conversiontable.iterrows():
    #        pattern = "^" + re.escape(entry['fin'])
    #        match = re.match(pattern, word)
    #        if match:
    #            ipa_converted += entry['IPA']
    #            word = word[len(entry['fin']):]
    #            match_found = True
    #            break
    #    # If no match is found, we append the first character of the word
    #    # to the result and remove it from the word
    #    if not match_found:
    #        ipa_converted += word[0]
    #        word = word[1:]
    #return ipa_converted

    ipa_converted = ""
    while word:
        match_found = False
        for fin, pattern in patterns.items():
            match = pattern.match(word)
            if match:
                ipa_converted += conversion_dict[fin]
                word = word[len(fin):]
                match_found = True
                break
        if not match_found:
            ipa_converted += word[0]
            word = word[1:]
    return ipa_converted

def populate_atgard(row):
    if pd.isna(row['Region_förkortning']):
        return 'Nej, ingen region'
    elif row['FO_uttal_fin'].startswith('‑'):
        return 'Nej, börjar med bindesstreck'
    elif row['FO_uttal_fin'].endswith('‑'):
        return 'Nej, slutar med bindesstreck'
    elif row['WD_lexeme_id'].strip():
        return 'Ja, uppdatera existerande lexem'
    else:
        return 'Ja, skapa lexem'

def convertbulk(df):
    print("starting convertbulk")
    df = df[:100000].copy()
    uttalrader = []
    for index, row in df.iterrows():
        for key, value in row['FO_Variants'].items():
            if value.get('Style',"") == "fin":
                #uttalrader.append([row['FO_Headword'],row['FO_hg'],row['FO_PartOfSpeech_class'], key, value.get('Regions',""), fin2ipa(key)])
                uttalrader.append({'FO_id':row['FO_id'],'FO_headword':row['FO_Headword'], 'FO_hg':row['FO_hg'], 'FO_PartOfSpeech_class_first':row['FO_PartOfSpeech_class_first'], 'FO_uttal_fin': key, 'region': value.get('Regions',""), 'WD_lexeme_id':row['WD_lexeme_id']})
    uttal_df = pd.DataFrame(uttalrader)
    print("next apply fin2ipa")
    uttal_df['WD_uttal_IPA'] = uttal_df['FO_uttal_fin'].apply(fin2ipa)
    uttal_df['FO_hg'] = uttal_df['FO_hg'].fillna('')
    print("next save uttal to output_uttal.xlsx")
    uttal_df.to_excel(outputpath+"output_uttal.xlsx", index=False, engine='openpyxl')
    #uttal_df.to_csv(outputpath+"output_uttal.csv", index=False)

    print("next explode regions")
    exploded_df = uttal_df.explode('region')
    print(exploded_df)
    df_regioner = pd.read_csv('regioner.tsv', sep='\t')
    merged_df = exploded_df.merge(df_regioner, left_on='region', right_on='Region_förkortning', how='left')
    merged_df['WD_åtgärd'] = merged_df.apply(populate_atgard, axis=1)
    desired_order = ['FO_id', 'FO_headword', 'FO_hg', 'FO_PartOfSpeech_class_first', 'FO_uttal_fin', 'Region_förkortning', 'Region_omrade', 'WD_åtgärd', 'WD_lexeme_id', 'WD_uttal_IPA', 'WD_region']
    merged_df = merged_df.reindex(columns=desired_order)

    print(merged_df)
    print("saving without formatting xlsx")
    merged_df.to_excel(outputpath+"output_uttal_regioner_no_formatting.xlsx", index=False, engine='openpyxl')

    # Create a new Excel workbook
    workbook = Workbook()
    worksheet = workbook.active

    print("formatting worksheets")
    # Write the DataFrame to the worksheet
    for row in dataframe_to_rows(merged_df, index=False, header=True):
        worksheet.append(row)
    # Add hyperlinks to the "URL" column
    for cell in worksheet['A'][1:]:
        cell.hyperlink = "https://kaino.kotus.fi/fo/?p=article&fo_id="+str(cell.value)
    for cell in worksheet['I'][1:]:        
        cell.hyperlink = "https://www.wikidata.org/wiki/Lexeme:"+str(cell.value)
    for cell in worksheet['K'][1:]:        
        cell.hyperlink = "https://www.wikidata.org/wiki/"+str(cell.value)

    # Save the workbook to an XLSX file
    print("saving formated worksheet")
    workbook.save(outputpath+"output_uttal_regioner_with_formatting.xlsx")
    print("done")


# actual running of script is here
if loadcacheflag == True:
    loadcache()
if loadlexemesflag == True: 
    df = loadwords()
if savetopickeflag == True: 
    savetopickle(df, outputpath)
if readpickleflag == True: 
    df = readpickle(outputpath)
if savetoexcelflag == True: 
    savetoexcel(df, outputpath)
if countcharsflag == True:
    countchars(df)
    loadconversiontable()
    savechars(outputpath)
if bulkconvertflag == True: 
    loadconversiontable()
    convertbulk(df)