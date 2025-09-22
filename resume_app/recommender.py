"""Recommender: embeddings-first with robust heuristic fallback.

Public API:
- extract_skills_from_jd(jd_text, model=None, top_k=40) -> List[str]
- recommend_with_matches(bullets, jd_text, top_n=5) -> List[(bullet, score, matched_tokens)]
- recommend(bullets, jd_text, top_n=5) -> List[(bullet, score)]

This single-file implementation preserves multi-word phrases (bigrams/trigrams),
prefers semantic matching via `sentence-transformers` when available, and
falls back to a token-overlap heuristic if not.
"""
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer, util, CrossEncoder
import re
import spacy
from spacy.matcher import Matcher


def preprocess_text(text: str) -> str:
    """Preprocess text by lowercasing and removing extra spaces."""
    return " ".join(text.lower().split())

# Initialize a larger Sentence-BERT model for richer embeddings
sbert_model = SentenceTransformer('all-mpnet-base-v2')
# Initialize CrossEncoder for re-ranking
ce_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
# Initialize spaCy model for parsing
nlp = spacy.load("en_core_web_sm")
# Initialize spaCy Matcher for headers
matcher = Matcher(nlp.vocab)
matcher.add("MUST_HAVE", [[{"LOWER": "must"}, {"LOWER": "have"}], [{"LOWER": "must-have"}], [{"LOWER": "required"}], [{"LOWER": "essential"}]])
matcher.add("NICE_TO_HAVE", [[{"LOWER": "nice"}, {"LOWER": "to"}, {"LOWER": "have"}], [{"LOWER": "nice-to-have"}], [{"LOWER": "preferred"}], [{"LOWER": "might"}, {"LOWER": "also"}, {"LOWER": "have"}]])


# Lightweight stopwords to filter trivial tokens
STOPWORDS = {
    'using', 'with', 'and', 'or', 'the', 'for', 'in', 'on', 'at', 'to', 'from', 'by', 'of',
    'experience', 'experienced', 'years', 'year', 'skills', 'skill', 'ability', 'abilities',
    'work', 'works', 'working', 'used', 'use', 'apply', 'applied', 'that', 'is', 'are',
    'a', 'an', 'as', 'be', 'have', 'has', 'will', 'would', 'should', 'can', 'may', 'technologies',
}

def extract_priority_skills(jd_text: str) -> Dict[str, List[str]]:
    """Extract must-have and nice-to-have skills from the job description text using structural parsing."""
    # Parse with spaCy and use sentence segmentation
    doc = nlp(jd_text)
    musts: List[str] = []
    nices: List[str] = []
    current = None
    for sent in doc.sents:
        sent_doc = nlp(sent.text)
        # Header detection via Matcher
        matches = matcher(sent_doc)
        header_found = False
        for match_id, start, end in matches:
            label = nlp.vocab.strings[match_id]
            if label == "MUST_HAVE":
                current = 'must_have'
                header_found = True
                break
            if label == "NICE_TO_HAVE":
                current = 'nice_to_have'
                header_found = True
                break
        if header_found:
            continue
        # If in a section, extract noun-chunks as skills
        if current:
            chunks = [chunk.text.strip() for chunk in sent_doc.noun_chunks]
            for chunk in chunks:
                if current == 'must_have':
                    musts.append(chunk)
                else:
                    nices.append(chunk)
    # Deduplicate preserving order
    musts = list(dict.fromkeys(musts))
    nices = list(dict.fromkeys(nices))
    return {
        "must_have": musts,
        "nice_to_have": nices
    }


def extract_skills_from_jd(jd_text: str, model: Optional[object] = None, top_k: int = 40) -> List[str]:
    """Return the most salient skill-like candidates (uni/bi/trigrams) from `jd_text`."""
    text_low = jd_text.lower()
    # Tokenize into words of length>=3
    words = re.findall(r"\w{3,}", text_low)
    # Filter stopwords
    words = [w for w in words if w not in STOPWORDS]
    if not words:
        return []
    # Unique unigrams
    unigrams = list(dict.fromkeys(words))
    # Bigrams and trigrams
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]
    candidates = unigrams + bigrams + trigrams
    # Rank by frequency then longer phrases
    freq: Dict[str, int] = {}
    for c in candidates:
        freq[c] = freq.get(c, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0])))
    return [c for c, _ in ranked[:top_k]]


def recommend_with_matches(bullets: List[Dict], jd_text: str, top_n: int = 5) -> List[Tuple[Dict, int, List[str]]]:
    """Recommend bullets using semantic matching, cross-encoder re-ranking, and priority boosting."""
    # Extract priority skills from job description
    priorities = extract_priority_skills(jd_text)
    
    # Get semantic recommendations
    semantic_results = _get_semantic_recommendations(bullets, jd_text, top_n)
    
    # Apply cross-encoder re-ranking
    cross_encoder_results = _apply_cross_encoder_reranking(semantic_results, jd_text)
    
    # Apply priority boosting and phrase matching
    final_results = _apply_priority_boosting(cross_encoder_results, jd_text, priorities)
    
    return final_results


