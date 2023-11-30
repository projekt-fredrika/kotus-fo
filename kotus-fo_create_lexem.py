#!/usr/bin/python3
import pandas as pd
import LexData
import pywikibot
from config import USERNAME_WIKIDATA, PASSWORD_WIKIDATA, PATH
import csv
import sys
from SPARQLWrapper import SPARQLWrapper, JSON

lemma = "havstorn"
sv = LexData.Language("sv", "Q9027")
repo = LexData.WikidataSession(USERNAME_WIKIDATA, PASSWORD_WIKIDATA)

path = PATH
#inputfile = "kotus-fo_create_lexem-input.xlsx"
inputfile = "output_uttal_regioner_exploded_no_formatting.xlsx"
csv_file_path = path + "kotus-fo_create_lexem_quickstatement.csv"
unique_file_path = path + "kotus-fo_create_lexem-results-unique.csv"

def read(excel_file_path):
    columns_to_read = ['FO_headword', 'FO_id', 'FO_compound', 'FO_PartOfSpeech_class_first', 'WD_åtgärd', "WD_lexeme_id", "WD_uttal_IPA", "WD_region"]
    df = pd.read_excel(excel_file_path, sheet_name="Sheet1", usecols=columns_to_read)
    print(f"total rows {df.shape[0]}")
    return df


def searchforform(lexem, grammatical):
    endpoint_url = "https://query.wikidata.org/sparql"

    gramquery = ""
    i = 1
    for g in grammatical: 
        gramquery += f"?form wikibase:grammaticalFeature ?feat{i}. VALUES ?feat{i} {{wd:{g}}}\n"
        i = i+1

    query = """SELECT DISTINCT ?form
    WHERE {
    VALUES ?l {wd:lexemvalue}
    ?l a ontolex:LexicalEntry ;
        dct:language wd:Q9027 ;
        dct:language ?lang;
        wikibase:lemma ?lemma .
    ?l ontolex:lexicalForm ?form.
    ?l wdt:P12032 ?foid.

    ?form a ontolex:Form .
    ?form ontolex:representation ?word .
    gramquery
    
    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } ORDER BY ?lemma 

    """.replace("lexemvalue",lexem).replace("gramquery",gramquery)

    #print(query)

    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    queryresult = sparql.query().convert()
    result = None
    for qr in queryresult["results"]["bindings"]:
        result = qr["form"]["value"]
        break
    return result



