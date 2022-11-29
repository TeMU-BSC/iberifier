from transformers import AutoModelForTokenClassification, AutoTokenizer
import numpy as np
from pprint import pprint
from typing import NamedTuple


class MultipleStartStatesError(Exception):
    """
    Exception raised when trying to set multiple start states of the Finite State Machine.
    """
    def __init__(self, message="Start State already set. Only one start state can be set per Finite State Machine"):
        super().__init__(self, message)


class StartStateNotSetError(Exception):
    """
    Exception raised when trying to run the Finite State Machine without setting a start.
    """
    def __init__(self, message="Trying to start the Finite State Machine without setting a start state. A start state must be set per Finite State Machine"):
        super().__init__(self, message)


class NoEndStatesAvailableError(Exception):
    """
    Exception raised when trying to run the Finite State Machine without setting end states.
    """
    def __init__(self, message="Trying to start the Finite State Machine without setting any end state. At lest one end state must be set"):
        super().__init__(self, message)


class InvalidTransitionWarning(Exception):
    """
    Exception raise when trying an invalid transition in the Finite State Machine
    """
    def __init__(self, message="Trying an invalid transition in the Finite state Machine"):
        print("WARNING", message)


class WrongTransitionError(Exception):
    """
    Exception raised when something that is not "BIOES" comes as a transition.
    """
    def __init__(self, message="The transition is not in 'BIOES' format"):
        super().__init__(self, message)


class EmptyTokenError(Exception):
    """
    Exception raised when something that is not "BIOES" comes as a transition.
    """
    def __init__(self, message="There are several emty tokens."):
        super().__init__(self, message)


class CharSpan(NamedTuple):
    """
    Character span in the original string.
    Args:
        start (`int`): Index of the first character in the original string.
        end (`int`): Index of the character following the last character in the original string.
    """
    start: int
    end: int


class FiniteStateMachine:
    """
    Finite State Machine to join entitites.
    
    """
    def __init__(self):
        self.handlers = {}
        self.startState = None
        self.endStates = []
        self.aggregation_strategy = None

    def add_state(self, state, handler, end_state=False):
        self.handlers[state] = handler
        if end_state:
            self.endStates.append(state)

    def set_start_state(self, state):
        if self.startState is not None: raise MultipleStartStatesError
        else: self.startState = state

    def remove_start_state(self):
        self.startState=None

    def add_aggregation_strategy(self, aggregation_strategy=None):
        """
        Function that given a list of text, entities and scores return a single entity.
        by default return the concatenation of all text, the most common entity and the 
        """
        def most_common(l):
            return max(set(l), key=l.count)

        def average(l):
            return sum(l) / len(l)

        if aggregation_strategy is None:
            def aggregation_strategy(tb, eb, sc):
                return ("".join(tb), 'O' if not eb else most_common(eb), sum(sc) / len(sc))

        self.aggregation_strategy = aggregation_strategy

    def run(self, entities):
        if self.startState is None: raise StartStateNotSetError
        if len(self.endStates) == 0: raise NoEndStatesAvailableError
        
        handler = self.handlers[self.startState]

        text_buffer = []
        entity_buffer = []
        score_buffer = []
        span_start = None
        span_end = None

        out_entities = []

        for entity in entities:
            newState, text_buffer, entity_buffer, scores_buffer, span_start, span_end = handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end)
            if newState in self.endStates:
                text, entity, score = self.aggregation_strategy(text_buffer, entity_buffer, score_buffer)
                out_entities.append({"entity": entity, "score": score, "word": text, "span": CharSpan(span_start, span_end)})
                text_buffer = []
                entity_buffer = []
                score_buffer = []
                span_start = None
                span_end = None
            handler = self.handlers[newState]
        return out_entities


