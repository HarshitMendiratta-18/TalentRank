import datetime
import re

SERVICE_COMPANIES = {"TCS", "Infosys", "Wipro", "Accenture", "Cognizant", "Capgemini", "Tech Mahindra", "HCL", "Mphasis"}

CORE_SKILLS = {
    "embeddings": ["embedding", "sentence-transformer", "sentence transformer", "word2vec", "bert", "roberta", "minilm", "bge", "e5"],
    "vector_dbs": ["vector", "pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss", "chromadb"],
    "python": ["python"],
    "evaluation": ["ndcg", "mrr", "map", "eval", "a/b test", "benchmark", "offline-to-online", "precision@k"]
}

NICE_TO_HAVE_SKILLS = {
    "llm_finetuning": ["fine-tuning", "finetuning", "lora", "qlora", "peft"],
    "learning_to_rank": ["learning to rank", "learning-to-rank", "xgboost", "lambdamart", "ranker"],
    "distributed_systems": ["distributed system", "large-scale", "inference optimization", "spark", "kafka", "scalability"]
}

def parse_date(d_str):
    if not d_str:
        return None
    try:
        return datetime.datetime.strptime(d_str, "%Y-%m-%d")
    except:
        return None

def score_experience(yoe):
    """
    Optimal years of experience is 6-8 years. Seniority is 5-9.
    """
    if 6.0 <= yoe <= 8.0:
        return 1.0
    elif 5.0 <= yoe < 6.0:
        return 0.8
    elif 8.0 < yoe <= 9.0:
        return 0.8
    elif 4.0 <= yoe < 5.0:
        return 0.5
    elif 9.0 < yoe <= 11.0:
        return 0.5
    elif 3.0 <= yoe < 4.0:
        return 0.3
    elif 11.0 < yoe <= 13.0:
        return 0.3
    else:
        return 0.1

def score_skills(candidate_skills):
    """
    Calculates a match score for core and nice-to-have skills.
    """
    skills_map = {s.get('name', '').lower(): s for s in candidate_skills if s.get('name')}
    
    # 1. Core Skills Match
    core_matches = 0
    total_core = len(CORE_SKILLS)
    core_score = 0.0
    
    for category, keywords in CORE_SKILLS.items():
        matched_skill = None
        for name, info in skills_map.items():
            if any(kw in name for kw in keywords):
                matched_skill = info
                break
        if matched_skill:
            core_matches += 1
            # Weight by proficiency
            prof = matched_skill.get('proficiency', 'intermediate').lower()
            prof_mult = 1.2 if prof == 'expert' else (1.0 if prof == 'advanced' else (0.8 if prof == 'intermediate' else 0.5))
            # Weight by endorsements
            endorsements = matched_skill.get('endorsements', 0)
            endor_mult = min(1.2, 1.0 + (endorsements / 100.0))
            core_score += prof_mult * endor_mult
            
    core_score_normalized = core_score / total_core if total_core > 0 else 0.0
    
    # 2. Nice to Have Skills Match
    nice_matches = 0
    nice_score = 0.0
    total_nice = len(NICE_TO_HAVE_SKILLS)
    
    for category, keywords in NICE_TO_HAVE_SKILLS.items():
        matched_skill = None
        for name, info in skills_map.items():
            if any(kw in name for kw in keywords):
                matched_skill = info
                break
        if matched_skill:
            nice_matches += 1
            prof = matched_skill.get('proficiency', 'intermediate').lower()
            prof_mult = 1.2 if prof == 'expert' else (1.0 if prof == 'advanced' else (0.8 if prof == 'intermediate' else 0.5))
            nice_score += prof_mult
            
    nice_score_normalized = nice_score / total_nice if total_nice > 0 else 0.0
    
    # Combine (Core weights 75%, Nice weights 25%)
    final_skills_score = 0.75 * core_score_normalized + 0.25 * nice_score_normalized
    return min(1.0, final_skills_score)

def score_career_growth(history):
    """
    Looks at career progression: promotions, tenure, and responsibility growth.
    """
    if not history:
        return 0.0
        
    num_jobs = len(history)
    tenures = [job.get('duration_months', 0) for job in history]
    avg_tenure = sum(tenures) / float(num_jobs) if num_jobs > 0 else 0.0
    
    # Promote if average tenure is stable (e.g. 2-4 years per role is healthy)
    # Frequent job hopping (< 18 months per job) is penalized
    tenure_score = 1.0
    if avg_tenure < 18.0:
        tenure_score = 0.5
    elif avg_tenure < 24.0:
        tenure_score = 0.8
        
    # Check for title promotions (e.g. going from Engineer to Senior or Lead)
    promotions = 0
    prev_title = ""
    for job in reversed(history): # Chronological order is usually reverse in profile list, let's look at titles
        title = job.get('title', '').lower()
        if "senior" in title or "lead" in title or "staff" in title or "principal" in title:
            if prev_title and not any(kw in prev_title for kw in ["senior", "lead", "staff", "principal"]):
                promotions += 1
        prev_title = title
        
    promo_score = min(1.0, promotions * 0.5 + 0.5)
    return 0.6 * tenure_score + 0.4 * promo_score

