import spacy
from pyUML import Graph, UMLClass

spacy.cli.download("en_core_web_sm")
nlp = spacy.load("en_core_web_sm")

deps_attr = ["pobj", "dobj", "conj"]
deps_class = ["nsubj", "nsubjpass", "conj", "attr"]

def preprocess_text(text):
    if not text.endswith("."): text += "."
    doc = nlp(text)
    for token in doc:
        # check for compound words
        if token.dep_ == "compound":
            text = text.replace(token.text + " " + token.head.text, token.text + "_" + token.head.text)
        # check for gerund followed by a noun
        if token.pos_ == "VERB" and token.tag_ == "VBG" and token.head.pos_ == "NOUN":
            text = text.replace(token.text + " " + token.head.text, token.text + "_" + token.head.text)
        # check if a noun is followed by a gerund
        if token.pos_ == "NOUN" and token.head.pos_ == "VERB" and token.head.tag_ == "VBG":
            text = text.replace(token.head.text + " " + token.text, token.head.text + "_" + token.text)
        # check for adjectives followed by a noun
        if token.pos_ == "ADJ" and token.head.pos_ == "NOUN":
            text = text.replace(token.text + " " + token.head.text, token.text + "_" + token.head.text)
    return text

def discard_attr_from_classes(classes_attr, attribute):
    for cls in classes_attr.keys():
        if attribute in classes_attr[cls]:
            classes_attr[cls].discard(attribute)
    return classes_attr

def add_to_classes(classes_attr, sent, token):
    if token not in classes_attr.keys():
        classes_attr[token] = set()
    else:
        classes_attr[token].add(token)
    classes_attr = discard_attr_from_classes(classes_attr, token)
    return classes_attr

def add_to_attributes(classes_attr, sent, token):
    if token not in classes_attr.keys():
        try:
            classes_attr[list(sent.root.children)[0].lemma_].add(token)
        except KeyError:
            pass
    return classes_attr

def get_classes_attributes(text):
    classes_attr = {}
    doc = nlp(text)
    for sent in doc.sents:
        for token in sent:
            if token.pos_ == "NOUN":
                # attribute
                if token.dep_ in deps_attr:
                    classes_attr = add_to_attributes(classes_attr, sent, token.lemma_)
                # class
                elif token.dep_ in deps_class:
                    classes_attr = add_to_classes(classes_attr, sent, token.lemma_)
    return classes_attr

def get_all_children_of_root(root, level):
    children = []
    l = 0 
    for child in root.children:
        if l == level: break
        children.append(child)
        children += get_all_children_of_root(child, level=level)
        l += 1
    return children
    
def get_relationships(text, classes, inheritances):
    relationships = set()
    doc = nlp(text)
    for sent in doc.sents:
        children = list(sent.root.children)
        children = get_all_children_of_root(sent.root, level=3)
        for i in range(len(children)):
            for j in range(i+1, len(children)):
                if children[i].lemma_ in classes and children[j].lemma_ in classes and children[i].lemma_ != children[j].lemma_:
                    adp = [tok for tok in sent.root.children if tok.pos_ == "ADP"]
                    adp = adp[0].text if adp else None
                    if adp:
                        rel = (children[i].lemma_, sent.root.text + " " + adp, children[j].lemma_)
                        rel_inv = (children[j].lemma_, sent.root.text + " " + adp, children[i].lemma_)
                    else:
                        rel = (children[i].lemma_, sent.root.text, children[j].lemma_)
                        rel_inv = (children[j].lemma_, sent.root.text, children[i].lemma_)
                    # skip if the opposite relationship is already added
                    if rel_inv not in relationships:
                        # skip if the relationship is an inheritance
                        if (rel[0], rel[2]) not in inheritances and (rel[2], rel[0]) not in inheritances:
                            relationships.add(rel)
    return relationships

def get_children_recursively(root, children):
    for child in root.children:
        if child.dep_ == "conj":
            children.append(child.lemma_)
            children = get_children_recursively(child, children)
    return children

def get_inheritance(text, classes):
    inheritances = set()
    doc = nlp(text)
    for sent in doc.sents:
        children = list(sent.root.children)
        if sent.root.lemma_ == "be":
            if "can" in [child.lemma_ for child in children]:
                parent = ""
                enfants = []
                for child in children:
                    if child.dep_ == "nsubj":
                        parent = child.lemma_
                    elif child.dep_ == "attr":
                        enfants.append(child.lemma_)
                        get_children_recursively(child, enfants)
                for enfant in enfants:
                    inheritances.add((enfant, parent))
            else:
                for i in range(len(children)):
                    for j in range(i+1, len(children)):
                        if children[i].lemma_ in classes and children[j].lemma_ in classes:
                            inheritances.add((children[i].lemma_, children[j].lemma_))
    return inheritances

def get_attribute_type(attribute):
    ints = ["no", "number", "num", "nb", "age"]
    floats = ["price", "salary"]
    for i in ints:
        if i in attribute:
            return "int"
    for f in floats:
        if f in attribute:
            return "float"
    if "date" in attribute:
      return "date"
    else:
      return "string"

def graph_from_uml(uml, relations, inheritances):
    graph = Graph('pyUML')

    for rel in relations:
        class1 = UMLClass(rel[0])
        graph.add_class(class1)
        class2 = UMLClass(rel[2])
        graph.add_class(class1)
        graph.add_association(class1, class2, label=rel[1])

    for inh in inheritances:
        class1 = UMLClass(inh[0])
        graph.add_class(class1)
        class2 = UMLClass(inh[1])
        graph.add_class(class1)
        graph.add_implementation(class1, class2)

    for cls in uml.keys():
        graph.add_class(UMLClass(cls, attributes={attr: get_attribute_type(attr) for attr in uml[cls]}))
    return graph