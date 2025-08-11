from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer
import json
import os
import math


class InvertedIndex():
    def __init__(self):
        self.letter_buckets = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))          # letter buckets for partial saving {char: {term: {doc_id: tf}}}
        self.doc_index = {}                                         # {doc_id: url}
        self.partial_id = 0
        self.current_doc_id = 0             # to save the current doc id
        self.tag_weights = {                # to add higher importance to diff parts of the content
            "title": 5,
            "h1": 4,
            "h2": 3,
            "h3": 2,
            "strong": 2,
            "em": 2,
            "b": 1.5,
            "i": 1.5,
            "mark": 1.5,
            "body": 1,
            "p": 1,
            "li": 1
        }
        self.tokenizer = RegexpTokenizer(r'\b[a-zA-Z0-9]+\b')           # only alphanumeric sequences
        self.stemmer = PorterStemmer()
        self.NUM_DOCS = 55393


    def tokenize(self, text):
        tokens = self.tokenizer.tokenize(text)
        return [self.stemmer.stem(word) for word in tokens]
    
    
    def check_html(self, text):
        for c in text:
            if not c.isspace():
                return c == '<'             # sign that content is probably html
        return False

    
    def parse_file(self, f):
        """
        Given a single json file, extract the text content, call tokenize, and store the tokens/words and frequencies in the inverted index
        """
        with open(f, "r") as file:
            try:
                data = json.load(file)
                if not self.check_html(data.get("content", "")):
                    return                                                  # skip this document/url -- likely not html     
                soup = BeautifulSoup(data["content"], "lxml")
                doc_id = self.store_doc_id(data["url"])
                self.store_by_tag(soup, doc_id)         # divide up by tags. and call tokenize for each tag.                
            except Exception as e:
                print(f"Error with file {f}: {e}")


    def store_by_tag(self, soup, doc_id):
        """
        Given a beautiful soup object, parse by tags to add weighted terms to the inverted_index
        """
        for element in soup.find_all(True):
            tag = element.name
            if tag in self.tag_weights:
                weight = self.tag_weights[tag]
                text = element.get_text(separator=" ").lower()
                tokens = self.tokenize(text)
                self.store_tokens(tokens, doc_id, weight)


    def store_doc_id(self, url): 
        """Given a url, calculates the doc_id and stores in the doc_id index"""
        doc_id = self.current_doc_id
        self.doc_index[doc_id] = url
        self.current_doc_id += 1
        return doc_id


    def store_tokens(self, tokens, doc_id, count):  
        """
        Stores the token in its corresponding letter bucket. Associates posting: {doc_id: frequency}.
        """      
        for word in tokens:
            bucket = word[0] if 'a' <= word[0] <= 'z' else 'other'
            self.letter_buckets[bucket][word][doc_id] += count


    def save_index(self):
        for bucket in self.letter_buckets:
            sorted_dict = dict(sorted(self.letter_buckets[bucket].items()))
            with open(f"{bucket}_{self.partial_id}.json", "w") as f:
                json.dump({k: dict(v) for k, v in sorted_dict.items()}, f)
            
        self.partial_id += 1
        self.letter_buckets.clear()

    def merge(self, dicts):
        """
        Helper function for the merge_index function. Given a list of dictionaries, merge them into a single dictionary and return that
        dictionary.
        """
        merged = {}
        for d in dicts:
            for term, postings, in d.items():
                if term not in merged:
                    merged[term] = postings.copy()
                else:
                    merged[term].update(postings)
        return merged
    
    
    def merge_index(self):
        """
        Main function for merging the partial letter-grouped index files. First, merge the partial index files into 27
        letter bucketed index files using the merge() function. Then, store those merged files into the main inverted index,
        tracking and maintaining position information for each term for later use when processing queries.
        """
        # merge the partial letter-grouped index files into 27 singular letter-grouped index files. and add them to main inverted index with positions dictionary for seeking:)
        letters = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','other']
        index = open("inverted_index.json", "w")
        positions_dict = {}
        byte_offset = 0
        for letter in letters:
            lst = []
            for num in range(6):
                filename = f"{letter}_{num}.json"
                with open(filename, "r") as f:
                    lst.append(json.load(f))
                os.remove(filename)         # delete the partial indexes
            
            merged = self.merge(lst)         # merge the dicts for each letter bucket
            byte_offset = self.store_merged(index, positions_dict, merged, byte_offset)
        
        index.close()
        
        with open("positions.json", "w") as positions_file:
            json.dump(positions_dict, positions_file)


    def tf_idf_postings(self, postings):
        """
        Given a dictionary of postings formatted as doc_id: tf, calculate the tf-idf score for each document a term is found in.
        Update the dictionary accordingly
        """
        df = len(postings)          # the number of docs the term is found in is the length of the postings dictionary
        N = self.NUM_DOCS           # total number of docs; doesn't change w this implementation
        idf = math.log10(N/df)      
        for doc_id, freq in postings.items():
            tf_idf = (1+math.log10(freq)) * idf
            postings[doc_id] = round(tf_idf, 3)
        
        return dict(sorted(postings.items(), key= lambda x:x[1], reverse=True))           # sort in descending order of tf-idf score for easier retrieval access in future. 


    def store_merged(self, index, positions_dict, merged, byte_offset):
        """
        Given a dictionary of merged terms and postings, write to the main index file. Also store
        positional information and length in order to seek() when processing queries.
        """
        for term, posting in merged.items():
            posting = self.tf_idf_postings(posting)      # calculate tf-idf posting here
            entry = json.dumps({term:posting}) + "\n"    # create json object
            index.write(entry)                           # write to the index file. newline for each index object -- easier retrieval/readability   
            length = len(entry)                                 
            positions_dict[term] = {"o":byte_offset, "l":length}       # write to positions dict w offset and length of entry
            byte_offset += length + 1                                      # update current byte offset
        return byte_offset


    def construct_index(self):
        # navigate thru each file in the DEV directory, calling parse_file on each file.
        p = Path('DEV')
        count = 0
        for dir in p.iterdir():
            print("processing:", dir)
            for file in dir.iterdir():
                count+=1
                self.parse_file(file)
                if count % 10000 == 0:         # storing the data every 10000 docs to avoid overloading memory. offload 5-6x = 5-6 partial indexes to merge at the end.
                    self.save_index()

        self.save_index()      # save the index @ the end again - final save
        self.merge_index()

        with open("doc_id_index.json", "w") as d:
            json.dump({str(k): v for k, v in self.doc_index.items()}, d)
        


if __name__ == "__main__":
    index = InvertedIndex()
    index.construct_index()