def score_behavioral(signals):
    """
    Scores behavioral activity.
    """
    # 1. Recruiter Response Rate (0 to 1)
    response_rate = signals.get('recruiter_response_rate', 0.0)
    
    # 2. Avg Response Time (lower is better, e.g. < 24 hours is best)
    resp_hours = signals.get('avg_response_time_hours', 168.0) # default to a week
    time_score = max(0.0, 1.0 - (resp_hours / 72.0)) # 0 if > 72 hours
    
    # 3. GitHub Activity (if -1, no GitHub connected)
    git_score = signals.get('github_activity_score', -1)
    git_score_normalized = max(0.0, git_score / 100.0)
    
    # 4. Recent Activity: last login date
    last_act_str = signals.get('last_active_date', '')
    active_score = 0.0
    if last_act_str:
        last_act = parse_date(last_act_str)
        if last_act:
            # Assume assessment is evaluated in late May/June 2026
            days_since = (datetime.datetime(2026, 6, 1) - last_act).days
            if days_since <= 90:
                active_score = 1.0
            elif days_since <= 180:
                active_score = 0.5
            else:
                active_score = 0.1
                
    # 5. Open to Work
    open_to_work = 1.0 if signals.get('open_to_work_flag') else 0.5
    
    behavioral_score = (
        0.25 * response_rate +
        0.20 * time_score +
        0.20 * git_score_normalized +
        0.25 * active_score +
        0.10 * open_to_work
    )
    return min(1.0, behavioral_score)

def score_logistics(profile, signals):
    """
    Pune/Noida location preference and notice period scoring.
    """
    loc = profile.get('location', '').lower()
    country = profile.get('country', '').lower()
    willing_reloc = signals.get('willing_to_relocate', False)
    
    # Noida / Pune preferred. Also NCR, Delhi, Hyderabad, Mumbai, Bangalore.
    loc_score = 0.0
    if any(keyword in loc for keyword in ["noida", "pune", "delhi", "ncr"]):
        loc_score = 1.0
    elif any(keyword in loc for keyword in ["hyderabad", "mumbai", "bangalore", "bengaluru"]):
        loc_score = 0.8 if willing_reloc or any(keyword in loc for keyword in ["pune", "noida"]) else 0.6
    elif country in ["india", "in"]:
        loc_score = 0.6 if willing_reloc else 0.3
    else:
        loc_score = 0.1 # Outside India, no sponsorship
        
    # Notice period (sub-30 is best)
    notice = signals.get('notice_period_days', 90)
    if notice <= 30:
        notice_score = 1.0
    elif notice <= 60:
        notice_score = 0.8
    elif notice <= 90:
        notice_score = 0.5
    else:
        notice_score = 0.2
        
    return 0.6 * loc_score + 0.4 * notice_score

def check_disqualifiers(profile, history):
    """
    Applies penalties for disqualifiers. Returns a multiplier between 0.2 and 1.0.
    """
    multiplier = 1.0
    
    # 1. Outsourcing / Consulting Firms Trap
    # If all candidate's companies are in SERVICE_COMPANIES, apply heavy penalty
    if history:
        all_service = True
        for job in history:
            comp = job.get('company', '')
            if comp not in SERVICE_COMPANIES:
                all_service = False
                break
        if all_service:
            multiplier *= 0.5 # Apply 50% penalty
            
    # 2. Pure Academic Research Trap
    # If title shows PhD/research focus, and description has no shipping words
    is_pure_research = True
    has_jobs = len(history) > 0
    for job in history:
        title = job.get('title', '').lower()
        desc = job.get('description', '').lower()
        # Look for shipping terms
        shipping_terms = ["ship", "deploy", "production", "scale", "infrastructure", "system", "product", "client"]
        if any(term in desc for term in shipping_terms) or not any(kw in title for kw in ["researcher", "phd", "fellow", "postdoc", "academic"]):
            is_pure_research = False
            break
    if has_jobs and is_pure_research:
        multiplier *= 0.6
        
    # 3. Title Chaser Trap
    # switching companies very rapidly (e.g. 3 jobs, average tenure < 15 months)
    if len(history) >= 3:
        tenures = [job.get('duration_months', 0) for job in history]
        avg_tenure = sum(tenures) / len(history)
        if avg_tenure < 15.0:
            multiplier *= 0.7
            
    return multiplier

def calculate_score(candidate, semantic_similarity, weights=None):
    """
    Calculates the final ranking score.
    """
    if candidate.get('is_anomalous', False):
        return 0.0
        
    if weights is None:
        weights = {
            "semantic": 0.30,
            "skills": 0.25,
            "experience": 0.15,
            "growth": 0.10,
            "behavioral": 0.15,
            "logistics": 0.05
        }
        
    profile = candidate.get('profile', {})
    skills = candidate.get('skills', [])
    history = candidate.get('career_history', [])
    signals = candidate.get('redrob_signals', {})
    
    # Individual scores
    semantic_score = semantic_similarity
    skills_score = score_skills(skills)
    exp_score = score_experience(profile.get('years_of_experience', 0))
    growth_score = score_career_growth(history)
    behavioral_score = score_behavioral(signals)
    logistics_score = score_logistics(profile, signals)
    
    # Raw weighted sum
    raw_score = (
        weights["semantic"] * semantic_score +
        weights["skills"] * skills_score +
        weights["experience"] * exp_score +
        weights["growth"] * growth_score +
        weights["behavioral"] * behavioral_score +
        weights["logistics"] * logistics_score
    )
    
    # Apply disqualifier penalties
    disq_multiplier = check_disqualifiers(profile, history)
    final_score = raw_score * disq_multiplier
    
    # Scale final score to a percentage (0.0 to 100.0)
    candidate['sub_scores'] = {
        'semantic': round(semantic_score * 100, 1),
        'skills': round(skills_score * 100, 1),
        'experience': round(exp_score * 100, 1),
        'growth': round(growth_score * 100, 1),
        'behavioral': round(behavioral_score * 100, 1),
        'logistics': round(logistics_score * 100, 1),
        'disq_multiplier': round(disq_multiplier, 2)
    }
    
    return round(final_score * 100.0, 2)
