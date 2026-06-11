import random

def generate_explanation(candidate, rank):
    """
    Generates a 1-2 sentence justification for why the candidate is at their rank.
    Incorporates specific facts, connects to the JD, notes honest concerns, and ensures variation.
    """
    profile = candidate.get('profile', {})
    skills = candidate.get('skills', [])
    history = candidate.get('career_history', [])
    signals = candidate.get('redrob_signals', {})
    sub_scores = candidate.get('sub_scores', {})
    
    name = profile.get('anonymized_name', 'Candidate')
    yoe = profile.get('years_of_experience', 0)
    title = profile.get('current_title', 'Engineer')
    
    # 1. Identify specific skills the candidate actually has
    skill_names = [s.get('name', '') for s in skills if s.get('name')]
    skill_set = {s.lower() for s in skill_names}
    
    # Check for JD-relevant skills they actually have
    ml_skills = []
    if any(kw in s for s in skill_set for kw in ["pytorch", "tensorflow", "keras", "deep learning"]):
        ml_skills.append("deep learning")
    if any(kw in s for s in skill_set for kw in ["sentence", "transformer", "bert", "embeddings"]):
        ml_skills.append("embeddings")
    if any(kw in s for s in skill_set for kw in ["pinecone", "weaviate", "qdrant", "milvus", "faiss", "vector"]):
        ml_skills.append("vector databases")
    if any(kw in s for s in skill_set for kw in ["eval", "ndcg", "mrr", "map", "a/b test"]):
        ml_skills.append("evaluation frameworks")
    if "python" in skill_set:
        ml_skills.append("Python")
        
    # Check for nice-to-have
    nice_skills = []
    if any(kw in s for s in skill_set for kw in ["fine-tuning", "finetuning", "lora", "qlora", "peft"]):
        nice_skills.append("LLM fine-tuning")
    if any(kw in s for s in skill_set for kw in ["xgboost", "lambdamart", "learning to rank"]):
        nice_skills.append("learning-to-rank")
        
    # 2. Check past employers and types
    employers = [job.get('company', '') for job in history if job.get('company')]
    has_services = any(comp in ["Wipro", "TCS", "Infosys", "Capgemini", "Accenture", "Cognizant", "Tech Mahindra", "HCL", "Mphasis"] for comp in employers)
    has_product = any(comp not in ["Wipro", "TCS", "Infosys", "Capgemini", "Accenture", "Cognizant", "Tech Mahindra", "HCL", "Mphasis"] for comp in employers)
    
    # 3. Identify concerns
    concerns = []
    notice = signals.get('notice_period_days', 0)
    if notice > 60:
        concerns.append(f"a longer notice period of {notice} days")
    loc = profile.get('location', '').lower()
    willing_reloc = signals.get('willing_to_relocate', False)
    if not any(kw in loc for kw in ["noida", "pune", "delhi", "ncr"]):
        if willing_reloc:
            concerns.append("relocation requirement to Pune/Noida")
        else:
            concerns.append("remote location without relocation commitment")
            
    # Compile the explanation based on rank
    reasons = []
    
    # High ranks: 1 - 20 (Strong recommendation)
    if rank <= 20:
        intro = f"Strong Senior AI Engineer match with {yoe} years of experience as a {title}."
        
        strength_parts = []
        if ml_skills:
            strength_parts.append(f"hands-on experience with {', '.join(ml_skills[:3])}")
        if has_product:
            strength_parts.append("proven track record of shipping production ML systems at product companies")
            
        details = " Details include " + " and ".join(strength_parts) if strength_parts else ""
        
        closing = ""
        if concerns:
            closing = f" Minor concern includes {concerns[0]}."
        elif signals.get('github_activity_score', 0) > 60:
            closing = f" Outstanding GitHub activity score of {signals['github_activity_score']} demonstrates strong open-source contribution."
            
        reasons.append(f"{intro}{details}.{closing}")
        reasons.append(f"Ranked #{rank} due to excellent {yoe}-year history matching our 'shipper' archetype. Features production experience with {', '.join(ml_skills[:2])}. Note: candidate has a {notice}-day notice period.")
        
    # Mid ranks: 21 - 80 (Good fit, but some gaps)
    elif rank <= 80:
        intro = f"Solid {yoe}-year candidate currently working as a {title}."
        
        fit = ""
        if ml_skills:
            fit = f" Matches core requirements in {', '.join(ml_skills[:2])}."
            
        gap = ""
        if concerns:
            gap = f" Main drawback is {concerns[0]}."
        elif has_services:
            gap = " Career history is primarily in services/outsourcing, which conflicts with our founding team product needs."
            
        reasons.append(f"{intro}{fit}{gap}")
        reasons.append(f"Intermediate match with {yoe} years experience. Shows competence in {', '.join(ml_skills[:2]) if ml_skills else 'adjacent fields'}, but lacks explicit {nice_skills[0] if nice_skills else 'vector search'} experience and has {notice}-day notice.")
        
    # Low ranks: 81 - 100 (Adjacent or below cutoff, included as fillers)
    else:
        intro = f"Ranked at #{rank} primarily due to adjacent skills only."
        details = f" Candidate has {yoe} years experience as a {title}."
        
        gap = ""
        if has_services and not has_product:
            gap = " Background is strictly service-firm based with no startup or product engineering exposure."
        elif not ml_skills:
            gap = " Lacks core ML, embedding, or vector search skills outlined in the JD."
            
        reasons.append(f"{intro}{details}{gap}")
        reasons.append(f"Filler candidate at rank {rank}. Minimal matching ML keywords (has {', '.join(ml_skills[:1]) if ml_skills else 'only software skills'}), and requires {concerns[0] if concerns else 'relocation'}.")

    return random.choice(reasons)
