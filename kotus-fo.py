#!/usr/bin/python3

# Parse and output words from wordlist of Finland Swedish dialects published by Institute for the Languages of Finland, see https://kaino.kotus.fi/fo/
# Ordbok över Finlands svenska folkmål
import xml.etree.ElementTree as ET
import pandas as pd
import os
import requests
import json
import ast 

loadcacheflag = False
loadlexemesflag = False
getwikidatalexemeflag = False
usecacheflag = False
savetopickeflag = False
# To create cache file and pickle file for faster processing - turn above to True and place downloaded xml-files in directory fo/. 
# Download zip file from https://www.kotus.fi/aineistot/tietoa_aineistoista/sahkoiset_aineistot_kootusti)
readpickleflag = True
savetoexcelflag = True
countcharsflag = False

# to run single xml files instead of all in directory, change to True 
singlexml = False
xml_file = ["Band1-01-abb.xml", "Band1-02-all.xml"]

# import parameters from config.py
from config import PATH
xmlfilepath = PATH+"fo/"
outputpath = PATH
cachefile = PATH+"cache.json"

chars = {}
cached_lexemes = {}
catconvert = {"sub":"substantiv", "verb":"verb", "adj":"adjektiv", "adv":"adverb", "interj":"interjektion","konj":"konjunktion","prep":"preposition","pron":"pronomen","räkn":"räkneord"}


def loadcache():
    global cached_lexemes
    if not os.path.exists(cachefile):
        with open(cachefile, "w") as file:
            file.write("{}")
        print(f"'{cachefile}' was created")
    with open(cachefile, 'r') as json_file:
        cached_lexemes = json.load(json_file)
        print(f"Loaded cache file: {cachefile}")

def listxmlfiles(directory_path):
    # Get a list of all files in the directory and filter to only .xml files
    file_list = os.listdir(directory_path)
    xml_files = [file for file in file_list if file.endswith(".xml")]
    if singlexml == True:
        xml_files = xml_file
    print(f"Found {len(xml_files)} XML-files")
    return sorted(xml_files)

def iterchild(element, i):
    i = i+1
    text =  "".join(element.itertext()).replace('\n', '').replace('\r', '')
    if "adjektiv" in text:
        print(i, element.tag, element.attrib, text)
    for child in element:
        iterchild(child, i)

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
        headword = dictionaryentry.find('./HeadwordCtn/Headword').text
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
        raw_xml = ET.tostring(dictionaryentry, encoding='utf-8').decode('utf-8')
        raw_xml_length = len(raw_xml)
        variant_tags = {}
        partofspeeches_tags = []
        partofspeech_first = ""
        partofspeech_class = ""
        d = "not set"
        active = "not set"
        print(headword)
        for child in dictionaryentry:
            if child.tag == "PartOfSpeech":
                partofspeech_freevalue = child.get("freeValue")
                partofspeech_text = (child.text)
                partofspeeches_tags.append([partofspeech_freevalue, partofspeech_text])
                if partofspeech_first == "":
                    partofspeech_first = partofspeech_text
                if partofspeech_class == "":
                    partofspeech_class = partofspeech_freevalue.split("_")[0]
                    for key, value in catconvert.items():
                        if partofspeech_class == key:
                            partofspeech_class = value
            if child.tag == "Variant":
                active = "Variant"
                d = child.text
                style = child.get('style')
                variant_tags[d] = {"Style": style, "Regions": []}
            elif child.tag == "GeographicalUsage" and active != "not set" and d != "not set":
                geousage = child.text
                variant_tags[d]["Regions"].append(geousage)
            else:
                continue
        data.append({"FO_url":url_kotus, "FO_id":id, "FO_Headword":headword, "FO_compound":compound, "FO_hg": homographnumber_class, "FO_oneword":oneword, "FO_hg":homographnumber, "FOPartOfSpeech": partofspeeches_tags,  "FO_Variants": variant_tags, "FO_PartOfSpeech_first": partofspeech_first, "FO_PartOfSpeech_class": partofspeech_class, "FO_raw_xml":raw_xml, "FO_raw_xml_length":raw_xml_length})
    for row in data:
        print(row['FO_Headword'], row['FO_oneword'], row['FO_PartOfSpeech_class'])
    return data

def countchars(df):
    for index, row in df.iterrows():
        for key, value in row['FO_Variants'].items():
            if value['Style'] == "fin":
                addchar(key, row['FO_oneword'])
                #print(key, value['Style'])

def addchar(word, word2):
    global chars
    i = 0
    while i < len(word):
        char = word[i]
        combination = None

        # Check for characters that are double
        if i + 1 < len(word) and char == word[i + 1]:
            combination = char * 2
            i += 1  # Skip next character

        # Check for characters followed by ':'
        elif i + 1 < len(word) and word[i + 1] == ':':
            combination = char + ":"
            i += 1  # Skip next character

        # Check for characters followed by 'ː'
        elif i + 1 < len(word) and word[i + 1] == 'ː':
            combination = char + "ː"
            i += 1  # Skip next character

        # Update the chars dictionary with the combination
        if combination:
            chars[combination] = chars.get(combination, {"count":0})
            chars[combination]["count"] = chars[combination]["count"] + 1
            chars[combination].setdefault("uttal", word)
            chars[combination].setdefault("ord", word2)
        # If there's no combination, treat as individual char
        else:
            chars[char] = chars.get(char, {"count":0})
            chars[char]["count"] = chars[char]["count"] + 1
            chars[char].setdefault("uttal", word)
            chars[char].setdefault("ord", word2)

        i += 1