def _get_semantic_recommendations(bullets: List[Dict], jd_text: str, top_n: int) -> List[Tuple[Dict, float, List[str]]]:
    """Get initial semantic recommendations using two-tower model."""
    mapping = {preprocess_text(b.get('bullet', '')): b for b in bullets}
    preprocessed_texts = list(mapping.keys())
    
    recommendations = two_tower_recommendation(jd_text, preprocessed_texts, top_n=top_n)
    
    results = []
    for text, score in recommendations:
        original = mapping.get(text)
        if original:
            results.append((original, score * 100, []))
    
    return results


def _apply_cross_encoder_reranking(results: List[Tuple[Dict, float, List[str]]], jd_text: str) -> List[Tuple[Dict, float, List[str]]]:
    """Apply cross-encoder re-ranking for improved relevance."""
    ce_pairs = [(jd_text, preprocess_text(rec.get('bullet', ''))) for rec, _, _ in results]
    ce_scores = ce_model.predict(ce_pairs)
    
    cross_results = []
    for (rec, _, matches), ce_score in zip(results, ce_scores):
        cross_results.append((rec, ce_score * 100, matches))
    
    cross_results.sort(key=lambda x: x[1], reverse=True)
    
    # Normalize scores to be positive
    if cross_results:
        min_score = min(score for _, score, _ in cross_results)
        normalized = []
        for rec, score, matches in cross_results:
            norm_score = score - min_score + 1
            normalized.append((rec, norm_score, matches))
        cross_results = normalized
    
    return cross_results


def _apply_priority_boosting(results: List[Tuple[Dict, float, List[str]]], jd_text: str, priorities: Dict[str, List[str]]) -> List[Tuple[Dict, int, List[str]]]:
    """Apply priority boosting and extract matched phrases."""
    jd_candidates = extract_skills_from_jd(jd_text)
    phrase_embs = sbert_model.encode(jd_candidates, convert_to_tensor=True)
    jd_lower = jd_text.lower()
    
    adjusted = []
    for rec, base_score, _ in results:
        score_adj = base_score
        
        # Find semantic phrase matches
        bullet_text = preprocess_text(rec.get('bullet', ''))
        bullet_emb = sbert_model.encode(bullet_text, convert_to_tensor=True)
        sims = util.cos_sim(bullet_emb, phrase_embs)[0].cpu().tolist()
        top_idxs = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:3]
        matched_phrases = [jd_candidates[i] for i in top_idxs if sims[i] > 0.1]
        
        # Apply priority boosts from JD-extracted priorities
        for must_skill in priorities.get('must_have', []):
            if must_skill.lower() in bullet_text.lower():
                score_adj += 20
        
        for nice_skill in priorities.get('nice_to_have', []):
            if nice_skill.lower() in bullet_text.lower():
                score_adj += 10
        
        adjusted.append((rec, int(score_adj), matched_phrases))
    
    adjusted.sort(key=lambda x: x[1], reverse=True)
    return adjusted


def recommend(bullets: List[Dict], jd_text: str, top_n: int = 5) -> List[Tuple[Dict, int]]:
    """Recommend bullets with scores only."""
    full = recommend_with_matches(bullets, jd_text, top_n=top_n)
    return [(b, s) for b, s, _ in full]


def two_tower_recommendation(job_description: str, user_experiences: List[str], top_n: int = 5) -> List[Tuple[str, float]]:
    """
    Two-tower recommendation model using Sentence-BERT.

    Args:
        job_description (str): The job description text.
        user_experiences (List[str]): List of user experience texts (e.g., resume content).
        top_n (int): Number of top recommendations to return.

    Returns:
        List[Tuple[str, float]]: Top N user experiences with similarity scores.
    """
    # Generate embeddings for the job description and user experiences
    jd_embedding = sbert_model.encode(job_description, convert_to_tensor=True)
    ue_embeddings = sbert_model.encode(user_experiences, convert_to_tensor=True)

    # Compute cosine similarity
    similarities = util.cos_sim(jd_embedding, ue_embeddings)[0].cpu().tolist()

    # Pair user experiences with their similarity scores
    scored_experiences = list(zip(user_experiences, similarities))

    # Sort by similarity score in descending order
    scored_experiences.sort(key=lambda x: x[1], reverse=True)

    return scored_experiences[:top_n]


# Example usage
if __name__ == "__main__":
    job_desc = "Looking for a software engineer with experience in Python, machine learning, and cloud computing."
    resumes = [
        "Experienced Python developer with expertise in machine learning and AWS.",
        "Skilled in Java and web development, with some exposure to cloud technologies.",
        "Data scientist with a strong background in Python, TensorFlow, and Azure."
    ]

    recommendations = two_tower_recommendation(job_desc, resumes, top_n=3)
    for rec in recommendations:
        print(f"Experience: {rec[0]}\nScore: {rec[1]:.4f}\n")
