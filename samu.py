import time
from modules.globals import *

class Samu:
    def __init__(self):
        self.CORRECT_ANSWER = None
        self.options_tried = []
        self.discart_options = ["A", "B", "C"]
        self.try_probably_answers = True
        self.try_probably_final_answers = True
    
    def reset(self):
        self.CORRECT_ANSWER = None
        self.options_tried = []
        self.discart_options = ["A", "B", "C"]
        self.try_probably_answers = True
        self.try_probably_final_answers = True


    def try_answer(self):
        # TRY IN ONE PHONE        
        # CHECK IF IS CORRECT - INCORRECT
        self.options_tried.append(self.discart_options[0])
        del self.discart_options[0]

    def discart_everything(self):
        return

    def check_probably_answers(self):
        global probably_answers
        #print(len(probably_answers))
        if len(probably_answers) == 0: return False
        return True

    def check_probably_final_answers(self):
        global probably_final_answers
        #print("ID SAMU: ", id(probably_final_answers))
        if len(probably_final_answers) == 0: return False
        return True

    def run_check(self):
        start = time.time()
        while True:
            time.sleep(0.1)
            if self.check_probably_answers() and self.try_probably_answers: self.print_probably_answer()
            if self.check_probably_final_answers() and self.try_probably_final_answers: self.print_probably_final_answer()
            if time.time() - start > 10: break
            


