"""Deterministic tools callable by the ResolveAI agents."""
import re
from datetime import datetime, timezone
from app.domain import now, dt, sla, retrieve, rank_teams, tokens, STOP

def search_knowledge_tool(ticket: dict, history: list[dict], extra_terms: list[str] = None, limit: int = 5, min_score: float = 0.12) -> list[dict]:
    """Retrieve historical resolved tickets with keyword overlap and optional term expansion."""
    query = tokens(ticket['title'] + ' ' + ticket['description'])
    if extra_terms:
        expanded_query = query | set(t.lower() for t in extra_terms if len(t) >= 3) - STOP
    else:
        expanded_query = query

    matches = []
    for row in history:
        if row.get('id') == ticket.get('id') or row.get('status') != 'resolved' or not row.get('solution'):
            continue
        overlap = expanded_query & tokens(row.get('title', '') + ' ' + row.get('description', '') + ' ' + row.get('solution', ''))
        if not overlap:
            continue
        score = len(overlap) / max(len(expanded_query), 1)
        if score < min_score:
            continue
        matches.append({
            **row,
            'retrieval_score': round(score, 3),
            'matched_terms': sorted(overlap)
        })
    return sorted(matches, key=lambda x: (-x['retrieval_score'], x.get('id', '')))[:limit]

def rank_resolver_teams_tool(category: str, expertise: list[str], teams: list[dict], tickets: list[dict]) -> list[dict]:
    """Deterministic resolver team scoring: Category (60) + Skills (20) + Spare Capacity (20)."""
    return rank_teams(category, expertise, teams, tickets)

def calculate_sla_tool(ticket: dict, clock=None) -> dict:
    """Deterministic SLA tracking metrics calculation."""
    return sla(ticket, clock)

def validate_citations_tool(steps: list[dict], sources: list[dict]) -> tuple[bool, str]:
    """Strictly validate that resolution steps cite real provided sources and respect basis labels."""
    allowed = {s['id'] for s in sources}
    for i, s in enumerate(steps):
        s_ids = s.get('source_ids', [])
        basis = s.get('basis', 'hypothesis')
        
        # Check unknown source IDs
        unknown = set(s_ids) - allowed
        if unknown:
            return False, f"Step {i+1} cites unknown source IDs: {sorted(unknown)}"
        
        # Historical basis must cite at least one valid source
        if basis == 'historical' and not s_ids:
            return False, f"Step {i+1} marked as 'historical' but has no source citations."
        
        # Hypothesis basis must not cite historical sources
        if basis == 'hypothesis' and s_ids:
            return False, f"Step {i+1} marked as 'hypothesis' cannot cite sources ({s_ids}). Set basis='historical' or remove source_ids."
            
    return True, ""
