from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os
import json

# Setup system path to include parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.preprocessing.data_loader import check_anomalies, build_search_document
from src.embeddings.embedder import CandidateEmbedder
from src.ranking.ranker import calculate_score
from src.explanation.explainer import generate_explanation

app = FastAPI(title="Redrob AI Predictive Talent Ranker Engine", version="1.0.0")

# CORS middleware to allow local and web testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to load lazy
CANDIDATES = []
EMBEDDER = None
CANDIDATES_PATH = ""
MODEL_PATH = ""

def discover_paths():
    global CANDIDATES_PATH, MODEL_PATH
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Model path
    MODEL_PATH = os.path.join(root_dir, "AI-Recruiter", "models", "all-MiniLM-L6-v2")
    
    # Candidates path candidates.jsonl (check various locations)
    options = [
        os.path.join(root_dir, "[PUB] India_runs_data_and_ai_challenge", "[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge", "candidates.jsonl"),
        os.path.join(root_dir, "[PUB] India_runs_data_and_ai_challenge", "candidates.jsonl"),
        os.path.join(root_dir, "India_runs_data_and_ai_challenge", "candidates.jsonl"),
        os.path.join(root_dir, "candidates.jsonl"),
        os.path.join(root_dir, "AI-Recruiter", "data", "candidates.jsonl")
    ]
    for opt in options:
        if os.path.exists(opt):
            CANDIDATES_PATH = opt
            break
            
    # Sample candidates path as fallback
    if not CANDIDATES_PATH:
        sample_options = [
            os.path.join(root_dir, "[PUB] India_runs_data_and_ai_challenge", "[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge", "sample_candidates.json"),
            os.path.join(root_dir, "sample_candidates.json")
        ]
        for opt in sample_options:
            if os.path.exists(opt):
                CANDIDATES_PATH = opt
                break

discover_paths()

def init_resources(load_full=False):
    global CANDIDATES, EMBEDDER
    if not EMBEDDER:
        print(f"Loading local SentenceTransformer model from {MODEL_PATH}...")
        EMBEDDER = CandidateEmbedder(MODEL_PATH)
        
    if not CANDIDATES:
        print(f"Loading candidates from {CANDIDATES_PATH}...")
        if CANDIDATES_PATH.endswith('.json'):
            # Load sample json
            with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
                CANDIDATES = json.load(f)
                for c in CANDIDATES:
                    errors = check_anomalies(c)
                    c['anomalies'] = errors
                    c['is_anomalous'] = len(errors) > 0
        else:
            # Load jsonl
            limit = 5000 if not load_full else 100000  # For API sandbox speed, default to first 5000 candidates unless requested
            count = 0
            with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    c = json.loads(line)
                    errors = check_anomalies(c)
                    c['anomalies'] = errors
                    c['is_anomalous'] = len(errors) > 0
                    CANDIDATES.append(c)
                    count += 1
                    if count >= limit:
                        break
        print(f"Successfully loaded {len(CANDIDATES)} candidates.")

class RankRequest(BaseModel):
    jd: str
    weights: dict = {
        "semantic": 0.30,
        "skills": 0.25,
        "experience": 0.15,
        "growth": 0.10,
        "behavioral": 0.15,
        "logistics": 0.05
    }
    load_all: bool = False

@app.on_event("startup")
def startup_event():
    # Discover paths and warm resources
    discover_paths()
    try:
        init_resources(load_full=False) # Load small subset on startup for quick responsiveness
    except Exception as e:
        print(f"Startup warning - could not load resources: {e}")

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "candidates_path": CANDIDATES_PATH,
        "model_path": MODEL_PATH,
        "candidates_loaded": len(CANDIDATES),
        "is_using_sample": CANDIDATES_PATH.endswith('.json')
    }

@app.get("/api/candidates")
def get_candidates():
    init_resources()
    # Return basic metadata of loaded candidates
    return [
        {
            "candidate_id": c["candidate_id"],
            "name": c["profile"]["anonymized_name"],
            "headline": c["profile"]["headline"],
            "years_of_experience": c["profile"]["years_of_experience"],
            "is_anomalous": c["is_anomalous"],
            "anomalies": c["anomalies"]
        }
        for c in CANDIDATES[:100]
    ]

@app.post("/api/rank")
def post_rank(req: RankRequest):
    try:
        init_resources(load_full=req.load_all)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize resources: {str(e)}")
        
    if not req.jd.strip():
        raise HTTPException(status_code=400, detail="Job description query cannot be empty.")
        
    clean_candidates = [c for c in CANDIDATES if not c['is_anomalous']]
    if not clean_candidates:
        return {"ranked_candidates": []}
        
    # Fit TF-IDF on clean candidates
    corpus = [build_search_document(c) for c in clean_candidates]
    EMBEDDER.fit_tfidf(corpus)
    
    # Retrieve top 100
    top_k = min(100, len(clean_candidates))
    top_indices, tfidf_scores = EMBEDDER.search_tfidf(req.jd, top_k=top_k)
    
    retrieved_candidates = [clean_candidates[idx] for idx in top_indices]
    retrieved_docs = [build_search_document(c) for c in retrieved_candidates]
    
    # Rerank using dense embeddings
    doc_embeddings = EMBEDDER.embed_texts(retrieved_docs)
    query_embedding = EMBEDDER.embed_texts([req.jd])[0]
    semantic_scores = EMBEDDER.calculate_similarity(query_embedding, doc_embeddings)
    
    scored_list = []
    for i, c in enumerate(retrieved_candidates):
        sem_sim = float(semantic_scores[i])
        final_score = calculate_score(c, sem_sim, req.weights)
        scored_list.append((final_score, c))
        
    # Sort
    scored_list.sort(key=lambda x: (-x[0], x[1]['candidate_id']))
    
    # Format recommendations
    recommendations = []
    for rank_idx, (score, c) in enumerate(scored_list):
        rank = rank_idx + 1
        reasoning = generate_explanation(c, rank)
        recommendations.append({
            "rank": rank,
            "candidate_id": c["candidate_id"],
            "score": score,
            "sub_scores": c["sub_scores"],
            "reasoning": reasoning,
            "profile": c["profile"],
            "skills": c["skills"],
            "career_history": c["career_history"],
            "redrob_signals": c["redrob_signals"]
        })
        
    return {
        "ranked_candidates": recommendations,
        "total_evaluated": len(CANDIDATES),
        "total_filtered": len(CANDIDATES) - len(clean_candidates)
    }

# Serve static files from web/ directory
web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")
