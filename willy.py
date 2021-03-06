from modules.globals import *
from modules.recognition import get_query
from modules.text_procesing import *
from googleapiclient.discovery import build 
from bs4 import BeautifulSoup
import requests
import concurrent.futures
from math import log
import time

class Willy:
    def __init__(self):

        # Yeah you need to enter your keys in a txt and type the path her
        keys = open(r"C:\Users\Usuario\Documents\Proyects 2021\Willy Proyect\modules\keys.txt", "r")
        self.api_key = keys.readline()[:-1]
        self.cse_id = keys.readline()
        keys.close()

        self.no_in_question = False
        self.brute_question = None
        self.brute_answers = None
        self.token_question = None
        self.token_answers = None
        self.answer_key_words = []
        self.data = []

        self.search_titles = []
        self.search_snippets = []
        self.doc_name = ""

        self.urls = []
        self.exclude_urls = []

        self.preliminary_scores = [] # Lista de listas de los score de googl_search, doc_name y snipper
        self.sentence_tf_idf_score = []
        self.final_answ_score = [] # Scores de respuestas

        # probably_answers (GLOBAL) lista con las respuestas en orden
        # probably_final_answers (GLOBAL) lista con las respuestas en orden

    def reset(self):
        global probably_answers 
        global probably_final_answers
        del probably_answers[:]
        del probably_final_answers[:]

        self.answer_key_words = []

        self.search_titles = []
        self.search_snippets = []

        self.urls = []
        self.exclude_urls = []

        self.preliminary_scores = []
        self.final_answ_score = []
        

    def parser_aux(self, tag):
        token = token_string(tag.get_text(strip=True, separator=" "))
        for word in self.answer_key_words:
            if word in token:
                self.data.append(token)
                return

    def parse(self):
        for i, url in zip(range(0,5), self.urls + self.exclude_urls):
            i+=1
            print("Parsing url Nro", i)
            self.data = []
            try: 
                soup = BeautifulSoup(requests.get(url).text, "html.parser")
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    found = [executor.submit(soup.find_all, tag) for tag in ["li","p"]]
                    for exe in found: 
                        for tag in exe.result(): self.parser_aux(tag)
                if len(self.data) > 0: return 1
            except: pass
        return 0
        

    def google_search(self):
        query = procces_google_query(self.brute_question)
        results = build("customsearch","v1",developerKey=self.api_key).cse().list(q=query,cx=self.cse_id,num=5).execute()
        if not results.get('items'): return 0 

        for r in results['items']:
            self.search_titles.append(r['title'])
            self.search_snippets.append(r['snippet'])
            url_low = r['link'].lower()
            if url_low.find("youtube") == -1 and url_low.find("anexo") == -1 and url_low.find("archivo") == -1 and url_low.find("image") == -1:
                self.urls.append(r['link'])
                if len(self.urls) == 1: self.doc_name = r['title']
            else: self.exclude_urls.append(r['link'])

        if len(self.urls) == 0: return -1
        return 1
    
    def pre_score(self, code): # Se busca respuesta en titulo, en busqueda y en snippets
        
        if code == "snip": token = token_string(" ".join(self.search_snippets))
        elif code == "goog": token = token_string(" ".join(self.search_titles))
        elif code == "docn": token = token_string(self.doc_name)

        score = [0,0,0]
        for word in token:
            for i in range(len(self.token_answers)):
                if word in self.token_answers[i]: score[i] += 1
        
        self.preliminary_scores.append(score[:])
        return True

    def edit_possible_answers(self): # Se ejecuta despues de haber buscado respuesta en titulo, busqueda y snip
        global probably_answers
        general_score = [[0,"A"],[0,"B"],[0,"C"]]
        for s_list in self.preliminary_scores:
            for i in range(len(s_list)): general_score[i][0] += s_list[i]
        general_score.sort(reverse= (not self.no_in_question)) # GLOBAL NO IN QUESTION?
        probably_answers = general_score[:]
        return
    
    def tf_idf_score(self):
        self.sentence_tf_idf_score = [0 for i in range(len(self.data))] # Score of all Sentences
        for word in self.token_question: # Calc idf for each word in question
            # Calc Idf for every word in question
            div = 0
            for sentence in self.data:
                if word in sentence: div += 1
            if div == 0: continue

            # Calc Tf for every paragraph with word and multiply with idf
            for i in range(len(self.data)): self.sentence_tf_idf_score[i] += (self.data[i].count(word) / len(self.data[i])) * log(len(self.data) / div)
                
        # Calc sentence query_density
        for i in range(len(self.data)):
            cont = 0
            for word in self.token_question:
                if word in self.data[i]: cont += 1
            self.sentence_tf_idf_score[i] *= cont / len(self.data[i])

        # VARIANTE - anwer_density (Error Similar_Answers)
        for i in range(len(self.data)):
            answer_score = [0,0,0]
            for j in range(3):
                for word in self.token_answers[j]:
                    if word in self.data[i]: answer_score[j] += 1
                answer_score[j] /= len(self.token_answers[j]) 
            self.sentence_tf_idf_score[i] *= max(max(answer_score[0], answer_score[1]), answer_score[2])
        return
            
    def no_final_answer(self):
        global probably_final_answers
        valid_answers = [False,False,False]
        cont_True = 0

        for sentence in self.data:
            for i in range(3):
                if valid_answers[i]: continue
                for word in self.token_answers[i]:
                    if word in sentence:
                        valid_answers[i] = True
                        cont_True += 1
                        break
            if cont_True == 3: break
                
        if cont_True == 1 or cont_True == 2:
            for i in range(3):
                if not valid_answers[i]: probably_final_answers.append(chr(i+65))
            return

        self.tf_idf_score()
        maxi = 0
        for i in range(len(self.sentence_tf_idf_score)):
            if self.sentence_tf_idf_score[i] > self.sentence_tf_idf_score[maxi]: maxi = i
        self.ident_answer_from_sentenence(self.data[maxi])
        

    def final_answer(self):
        self.tf_idf_score()
        maxi = 0
        for i in range(len(self.sentence_tf_idf_score)):
            if self.sentence_tf_idf_score[i] > self.sentence_tf_idf_score[maxi]: maxi = i
        self.ident_answer_from_sentenence(self.data[maxi])

    def run(self, q_lines):

        # READ AND PROCESS QUESTION & ANSWERS
        s = time.time()
        self.brute_question, self.brute_answers = get_query(q_lines)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            nq = executor.submit(search_no_question, self.brute_question)
            tq = executor.submit(token_string, self.brute_question)
            ta = [executor.submit(token_string, a) for a in self.brute_answers]

            self.no_in_question = nq.result()
            self.token_question = tq.result()
            self.token_answers = [exe.result() for exe in ta]
            for answ in self.token_answers: self.answer_key_words += [word for word in answ if word not in self.answer_key_words]

        # GOOGLE SEARCH
        var = self.google_search()
        if var == 0:
            print("No Google Results D:")
            return 

        # Check answer in search, snippet, doc name and start final answer
        with concurrent.futures.ThreadPoolExecutor() as executor:
            parser = executor.submit(self.parse)
            scores1 = [executor.submit(self.pre_score, c) for c in ["snip", "goog", "docn"]]
            for i in range(3): scores1[i].result()
            self.edit_possible_answers()

            if parser.result(): f_answ = executor.submit(self.final_answer) if not self.no_in_question else executor.submit(self.no_final_answer)
            else: 
                print('NO ANSWERS ANYWHERE :(')
                return
            f_answ.result()
        return

    # FUNCION PARA IDENTIFICACION DE RESPUESTA
    def ident_answer_from_sentenence(self, sentence):
        global probably_final_answers
        # ANSWER DENSITY
        self.final_answ_score = [0,0,0]
        for i in range(3):
            for word in self.token_answers[i]: self.final_answ_score[i] += sentence.count(word)
            self.final_answ_score[i] /= len(self.token_answers[i])
        
        # ANSWER WORDS CLOSE TO QUESTION WORDS
        answers_score2 = [0,0,0]
        question_words_index = []
        for question_word in self.token_question:
            for i in range(len(sentence)):
                if question_word == sentence[i]: question_words_index.append(i)
        
        for i in range(3):
            answer_index = []
            for answer_word in self.token_answers[i]:
                for j in range(len(sentence)):
                    if answer_word == sentence[j]: answer_index.append(j)

            for q_index in question_words_index:
                if len(answer_index) == 0: continue
                count = 0
                for a_index in answer_index: count += abs(q_index - a_index)
                count /= len(answer_index)
                answers_score2[i] += count
            if len(question_words_index) == 0 or len(answer_index) == 0: answers_score2[i] = len(sentence)
            answers_score2[i] /= len(question_words_index)


        self.final_answ_score = [(self.final_answ_score[i] * 100) / answers_score2[i] for i in range(3)]

        # MOST REPEATED ANSWER IN ALL DATA
        answers_score2 = [0,0,0]
        for i in range(3):
            for sent in self.data:
                count = 0
                for word in self.token_answers[i]: count += sent.count(word)
                answers_score2[i] +=  count / len(sent)

        self.final_answ_score = [self.final_answ_score[i] + answers_score2[i] for i in range(3)]
        
        aux = [[self.final_answ_score[i], chr(i+65)] for i in range(len(self.final_answ_score))]
        aux.sort(reverse= (not self.no_in_question))
        probably_final_answers = aux[:]
