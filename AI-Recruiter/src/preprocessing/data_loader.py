import json
import os
from datetime import datetime

def parse_date(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str, "%Y-%m-%d")
    except:
        return None

def check_anomalies(candidate):
    """
    Returns a list of error strings representing schema/logical violations (honeypots).
    If empty, candidate is clean.
    """
    errors = []
    
    profile = candidate.get('profile', {})
    signals = candidate.get('redrob_signals', {})
    skills = candidate.get('skills', [])
    history = candidate.get('career_history', [])
    edu = candidate.get('education', [])
    
    # 1. Timeline inversion: last active before signup
    signup = parse_date(signals.get('signup_date'))
    last_active = parse_date(signals.get('last_active_date'))
    if signup and last_active and last_active < signup:
        errors.append(f"last_active_date ({signals.get('last_active_date')}) before signup_date ({signals.get('signup_date')})")
        
    # 2. Salary range inversion: min > max
    sal = signals.get('expected_salary_range_inr_lpa', {})
    s_min = sal.get('min')
    s_max = sal.get('max')
    if s_min is not None and s_max is not None and s_min > s_max:
        errors.append(f"salary range min ({s_min}) greater than max ({s_max})")
        
    # 3. Experience duration mismatch (expert with 0 duration)
    expert_zero_dur = sum(1 for s in skills if s.get('proficiency') in ['expert', 'advanced'] and s.get('duration_months', 0) == 0)
    if expert_zero_dur >= 3:
        errors.append(f"{expert_zero_dur} expert/advanced skills with 0 duration")
        
    # 4. Job date order and overlap anomalies
    for idx, job in enumerate(history):
        start = parse_date(job.get('start_date'))
        end = parse_date(job.get('end_date'))
        if start and end and start > end:
            errors.append(f"job {idx} start date ({job.get('start_date')}) after end date ({job.get('end_date')})")
            
    # 5. Education timeline anomalies
    for idx, school in enumerate(edu):
        start_yr = school.get('start_year')
        end_yr = school.get('end_year')
        if start_yr is not None and end_yr is not None and start_yr > end_yr:
            errors.append(f"edu {idx} start year ({start_yr}) after end year ({end_yr})")
            
    # 6. Education / oldest job discrepancy (job starts 5+ years before college starts)
    oldest_job_year = 9999
    for job in history:
        start = parse_date(job.get('start_date'))
        if start and start.year < oldest_job_year:
            oldest_job_year = start.year
            
    earliest_edu_year = 9999
    for school in edu:
        start_yr = school.get('start_year')
        if start_yr and start_yr < earliest_edu_year:
            earliest_edu_year = start_yr
            
    if oldest_job_year < earliest_edu_year - 5:
        errors.append(f"oldest job start year ({oldest_job_year}) starts more than 5 years before college start ({earliest_edu_year})")
        
    return errors

def build_search_document(candidate):
    """
    Compiles text representation of candidate profile for retrieval.
    """
    profile = candidate.get('profile', {})
    skills = candidate.get('skills', [])
    history = candidate.get('career_history', [])
    
    parts = []
    if profile.get('headline'):
        parts.append(profile['headline'])
    if profile.get('summary'):
        parts.append(profile['summary'])
    if profile.get('current_title'):
        parts.append(profile['current_title'])
        
    skill_names = [s.get('name', '') for s in skills if s.get('name')]
    if skill_names:
        parts.append("Skills: " + ", ".join(skill_names))
        
    for job in history:
        title = job.get('title', '')
        desc = job.get('description', '')
        if title:
            parts.append(title)
        if desc:
            parts.append(desc)
            
    return " ".join(parts)

def load_candidates(candidates_path, clean_only=True):
    """
    Yields parsed candidates. If clean_only=True, skips candidates with any anomalies.
    """
    if not os.path.exists(candidates_path):
        raise FileNotFoundError(f"File not found: {candidates_path}")
        
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                candidate = json.loads(line)
                errors = check_anomalies(candidate)
                candidate['anomalies'] = errors
                candidate['is_anomalous'] = len(errors) > 0
                
                if clean_only and candidate['is_anomalous']:
                    continue
                yield candidate
            except Exception as e:
                print(f"Error reading candidate line: {e}")
                continue
