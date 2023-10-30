#!/usr/bin/python3
import pandas as pd
import LexData
import pywikibot
from config import USERNAME_WIKIDATA, PASSWORD_WIKIDATA, PATH
import csv

lemma = "havstorn"
sv = LexData.Language("sv", "Q9027")
repo = LexData.WikidataSession(USERNAME_WIKIDATA, PASSWORD_WIKIDATA)

path = PATH
inputfile = "kotus-fo_create_lexem-input.xlsx"
csv_file_path = path + "kotus-fo_create_lexem_quickstatement.csv"
unique_file_path = path + "kotus-fo_create_lexem-results-unique.csv"

def read(excel_file_path):
    columns_to_read = ['FO_headword', 'FO_id', 'FO_PartOfSpeech_class_first', "WD_lexeme_id", "WD_uttal_IPA", "WD_region"]
    df = pd.read_excel(excel_file_path, sheet_name="skapa", usecols=columns_to_read)
    print(f"total rows {df.shape[0]}")
    return df

def createlexemes(df):
    df_unique = df.drop_duplicates(subset='FO_headword')
    print(f"without duplicates: {df_unique.shape[0]}")

    categories = {
        "substantiv" : "Q1084", # https://www.wikidata.org/wiki/Q1084
        "verb" : "Q24905", # https://www.wikidata.org/wiki/Q24905
        "adjektiv" : "Q34698", # https://www.wikidata.org/wiki/Q34698
        "interjektion" : "Q83034", #https://www.wikidata.org/wiki/Q83034
        "räkneord" : "Q63116", #https://www.wikidata.org/wiki/Q63116
        "adverb" : "Q380057", #https://www.wikidata.org/wiki/Q380057
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
        uniquelist.append([L1['id'],lemma])
        list.append([L1['id'],"P12032",f'"{id}"'])
        if lemma1 is not None or lemma2 is not None:
            L2 = LexData.get_or_create_lexeme(repo, lemma1, sv, cat_wikidata)
            list.append([L1['id'],"P5238",L2['id'],"P1545",'"1"'])
            L3 = LexData.get_or_create_lexeme(repo, lemma2, sv, cat_wikidata)
            list.append([L1['id'],"P5238",L3['id'],"P1545",'"2"'])

#        print(L1['lemmas']['sv']['value'], L2['lemmas']['sv']['value']), {L3['lemmas']['sv']['value']} 

        if len(L1.forms) == 0 and cat=="substantiv":
            L1.createForm(lemma, ["Q110786","Q131105","Q53997857"]) # singular, nominativ, obestämd
        if len(L1.forms) == 0 and cat=="verb":
            L1.createForm(lemma, ["Q179230","Q1317831"]) # infinitiv, aktivum
        if len(L1.forms) == 0 and cat=="adjektiv":
            L1.createForm(lemma, ["Q1305037","Q110786","Q53997857","Q3482678"]) # utrum, singular, obestämd, positiv
        if len(L1.forms) == 0 and cat=="interjektion": # ingen, enligt t.ex. https://w.wiki/7xUQ
            L1.createForm(lemma, [])
        if len(L1.forms) == 0 and cat=="räkneord": # ingen, enligt t.ex. https://www.wikidata.org/wiki/Lexeme:L579173
            L1.createForm(lemma, [])
        if len(L1.forms) == 0 and cat=="adverb": # https://w.wiki/7xV3
            L1.createForm(lemma, [])

        filtered_df = df[df["FO_headword"] == row["FO_headword"]]
        print(filtered_df)
        for index, row2 in filtered_df.iterrows():
            L1form = f"{L1['id']}-F1"
            uttal = '"'+row2["WD_uttal_IPA"]+'"'
            region = row2["WD_region"]
            list.append([L1form,"P898",uttal,"P407","Q9027","P5237",region])
        print("---")

    print(df)

    with open(csv_file_path, 'w') as file:
        text = ""
        for row in list:
            print(row)
            for item in row: 
                text = text+"\t"+item
            text = text + '\n'
        file.write(text)

    with open(unique_file_path, 'w') as file:
        text = "unika Q-koder"
        for row in uniquelist:
            text = text+"\n"
            for item in row: 
                text = text+"\t"+item
        file.write(text)

    # You can easily create forms…
    #if len(L2.forms) == 0:
    #    L2.createForm("firsts", ["Q146786"])

    # …or senses, with or without additional claims
    #if len(L2.senses) == 0:
    #    L2.createSense(
    #        {
    #            "en": "Element in an ordered list which comes before all others according to the ordering",
    #            "de": "einer Ordnung folgend das Element vor allen anderen",
    #        },
    #        claims={"P5137": ["Q19269277"]},
    #    )

df = read(path+inputfile)
createlexemes(df)