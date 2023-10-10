# kotus-fo
Python script to parse wordlist of Finland Swedish dialects published by Institute for the Languages of Finland

På svenska: python script för att behandla svenska ord från "Ordbok över Finlands svenska folkmål" utgiven av "Institutet för de inhemska språken"

The publication can be found at https://kaino.kotus.fi/fo/

## Workflow and functions
1. Creates base data for over 70 000 words in dataframe by parsing XML file of publication. XML-files are available for download at https://www.kotus.fi/aineistot/tietoa_aineistoista/sahkoiset_aineistot_kootusti
2. Searches words in wikidata for corresponding lexemes with the same lemma, language (Swedish) and category (noun, verb, etc) and adds wikidata L-code to dataframe. Saves/reads results from/to cache.json in case process is interrupted. 
3. Saves result as dataframe as a pickle-file, and can reload dataframe from pickle-file to skip previous steps for fast processing. 
4. Filters and manipulates data as needed and outputs as sheets in excel file output-data.xlsx
5. List characters used in words' dialect descriptions for creating conversion table to (IPA) International Phonetic Alphabet

## Beneficial outputs
- Sheet with matched words with needed Wikidata Quickstatement commans to add identifier P12032 (Ordbok över Finlands svenska folkmål ID) to corresponding Wikidata lexemes. 
- Sheet with interesting lexemes mechanically picked for creation as Wikidata lexemes
- Sheet with used characters for preparing IPA conversion
