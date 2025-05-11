#import numpy as np
#import pickle
import tensorflow as tf
#from tf.keras.models import load_model
#from keras._tf_keras.keras.preprocessing.sequence import pad_sequences
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
#import models.text_model.model_config as mc
from transformers import BertTokenizer, BertForSequenceClassification
import torch
from utils import clean_text

dict_emotion = {
    'neutral' : 'neutral',
    'anger' : 'anger',
    'enthusiasm' : 'surprise',
    'fear' : 'fear',
    'sadness' : 'sadness',
    'happiness' : 'joy',
    'disgust' : 'disgust'
}

basic_dict = {0: 'anger', 1: 'disgust', 2: 'fear', 3: 'joy', 4: 'sadness', 5: 'surprise', 6: 'neutral'}

class TextProcessor:
    @staticmethod
    def preprocess_text(text):
        tf.config.set_visible_devices([], 'GPU')
        nltk.download('stopwords')
        nltk.download('wordnet')
        stop_words = set(stopwords.words('russian'))  # + list(punctuation)
        lemmatizer = WordNetLemmatizer()
        words = nltk.word_tokenize(text.lower(), language='russian', preserve_line=True)
        words = [lemmatizer.lemmatize(w) for w in words if w not in stop_words]
        return " ".join(words)

    @staticmethod
    def emo_detection(text):
        cleaned_text = clean_text(text)
        model_dir = "models/text_model_v2/emotion_bert_model"
        # model_dir = "saved_rubert_model"
        model = BertForSequenceClassification.from_pretrained(model_dir)
        tokenizer = BertTokenizer.from_pretrained(model_dir)
        model.eval()
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            predicted_class = torch.argmax(logits, dim=1).item()
        text_class = basic_dict[predicted_class]
        return text_class


