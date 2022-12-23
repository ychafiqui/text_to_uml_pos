import streamlit as st
import os
import uuid
from functions import *

st.title("Text to UML Diagram Generator with spaCy POS and Dependency Parsing")

text = st.text_area("Write your specification here", height=200)
btn = st.button("Generate")

if btn:
    text = preprocess_text(text)
    classes_attr = get_classes_attributes(text)
    inheritances = get_inheritance(text, classes_attr.keys())
    relations = get_relationships(text, classes_attr.keys(), inheritances)
    graph = graph_from_uml(classes_attr, relations, inheritances)
    image_url = str(uuid.uuid1()) + ".png"
    graph.write_png(image_url)
    st.image(image_url)
    os.remove(image_url)