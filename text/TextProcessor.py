import numpy as np
import pickle
import tensorflow as tf
#from tf.keras.models import load_model
from keras._tf_keras.keras.preprocessing.sequence import pad_sequences
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import models.text_model.model_config as mc

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
        tf.config.set_visible_devices([], 'GPU')
        processed = TextProcessor.preprocess_text(text)
        model = tf.keras.models.load_model('models/text_model/emotion_model_small.h5')
        with open('models/text_model/model_data/tokenizer_small.pkl', 'rb') as f:
            tokenizer = pickle.load(f)
        with open('models/text_model/model_data/label_to_index_small.pkl', 'rb') as f:
            label_to_index = pickle.load(f)
        sequence = tokenizer.texts_to_sequences([processed])
        padded = pad_sequences(sequence, maxlen=mc.MAX_SEQUENCE_LENGTH)
        prediction = model.predict(padded)[0]
        threshold = 0.5
        predicted_labels = [label_to_index[i] for i, prob in enumerate(prediction) if prob >= threshold]
        if not predicted_labels:
            predicted_labels = [label_to_index[np.argmax(prediction)]]

        return predicted_labels