def createlexemes(df):
    df_unique = df.drop_duplicates(subset=['FO_headword', 'FO_PartOfSpeech_class_first'])
    print(f"unique FO_headword & FO_PartOfSpeech_class_first (can be same as existing lexemes ): {df_unique.shape[0]}")

    categories = {
        "substantiv" : "Q1084", # https://www.wikidata.org/wiki/Q1084
        "verb" : "Q24905", # https://www.wikidata.org/wiki/Q24905
        "adjektiv" : "Q34698", # https://www.wikidata.org/wiki/Q34698
        "interjektion" : "Q83034", #https://www.wikidata.org/wiki/Q83034
        "räkneord" : "Q63116", #https://www.wikidata.org/wiki/Q63116
        "adverb" : "Q380057", #https://www.wikidata.org/wiki/Q380057
        "preposition" : "Q4833830", #https://www.wikidata.org/wiki/Q4833830
        "konjunktion" : "Q36484", #https://www.wikidata.org/wiki/Q36484
        "adverb" : "Q380057", #https://www.wikidata.org/wiki/Q380057
        "pronomen" : "Q36224", #https://www.wikidata.org/wiki/Q36224
        "ortnamn" : "Q7884789", #https://www.wikidata.org/wiki/Q7884789
    }

    i = 0
    list = []
    uniquelist = []
    for index, row in df_unique.iterrows():
        lemma = row["FO_headword"]
        lemma1 = None
        lemma2 = None
        if len(lemma.split('-'))>1:
            lemma1 = lemma.split('-')[0].strip()
            lemma2 = lemma.split('-')[1].strip()
        lemma = lemma.replace('-', '').strip()

        cat = row["FO_PartOfSpeech_class_first"]
        id = row["FO_id"].replace("FO_","")
        cat_wikidata = categories.get(cat,"")
        print(f"Rad {index + 1}: {lemma}, {cat} ({cat_wikidata}), {id}, {lemma1}, {lemma2}")

        L1 = LexData.get_or_create_lexeme(repo, lemma, sv, cat_wikidata)
        #print(L1['lemmas']['sv']['value'], L1["id"])
        uniquelist.append([L1['id'],lemma])
        list.append([L1['id'],"P12032",f'"{id}"'])

        if lemma1 is not None or lemma2 is not None:
            print("creating lemma1 and lemma2")
            L2 = LexData.get_or_create_lexeme(repo, lemma1, sv, cat_wikidata)
            list.append([L1['id'],"P5238",L2['id'],"P1545",'"1"'])
            L3 = LexData.get_or_create_lexeme(repo, lemma2, sv, cat_wikidata)
            list.append([L1['id'],"P5238",L3['id'],"P1545",'"2"'])


        # print(L1['lemmas']['sv']['value'], L2['lemmas']['sv']['value']), {L3['lemmas']['sv']['value']} 
        grammatical = []
        if cat=="substantiv":
            grammatical = ["Q131105","Q110786","Q53997857"] # nominativ, singular, obestämd
        if cat=="verb":
            grammatical = ["Q179230","Q1317831"] # infinitiv, aktivum
        if cat=="adjektiv":
            grammatical = ["Q1305037","Q110786","Q53997857","Q3482678"] # utrum, singular, obestämd, positiv
        if cat=="interjektion": # ingen, enligt t.ex. https://w.wiki/7xUQ
            grammatical = []
        if cat=="räkneord": # ingen, enligt t.ex. https://www.wikidata.org/wiki/Lexeme:L579173
            grammatical = []
        if cat=="adverb": # https://w.wiki/7xV3
            grammatical = []
        if cat=="preposition": #
            grammatical = []
        if cat=="konjunktion": # https://w.wiki/8KzC
            grammatical = []
        if cat=="adverb": #
            grammatical = []
        #if cat=="pronomen": #
        #    grammatical = []
        #if cat=="ortnamn": #
        #    grammatical = []

        print(lemma, L1["id"], cat, grammatical)

        formid = None
        formid_url = searchforform(L1['id'],grammatical)

        if formid_url == None:
            if grammatical != None:
                formid = L1.createForm(lemma, grammatical)
                print(f"created form {formid}")
            else:
                formid = "ERROR"
                print(f"SHOULD CREATE FORM")
        else:
            formid = formid_url.split("/")[len(formid_url.split("/"))-1]
            print(f"found formid {formid}")

        filtered_df = df[df["FO_headword"] == row["FO_headword"]]
        #print(filtered_df)
        for index, row2 in filtered_df.iterrows():
            #L1form = f"{L1['id']}-{id}"
            L1form = formid
            uttal = '"'+row2["WD_uttal_IPA"]+'"'
            region = row2["WD_region"]
            list.append([L1form,"P898",uttal,"P407","Q9027","P5237",region])
        print("---")

    print(df)

    with open(csv_file_path, 'w') as file:
        text = ""
        for row in list:
            for item in row: 
                text = text+"\t"+item
            text = text + '\n'
        file.write(text)

    with open(unique_file_path, 'w') as file:
        text = "unika L-koder"
        for row in uniquelist:
            text = text+"\n"
            for item in row: 
                text = text+"\t"+item
        file.write(text)



# Run script here. various filters to control what words to run: 

df = read(path+inputfile) 
#df = df[df['FO_headword'] == 'börja'].copy()
df = df[(df['FO_compound'] == 'simplex') & (df['WD_åtgärd'] == 'Ja, uppdatera existerande lexem') & (df['FO_headword'].str.startswith('b')) & (df['FO_PartOfSpeech_class_first'] != '')  ].copy()
#df = filtered_df = df[df['FO_headword'].between('att', 'att')].copy()
#df = filtered_df = df[df['FO_headword'].between('apotek', 'baba')].copy()
#df = df[(df['FO_compound'] == 'simplex') & (df['WD_åtgärd'] == 'Ja, skapa lexem')].copy()
# en rad innan : sista raden

# prints overview of input: 
print(df)
unique_count = df['FO_headword'].nunique()
print("unique FO_headword", unique_count)
unique_count = df['WD_lexeme_id'].nunique()
print("unique lexem", unique_count)
unique_count = df['WD_uttal_IPA'].nunique()
print("WD_uttal_IPA", unique_count)
print("Rader totalt", len(df))


# creates lexemes, forms and creates quickstatement commands 
createlexemes(df)