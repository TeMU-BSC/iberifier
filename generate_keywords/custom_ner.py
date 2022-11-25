from transformers import AutoModelForTokenClassification, AutoTokenizer
import numpy as np
from pprint import pprint


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


class FiniteStateMachineJoinEntities:
    """
    Finite State Machine to join entitites.
    
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
    def __init__(self):
        self.handlers = {}
        self.startState = None
        self.endStates = []
        self.aggregation_startegy = None

    def add_state(self, state, handler, end_state=False):
        self.handlers[state] = handler
        if end_state:
            self.endStates.append(state)

    def set_start_state(self, state):
        if self.startState is not None: raise MultipleStartStatesError
        else: self.startState = state

    def remove_start_state(self):
        self.startState=None

    def add_aggregation_strategy(self, aggregation_startegy=None):
        """
        Function that given a list of text, entities and scores return a single entity.
        by default return the concatenation of all text, the most common entity and the 
        """
        def most_common(l):
            return max(set(l), key=l.count)

        def average(l):
            return sum(l) / len(l)

        if aggregation_startegy is None:
            aggregation_startegy = lambda tb, eb, sc: ("".join(tb), most_common(eb), sum(sc) / len(sc))

        self.aggregation_startegy = aggregation_startegy

    def run(self, entities):
        if self.startState is None: raise StartStateNotSetError
        if len(self.endStates) == 0: raise NoEndStatesAvailableError
        
        handler = self.handlers[self.startState]

        text_buffer = []
        entity_buffer = []
        score_buffer = []

        out_entities = []

        for entity in entities:
            newState, text_buffer, entity_buffer, scores_buffer = handler(entity, text_buffer, entity_buffer, score_buffer)
            if newState in self.endStates:
                text, entity, score = self.aggregation_startegy(text_buffer, entity_buffer, score_buffer)
                out_entities.append({"entity_group": entity, "score": score, "word": text})
                text_buffer = []
                entity_buffer = []
                score_buffer = []
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

        def start_handler(entity, text_buffer, entity_buffer, score_buffer):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity_group"].split('-', 1)[:1][0]
            current_entity = entity["entity_group"].split('-', 1)[1:]
            if current_entity != []: 
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
            return newState, text_buffer, entity_buffer, score_buffer

        def building_handler(entity, text_buffer, entity_buffer, score_buffer):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity_group"].split('-', 1)[:1][0]
            current_entity = entity["entity_group"].split('-', 1)[1:]
            if current_entity != []: 
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
            return newState, text_buffer, entity_buffer, score_buffer


        def end_handler(entity, text_buffer, entity_buffer, score_buffer):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity_group"].split('-', 1)[:1][0]
            current_entity = entity["entity_group"].split('-', 1)[1:]
            if current_entity != []: 
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
            return newState, text_buffer, entity_buffer, score_buffer

        def error_handler(entity, text_buffer, entity_buffer, score_buffer):
            """
            handler that given an entity and buffers returns new state and new buffers 
            """
            _type = entity["entity_group"].split('-', 1)[:1][0]
            current_entity = entity["entity_group"].split('-', 1)[1:]
            if current_entity != []: 
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
            return newState, text_buffer, entity_buffer, score_buffer

        # create the Finite State Machine
        self.JoinEntitites = FiniteStateMachineJoinEntities()
        self.JoinEntitites.add_state("START", start_handler)
        self.JoinEntitites.add_state("BUILDING", building_handler)
        self.JoinEntitites.add_state("END", end_handler, end_state=True)
        self.JoinEntitites.add_state("ERROR", error_handler, end_state=True)
        self.JoinEntitites.set_start_state("START")
        self.JoinEntitites.add_aggregation_strategy()


    def __call__(self, text):
        """ 
        Given a text return the entitites
        """
        token_ids = self.tokenizer(text, return_tensors="pt")["input_ids"]
        output_logits = self.model(token_ids)["logits"]
        entities = []
        for token, logits in zip(token_ids[0], output_logits[0]):
            logits = np.array(logits.detach())
            label_idx = np.argmax(logits).item()
            entity = {"entity_group": self.model.config.id2label[label_idx],
                      "word": self.tokenizer.decode(token),
                      "score": self.softmax(logits)[label_idx]}
            entities.append(entity)
        out_entities = self.JoinEntitites.run(entities)
        return out_entities



if __name__ == "__main__":
    """
    Example of main that reads std input and identifies entities
    """

    model = AutoModelForTokenClassification.from_pretrained("PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus")
    tokenizer = AutoTokenizer.from_pretrained("PlanTL-GOB-ES/roberta-base-bne-capitel-ner-plus")

    ner = CustomNerPipeline(model, tokenizer)

    text = input("text:")
    while(text != "exit"):
        out_entities = ner(text)
        pprint(out_entities)
        text = input("text:")