class CustomNerPipeline:
    """
    Implement a custom ner pipeline using the FiniteStateMachineJoinEntities class implementing custom handlers.

    """

    def softmax(self, x):
        """Compute softmax values for each sets of scores in x."""
        return np.exp(x) / np.sum(np.exp(x), axis=0)

    def __init__(self, model, tokenizer):

        # Add model and tokenizer
        self.model = model
        self.tokenizer = tokenizer
        self.punct = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~', '¿', '¡', '</s>']

        def b_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            if entity["word"] == '': return "END", text_buffer, entity_buffer, score_buffer, span_start, span_end
            _type = entity["entity"].split('-', 1)[:1][0]
            text_buffer.append(entity["word"])
            score_buffer.append(entity["score"])
            if span_start is None and entity["span"] is not None: span_start = entity["span"].start
            if entity["span"] is not None: span_end = entity["span"].end
            if _type == 'B': newState = "B"
            elif _type == 'I': newState = "B"
            elif _type == 'O': newState = "B"
            elif _type == 'E': newState = "S" 
            elif _type == 'S': newState = "B"
            else: raise WrongTransitionError
            if entity["entity"] != 'O':
                entity_buffer.append(entity["entity"])
                entity_buffer = [newState + ent[1:] for ent in entity_buffer]
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end

        def i_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            if entity["word"] == '': return "END", text_buffer, entity_buffer, score_buffer, span_start, span_end
            _type = entity["entity"].split('-', 1)[:1][0]
            text_buffer.append(entity["word"])
            score_buffer.append(entity["score"])
            if span_start is None and entity["span"] is not None: span_start = entity["span"].start
            if entity["span"] is not None: span_end = entity["span"].end
            if _type == 'B': newState = "I"
            elif _type == 'I': newState = "I"
            elif _type == 'O': newState = "I"
            elif _type == 'E': newState = "S" 
            elif _type == 'S': newState = "S"
            else: raise WrongTransitionError
            if entity["entity"] != 'O':
                entity_buffer.append(entity["entity"])
                entity_buffer = [newState + ent[1:] for ent in entity_buffer]
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end

        def o_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            if entity["word"] == '': return "END", text_buffer, entity_buffer, score_buffer, span_start, span_end
            _type = entity["entity"].split('-', 1)[:1][0]
            text_buffer.append(entity["word"])
            score_buffer.append(entity["score"])
            if span_start is None and entity["span"] is not None: span_start = entity["span"].start
            if entity["span"] is not None: span_end = entity["span"].end
            if entity["entity"] != 'O':
                entity_buffer.append(entity["entity"])
                entity_buffer = [_type + ent[1:] for ent in entity_buffer]
            return _type, text_buffer, entity_buffer, score_buffer, span_start, span_end

        def e_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            if entity["word"] == '': return "END", text_buffer, entity_buffer, score_buffer, span_start, span_end
            _type = entity["entity"].split('-', 1)[:1][0]
            text_buffer.append(entity["word"])
            score_buffer.append(entity["score"])
            if span_start is None and entity["span"] is not None: span_start = entity["span"].start
            if entity["span"] is not None: span_end = entity["span"].end
            if _type == 'B': newState = "E"
            elif _type == 'I': newState = "I"
            elif _type == 'O': newState = "E"
            elif _type == 'E': newState = "E" 
            elif _type == 'S': newState = "E"
            else: raise WrongTransitionError
            if entity["entity"] != 'O':
                entity_buffer.append(entity["entity"])
                entity_buffer = [newState + ent[1:] for ent in entity_buffer]
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end

        def s_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            if entity["word"] == '': return "END", text_buffer, entity_buffer, score_buffer, span_start, span_end
            _type = entity["entity"].split('-', 1)[:1][0]
            text_buffer.append(entity["word"])
            score_buffer.append(entity["score"])
            if span_start is None and entity["span"] is not None: span_start = entity["span"].start
            if entity["span"] is not None: span_end = entity["span"].end
            if _type == 'B': newState = "B"
            elif _type == 'I': newState = "I"
            elif _type == 'O': newState = "S"
            elif _type == 'E': newState = "S" 
            elif _type == 'S': newState = "S"
            else: raise WrongTransitionError
            if entity["entity"] != 'O':
                entity_buffer.append(entity["entity"])
                entity_buffer = [newState + ent[1:] for ent in entity_buffer]
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end
        
        def end_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            if entity["word"] == '': raise EmptyTokenError 
            _type = entity["entity"].split('-', 1)[:1][0]
            text_buffer.append(entity["word"])
            score_buffer.append(entity["score"])
            if span_start is None and entity["span"] is not None: span_start = entity["span"].start
            if entity["span"] is not None: span_end = entity["span"].end
            if entity["entity"] != 'O':
                entity_buffer.append(entity["entity"])
                entity_buffer = [_type + ent[1:] for ent in entity_buffer]
            return _type, text_buffer, entity_buffer, score_buffer, span_start, span_end


        self.JoinWords = FiniteStateMachine()
        self.JoinWords.add_state("B", b_handler)
        self.JoinWords.add_state("I", i_handler)
        self.JoinWords.add_state("O", o_handler)
        self.JoinWords.add_state("E", e_handler)
        self.JoinWords.add_state("S", s_handler)
        self.JoinWords.add_state("END", end_handler, end_state=True)
        self.JoinWords.set_start_state("O")

        def most_common(l):
            return max(set(l), key=l.count)

        def average(l):
            return sum(l) / len(l)

        self.JoinWords.add_aggregation_strategy(lambda tb, eb, sc: ("".join(tb), 'O' if not eb else most_common(eb), sum(sc) / len(sc)))


        """
        Allowed states:
         - START
         - BUILDING
         - END
         - ERROR
        Allowed edges:
         - START (B) --> BUILDING
         - START (I) --> ERROR
         - START (O) --> START
         - START (E) --> ERROR
         - START (S) --> END
         - BUILDING (B) --> ERROR
         - BUILDING (I) --> BUILDING
         - BUILDING (O) --> ERROR
         - BUILDING (E) --> END
         - BUILDING (S) --> ERROR
         - END (B) --> BUILDING
         - END (I) --> ERROR 
         - END (O) --> START 
         - END (E) --> ERROR
         - END (S) --> END
         - ERROR (B) --> BUILDING
         - ERROR (I) --> ERROR
         - ERROR (O) --> START
         - ERROR (E) --> ERROR
         - ERROR (S) --> END
        """
        def start_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity"].split('-', 1)[:1][0]
            current_entity = entity["entity"].split('-', 1)[1:]
            if current_entity != []: 
                if span_start is None and entity["span"] is not None: span_start = entity["span"].start
                if entity["span"] is not None: span_end = entity["span"].end
                text_buffer.append(entity["word"])
                entity_buffer.append(current_entity[0])
                score_buffer.append(entity["score"])
            if _type == 'B': newState = "BUILDING"
            elif _type == 'O': newState = "START"
            elif _type == 'S': newState = "END"
            elif _type == 'I': newState = "ERROR" 
            elif _type == 'E': newState = "ERROR"
            else: raise WrongTransitionError
            if newState == "ERROR": InvalidTransitionWarning
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end

        def building_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity"].split('-', 1)[:1][0]
            current_entity = entity["entity"].split('-', 1)[1:]
            if current_entity != []: 
                if span_start is None and entity["span"] is not None: span_start = entity["span"].start
                if entity["span"] is not None: span_end = entity["span"].end
                text_buffer.append(entity["word"])
                entity_buffer.append(current_entity[0])
                score_buffer.append(entity["score"])
            if _type == 'B': newState = "ERROR"
            elif _type == 'O': newState = "ERROR"
            elif _type == 'S': newState = "ERROR"
            elif _type == 'I': newState = "BUILDING" 
            elif _type == 'E': newState = "END"
            else: raise WrongTransitionError
            if newState == "ERROR": InvalidTransitionWarning
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end


        def end_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity"].split('-', 1)[:1][0]
            current_entity = entity["entity"].split('-', 1)[1:]
            if current_entity != []: 
                if span_start is None and entity["span"] is not None: span_start = entity["span"].start
                if entity["span"] is not None: span_end = entity["span"].end
                text_buffer.append(entity["word"])
                entity_buffer.append(current_entity[0])
                score_buffer.append(entity["score"])
            if _type == 'B': newState = "BUILDING"
            elif _type == 'O': newState = "START"
            elif _type == 'S': newState = "END"
            elif _type == 'I': newState = "ERROR" 
            elif _type == 'E': newState = "ERROR"
            else: raise WrongTransitionError
            if newState == "ERROR": InvalidTransitionWarning
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end

        def error_handler(entity, text_buffer, entity_buffer, score_buffer, span_start, span_end):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity"].split('-', 1)[:1][0]
            current_entity = entity["entity"].split('-', 1)[1:]
            if current_entity != []: 
                if span_start is None and entity["span"] is not None: span_start = entity["span"].start
                if entity["span"] is not None: span_end = entity["span"].end
                text_buffer.append(entity["word"])
                entity_buffer.append(current_entity[0])
                score_buffer.append(entity["score"])
            if _type == 'B': newState = "BUILDING"
            elif _type == 'O': newState = "START"
            elif _type == 'S': newState = "END"
            elif _type == 'I': newState = "ERROR" 
            elif _type == 'E': newState = "ERROR"
            else: raise WrongTransitionError
            if newState == "ERROR": InvalidTransitionWarning
            return newState, text_buffer, entity_buffer, score_buffer, span_start, span_end



        # create the Finite State Machine
        self.JoinEntitites = FiniteStateMachine()
        self.JoinEntitites.add_state("START", start_handler)
        self.JoinEntitites.add_state("BUILDING", building_handler)
        self.JoinEntitites.add_state("END", end_handler, end_state=True)
        self.JoinEntitites.add_state("ERROR", error_handler, end_state=True)
        self.JoinEntitites.set_start_state("START")
        self.JoinEntitites.add_aggregation_strategy()


    # def BIOLU2BIOES(self, entity):
    #     if entity[0] == "L": return "E"+entity[1:]
    #     if entity[0] == "U": return "S"+entity[1:]
    #     else: return entity


    def __call__(self, text):
        """ 
        Given a text return the entitites
        """
        batch_encoded = self.tokenizer(text, return_tensors="pt")
        token_ids = batch_encoded["input_ids"]
        spans = [None] + [batch_encoded.token_to_chars(idx) for idx in range(1, len(token_ids[0])-1)] + [None]
        output_logits = self.model(token_ids)["logits"]
        entities = []
        for token, logits, span in zip(token_ids[0], output_logits[0], spans):
            logits = np.array(logits.detach())
            label_idx = np.argmax(logits).item()
            subword = self.tokenizer.decode(token)
            if subword[0] == ' ' or subword in self.punct:
                entities.append({"word": ''})
            entity = {"entity": self.model.config.id2label[label_idx],
                      "word": subword,
                      "score": self.softmax(logits)[label_idx],
                      "span": span}
            entities.append(entity)
#         print("model entitites:")
#         pprint(entities)
        joined_words_entities = self.JoinWords.run(entities)
#         print("joined words:")
#         pprint(joined_words_entities)
        out_entities = self.JoinEntitites.run(joined_words_entities)
        return out_entities



if __name__ == "__main__":
    """
    Example of main that reads std input and identifies entities
    """

    model = AutoModelForTokenClassification.from_pretrained("PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus")
    tokenizer = AutoTokenizer.from_pretrained("PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus")
#     model = AutoModelForTokenClassification.from_pretrained("monilouise/ner_news_portuguese")
#     tokenizer = AutoTokenizer.from_pretrained("monilouise/ner_news_portuguese")

    ner = CustomNerPipeline(model, tokenizer)

    text = input("text:")
    while(text != "exit"):
        out_entities = ner(text)
        pprint(out_entities)
        text = input("text:")
