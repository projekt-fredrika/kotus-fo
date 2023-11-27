# kotus-fo
Python script to parse wordlist of Finland Swedish dialects published by Institute for the Languages of Finland and prepare data for Wikidata

På svenska: python script för att behandla svenska ord från "Ordbok över Finlands svenska folkmål" utgiven av "Institutet för de inhemska språken" för Wikidata

The publication can be found at https://kaino.kotus.fi/fo/ and is described on Wikipedia at https://sv.wikipedia.org/wiki/Ordbok_över_Finlands_svenska_folkmål

## Workflow and functions
### 1. Creates base data
Collects base data for 79 000 words in dataframe by parsing XML file of publication. XML-files are available for download at https://www.kotus.fi/aineistot/tietoa_aineistoista/sahkoiset_aineistot_kootusti. Parses the metadata in XML to dataframe (Regions, Dialects, Grammer, Gloss, Examples, See Also).

### 2. Matches words to Wikidata lexemes
Searches words in Wikidata for corresponding lexemes with the same lemma, language (Swedish) and category (noun, verb, etc) and adds Wikidata L-code to dataframe. Saves/reads results from/to cache.json in case process is interrupted or later runs. 

At this point: can save result in dataframe as a pickle-file, and can reload dataframe from pickle-file to skip previous steps for fast processing. 

Creates Wikidata Quickstatement commands, to add identifier P12032 (Ordbok över Finlands svenska folkmål ID) to corresponding existing Wikidata lexemes. 

### 3. Creates dialect word as IPA
Converts all dialect words in fin (over 133 000) to IPA (International Phonetic Alphabet) based on conversion table. Wikidata lexemes uses IPA. 

Filters dialect words that are not in "lemma form" according to 6 rules, created based on word list. The challenge has been to mechanically filter out dialect words that are not in the right "lemma form", due to the orignal word list being written to be read by humans, not machines. 

Above was made possible by analyzing used characters in dialects words to create a IPA-conversion table for dialect words written in fin (not grov). 