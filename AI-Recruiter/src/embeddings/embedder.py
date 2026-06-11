from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

class CandidateEmbedder:
    def __init__(self, local_model_path):
        """
        Loads the SentenceTransformer model from local weights.
        """
        self.model = SentenceTransformer(local_model_path)
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        
    def embed_texts(self, texts):
        """
        Generates dense vector representations of texts.
        """
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        
    def calculate_similarity(self, query_embedding, doc_embeddings):
        """
        Calculates cosine similarities between a query embedding and multiple document embeddings.
        """
        # Norms
        q_norm = np.linalg.norm(query_embedding)
        doc_norms = np.linalg.norm(doc_embeddings, axis=1)
        
        # Prevent division by zero
        doc_norms[doc_norms == 0] = 1.0
        if q_norm == 0:
            return np.zeros(len(doc_embeddings))
            
        dot_products = np.dot(doc_embeddings, query_embedding)
        similarities = dot_products / (doc_norms * q_norm)
        return similarities

    def fit_tfidf(self, corpus):
        """
        Fits TF-IDF vectorizer on candidate profiles corpus.
        """
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(corpus)
        
    def search_tfidf(self, query, top_k=1000):
        """
        Performs fast retrieval using TF-IDF and returns the indices and similarity scores.
        """
        query_vector = self.tfidf_vectorizer.transform([query])
        scores = (self.tfidf_matrix * query_vector.T).toarray().flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]
        return top_indices, scores[top_indices]
