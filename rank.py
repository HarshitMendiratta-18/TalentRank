import argparse
import sys
import os
import csv
import gzip
import json

# Setup system path to include AI-Recruiter directory
root_dir = os.path.dirname(os.path.abspath(__file__))
ai_recruiter_dir = os.path.join(root_dir, "AI-Recruiter")
sys.path.append(ai_recruiter_dir)

from src.preprocessing.data_loader import check_anomalies, build_search_document
from src.embeddings.embedder import CandidateEmbedder
from src.ranking.ranker import calculate_score
from src.explanation.explainer import generate_explanation

JD_QUERY = (
    "Senior AI Engineer, Founding Team, machine learning, embeddings retrieval, "
    "vector database, Pinecone, FAISS, Milvus, Qdrant, search ranking evaluation frameworks, "
    "NDCG, MRR, MAP, A/B testing, Python development, product engineering shipper"
)

def load_all_candidates(candidates_path):
    """
    Loads candidates, handles gzip if applicable.
    """
    if not os.path.exists(candidates_path):
        raise FileNotFoundError(f"Candidate file not found: {candidates_path}")
        
    is_gz = candidates_path.endswith('.gz')
    open_func = gzip.open if is_gz else open
    mode = 'rt' if is_gz else 'r'
    
    candidates = []
    with open_func(candidates_path, mode, encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            candidate = json.loads(line)
            # Evaluate anomalies
            errors = check_anomalies(candidate)
            candidate['anomalies'] = errors
            candidate['is_anomalous'] = len(errors) > 0
            candidates.append(candidate)
    return candidates

def main():
    parser = argparse.ArgumentParser(description="AI-Powered Predictive Candidate Ranking Engine")
    parser.add_argument("--candidates", required=True, help="Path to candidates dataset (.jsonl or .gz)")
    parser.add_argument("--out", required=True, help="Path to save ranked output CSV")
    args = parser.parse_args()
    
    print(f"Loading candidates from {args.candidates}...")
    candidates = load_all_candidates(args.candidates)
    total_candidates = len(candidates)
    print(f"Loaded {total_candidates} candidates.")
    
    # Filter out anomalous candidates
    clean_candidates = [c for c in candidates if not c['is_anomalous']]
    anomalous_count = total_candidates - len(clean_candidates)
    print(f"Filtered out {anomalous_count} anomalous candidates. Clean candidates remaining: {len(clean_candidates)}")
    
    # Initialize embedder with local offline model
    model_path = os.path.join(ai_recruiter_dir, "models", "all-MiniLM-L6-v2")
    print(f"Initializing embedder using model at {model_path}...")
    embedder = CandidateEmbedder(model_path)
    
    # Step 1: Retrieval (TF-IDF)
    print("Building search index and running TF-IDF retrieval...")
    corpus = [build_search_document(c) for c in clean_candidates]
    embedder.fit_tfidf(corpus)
    
    # Retrieve top 1000 candidates
    top_k = min(1000, len(clean_candidates))
    top_indices, tfidf_scores = embedder.search_tfidf(JD_QUERY, top_k=top_k)
    
    retrieved_candidates = [clean_candidates[idx] for idx in top_indices]
    print(f"Retrieved top {len(retrieved_candidates)} candidates for dense reranking.")
    
    # Step 2: Reranking (SentenceTransformers)
    print("Generating embeddings and computing semantic similarities...")
    retrieved_docs = [build_search_document(c) for c in retrieved_candidates]
    doc_embeddings = embedder.embed_texts(retrieved_docs)
    query_embedding = embedder.embed_texts([JD_QUERY])[0]
    
    semantic_scores = embedder.calculate_similarity(query_embedding, doc_embeddings)
    
    print("Scoring candidates based on hybrid signals...")
    scored_list = []
    for i, candidate in enumerate(retrieved_candidates):
        sem_sim = float(semantic_scores[i])
        final_score = calculate_score(candidate, sem_sim)
        scored_list.append((final_score, candidate))
        
    # Sort candidates by final_score descending, break ties by candidate_id ascending
    scored_list.sort(key=lambda x: (-x[0], x[1]['candidate_id']))
    
    # Select top 100
    top_100 = scored_list[:100]
    print(f"Selected top 100 candidates. Writing to {args.out}...")
    
    # Create target directories for output if needed
    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    # Write CSV
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank_idx, (score, candidate) in enumerate(top_100):
            rank = rank_idx + 1
            cid = candidate['candidate_id']
            # Convert score back to decimal (0.0 to 1.0)
            score_decimal = round(score / 100.0, 4)
            reasoning = generate_explanation(candidate, rank)
            writer.writerow([cid, rank, score_decimal, reasoning])
            
    print("Ranking successfully written!")
    
    # Verify using hackathon's validation script
    print("Verifying final output format...")
    validator_script = os.path.join(
        root_dir,
        "[PUB] India_runs_data_and_ai_challenge",
        "[PUB] India_runs_data_and_ai_challenge",
        "India_runs_data_and_ai_challenge",
        "validate_submission.py"
    )
    if os.path.exists(validator_script):
        print("Running validate_submission.py...")
        import subprocess
        result = subprocess.run(
            ["python", validator_script, args.out],
            capture_output=True,
            text=True
        )
        print("Validation output:")
        print(result.stdout)
        if result.stderr:
            print("Validation errors/warnings:")
            print(result.stderr)
    else:
        print("Validator script not found, skipping verification step.")

if __name__ == "__main__":
    main()
