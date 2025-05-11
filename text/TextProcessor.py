import torch
from transformers import BertTokenizer, BertForSequenceClassification
from utils import clean_text

basic_dict = {
    0: 'anger',
    1: 'disgust',
    2: 'fear',
    3: 'joy',
    4: 'sadness',
    5: 'surprise',
    6: 'neutral'
}

class TextProcessor:
    model = None
    tokenizer = None
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    @classmethod
    def load_model(cls):
        if cls.model is None or cls.tokenizer is None:
            model_dir = "models/text_model_v2/emotion_bert_model"
            # CPU или CUDA, ничего больше
            cls.model = BertForSequenceClassification.from_pretrained(model_dir).to(cls.device)
            cls.tokenizer = BertTokenizer.from_pretrained(model_dir)
            cls.model.eval()

    @classmethod
    def emo_detection(cls, text: str):
        cls.load_model()

        cleaned_text = clean_text(text)
        inputs = cls.tokenizer(cleaned_text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        inputs = {k: v.to(cls.device) for k, v in inputs.items()}

        try:
            with torch.no_grad():
                outputs = cls.model(**inputs)
                logits = outputs.logits
                predicted_class = torch.argmax(logits, dim=1).item()
                return basic_dict[predicted_class]
        except Exception as e:
            print(f"[!] Ошибка при распознавании эмоции: {e}")
            return None