def readpickle(path):
    pickle_file = path+"dataframe.pkl"
    loaded_df = pd.read_pickle(pickle_file)
    print(f"\nLoaded pickle file {pickle_file} with {len(loaded_df)} rows")
    return loaded_df

def savetopickle(df, outputpath):
    output_pickle_file = outputpath+"dataframe.pkl"
    df.to_pickle(output_pickle_file)
    print(f"saved pickle file {output_pickle_file}")

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

def loadlexemes():
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
            word = row["FO_oneword"]
            category_fo = row["FO_PartOfSpeech_class"]
            category_fo_homonum = row["FO_hg"]
            cache_or_api_or_error,hits,lexeme_id,value,language,category,url = search_lexeme(word, category_fo, category_fo_homonum)
            df.at[index, "hits"] = hits
            df.at[index, "lexeme_id"] = lexeme_id
            df.at[index, "value"] = value
            df.at[index, "language"] = language
            df.at[index, "category"] = category
            df.at[index, "url"] = url
            print(f"Row {index + 1}/{len(df)}\t{cache_or_api_or_error}\t{word}\t{hits}\t{lexeme_id}\t{value}\t{language}\t{category}\t{url}")
        print("Done collecting lexeme stats")

    print(f"Total amount of rows: {len(df)}")
    return df

def savechars(outputpath):
    df = pd.DataFrame(chars).T
    df = df.sort_values(by='Count', ascending=False)
    #print(df)
    output_excel_file = outputpath+"output_chars.xlsx"
    df.to_excel(output_excel_file)
    print(f"Saved chars to file: {output_excel_file}")

def savetoexcel(df, outputpath):
    # Create a Pandas Excel writer object
    output_excel_file = outputpath+"output_data.xlsx"
    excel_writer = pd.ExcelWriter(output_excel_file, engine='xlsxwriter')

    # Write each DataFrame to a separate sheet
    print("\nAnalytics")

    print(f"All: Total rows in dataframe: {df.shape[0]}")
    #print(df)
    filtered_df = df[['FO_id', 'FO_Headword', 'FO_compound', 'FO_hg', 'FO_oneword', 'lexeme_id']]
    #filtered_df.to_excel(excel_writer, sheet_name='All', index=False)

    filtered_df = df[df['FO_compound'] == False].copy()
    print(f"Non-compound: Simplex words (FO_compound == False): {filtered_df.shape[0]}")
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Non-compound', index=False)

    filtered_df = df[df['FO_Headword'].str.endswith('-')].copy()
    print(f"Förled: Headword ends with hyphen (-), prefix in FO: {filtered_df.shape[0]}")
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Förled', index=False)

    #print("\nMatched to Wikidata lexemes")
    filtered_df = df[df['lexeme_id'].notnull() & (df['lexeme_id'].astype(str).str.len() > 0)].copy()
    print(f"Lexeme_id: Matched lexemes: {filtered_df.shape[0]}")
    for index, row in filtered_df.iterrows():
        lexeme_id = filtered_df.at[index, "lexeme_id"]
        if filtered_df.at[index, "lexeme_id"] != "":
            filtered_df.at[index, "QS_L"] = lexeme_id
            filtered_df.at[index, "QS_desc_src"] = "P12032"
            filtered_df.at[index, "QS_id"] = '"'+filtered_df.at[index, "FO_id"].replace("FO_", "")+'"'
    #print(filtered_df)
    #filtered_df.to_excel(excel_writer, sheet_name='Lexeme_id', index=False)

    print("\nNew lexeme candidates")
    filtered_df = df.copy()
    values_to_keep = ['havs','båt','fisk','is']
    filtered_df['First_Part'] = filtered_df['FO_Headword'].str.split('-').str[0]
    filtered_df = filtered_df[filtered_df['First_Part'].isin(values_to_keep)]
    count = filtered_df['First_Part'].value_counts()
    count = filtered_df['First_Part'].value_counts().reset_index()
    count.columns = ['First_Part', 'Count']
    merged_df = filtered_df.merge(count, on='First_Part')
    merged_df = merged_df.sort_values(by='Count', ascending=False)
    merged_df = merged_df.head(1000)
    print(f"Förled Limited: Words starting with {values_to_keep} in total: {merged_df.shape[0]}")    
    #print(merged_df)
    merged_df.to_excel(excel_writer, sheet_name='Förled Limited', index=True)

    filtered_df = df.sort_values(by='FO_raw_xml_length', ascending=False).copy()
    filtered_df = filtered_df.head(500)
    print(f"Top by explanation length: {filtered_df.shape[0]}")
    #print(filtered_df)
    filtered_df.to_excel(excel_writer, sheet_name='Top by explanation length', index=False) 

    excel_writer.save()
    print(f"Saved selected dataframes to file: {output_excel_file}")

if loadcacheflag == True:
    loadcache()
if loadlexemesflag == True: 
    df = loadlexemes()
if savetopickeflag == True: 
    savetopickle(df, outputpath)
if readpickleflag == True: 
    df = readpickle(outputpath)
if savetoexcelflag == True: 
    savetoexcel(df, outputpath)
if countcharsflag == False:
    print("Not counting chars")
else: 
    countchars(df)
    print(f"Amount of chars total: {len(chars)}")
    #print(chars)
    savechars(outputpath)