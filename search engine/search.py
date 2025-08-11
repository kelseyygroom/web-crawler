import json
import nltk
from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer
import time


class SearchEngine():
    def __init__(self):
        self.tokenizer = RegexpTokenizer(r'\b[a-zA-Z0-9]+\b')
        self.stemmer = PorterStemmer()
        self.docfile = open("doc_id_index.json", "r")
        self.doc_index = json.load(self.docfile)
        self.positionsfile = open("positions.json", "rb")
        self.positions = json.load(self.positionsfile)
        self.index = open("inverted_index.json", "rb")

    def close_files(self):
        self.docfile.close()
        self.positionsfile.close()
        self.index.close()

    def parse_query(self, query):
        """
        Given a string query, tokenize/parse/stem in the same way that words were processed in the inverted index. Returns a list of tokens.
        """
        query = query.lower()                                     # for now, query is each word AND-ed. or a single word
        tokenizer = RegexpTokenizer(r'\b[a-zA-Z0-9]+\b')          # same procedure for tokenizing stemming in the index  
        stemmer = PorterStemmer()

        tokens = tokenizer.tokenize(query)

        return [stemmer.stem(word) for word in tokens if word != 'and']         # all queries for now are "AND-ed" ignore the word and; not relevant
            

    def get_postings(self, query):
        """
        Given a list of tokens in a query, search for each token in the inverted index, using seek() and the positions index file.
        Return a list of all the tokens' postings.
        """
        positions = self.positions
        index = self.index
        postings = []
        for q in query: 
            try:
                info = positions[q]
            except:
                return -1
            offset = info["o"]
            index.seek(offset)
            posting = eval(index.readline().strip())[q]
            postings.append(posting)
        return postings             # returns a list of posting dictionaries for each term in the query


    def get_docs(self, posting):
        """
        Given a list of postings, return the document id's that are in common
        """
        posting = sorted(posting, key=len)              # want to intersect the smallest postings each time (more efficient) so sort in ascending
        p1 = list(posting[0].items())                              # get smallest length posting    
        for i in range(1, len(posting)):              # continually intersect the next smallest posting with the already intersected postings
            p2 = list(posting[i].items())
            p1 = self.intersect(p1, p2)
        
        return sorted(p1, key=lambda x:x[1], reverse=True)


    def intersect(self, p1, p2):
        """
        Intersect two lists of tuples (doc_id, tf-idf) based on their document id's. Sums the tf-idf scores of common documents 
        and returns a singular posting list of tuples containing common document_ids with summed tf-idf scores. 
        """
        answer = []             # to store the document id's in common
        len1 = len(p1)
        len2 = len(p2)
        # need to be sorted in ascending order for merging to work
        p1 = sorted(p1, key=lambda x:x[0])         
        p2 = sorted(p2, key=lambda x:x[0])
        i1 = 0
        i2 = 0

        while i1 < len1 and i2 < len2:
            if p1[i1][0] == p2[i2][0]: 
                answer.append((p1[i1][0], round(p1[i1][1]+p2[i2][1], 3)))       # append the doc id and sum tf-idf scores
                i1+=1
                i2+=1
            elif p1[i1][0] < p2[i2][0]:           # otherwise increment p1
                i1+=1
            else:
                i2 += 1
        
        return answer


    def results(self, docs):
        """
        Given a list of doc id's, print all the matching URLs. The index already sorts documents in descending order of tf-idf
        scores, so simply return in order and they will already be ranked.
        """
        doc_index = self.doc_index
        i = 1
        for doc, _ in docs:
            print(f"\t{i}. {doc_index[doc]}")
            i+=1
            if (i > 50):
                break


    def search(self, query):
        parsed = self.parse_query(query)
        postings = self.get_postings(parsed)
        if postings == -1:
            print("No Results Found for Query:", query)
        else:
            docs = self.get_docs(postings)
            self.results(docs)


if __name__ == "__main__":
    SE = SearchEngine()
    query = input("Search (Type QUIT_SE to quit): ")
    while query != "QUIT_SE":                     # has to be quit by Ctrl+C in terminal killing program
        if query == "" or query.isspace():
            continue
        before = time.time() *1000           # time in ms
        SE.search(query)
        after = time.time() *1000
        print("TIME TO PROCESS QUERY:", after-before, "ms")
        query = input("Search (Type QUIT_SE to quit): ")
    
    SE.close_files()