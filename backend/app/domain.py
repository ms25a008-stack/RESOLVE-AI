"""Explainable, deterministic rules. These functions are not AI."""
import re
from datetime import datetime, timezone

SLA_HOURS = {'P1': 4, 'P2': 8, 'P3': 24, 'P4': 72}
CATEGORIES = ['Network', 'Identity', 'Applications', 'Hardware', 'Cloud', 'Security']

def now():
    return datetime.now(timezone.utc)

def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def sla(ticket, clock=None):
    clock = clock or now()
    end = dt(ticket['resolved_at']) if ticket.get('resolved_at') else clock
    remaining = (dt(ticket['sla_due_at']) - end).total_seconds() / 60
    budget = (dt(ticket['sla_due_at']) - dt(ticket['created_at'])).total_seconds() / 60
    elapsed = max(0, min(100, 100 * (1 - remaining / max(budget, 1))))
    if ticket['status'] == 'resolved':
        state, reason = ('met', 'Resolved within SLA') if remaining >= 0 else ('missed', 'Resolved after SLA deadline')
    elif remaining <= 0:
        state, reason = 'breached', 'Resolution deadline has passed'
    elif remaining <= 60 or elapsed >= 75:
        state, reason = 'at_risk', 'At most 60 minutes remain or at least 75% of the SLA budget is consumed'
    else:
        state, reason = 'on_track', 'More than 60 minutes remain and less than 75% of the SLA budget is consumed'
    return dict(state=state, reason=reason, minutes_remaining=round(remaining), elapsed_percent=round(elapsed))

STOP = {'the','and','for','with','from','this','that','after','have','has','are','was','not','user','users','cannot','issue','office','reported'}
def tokens(text):
    return set(re.findall(r'[a-z0-9]{3,}', text.lower())) - STOP

def retrieve(ticket, history, limit=5):
    query = tokens(ticket['title'] + ' ' + ticket['description'])
    matches = []
    for row in history:
        if row['id'] == ticket['id'] or row['status'] != 'resolved' or not row.get('solution'): continue
        overlap = query & tokens(row['title'] + ' ' + row['description'] + ' ' + row['solution'])
        if not overlap: continue
        score = len(overlap) / max(len(query), 1)
        if score < .12: continue
        matches.append({**row, 'retrieval_score': round(score, 3), 'matched_terms': sorted(overlap)})
    return sorted(matches, key=lambda x: (-x['retrieval_score'], x['id']))[:limit]

def rank_teams(category, expertise, teams, tickets):
    results = []
    for team in teams:
        active = sum(t['status'] != 'resolved' and t.get('assigned_team_id') == team['id'] for t in tickets)
        capacity = team['capacity']
        match = category in team['categories']
        skill_overlap = tokens(' '.join(expertise)) & tokens(' '.join(team['skills']))
        score = (60 if match else 0) + min(20, len(skill_overlap) * 10) + max(0, 20 * (1-active/capacity))
        results.append({**team, 'active_tickets': active, 'score': round(score, 1), 'reason': f"{'Category match' if match else 'No category match'}; {len(skill_overlap)} matching skill terms; {active}/{capacity} active ticket capacity. Score = category (60) + expertise (up to 20) + spare capacity (up to 20)."})
    return sorted(results, key=lambda x: (-x['score'], x['id']))
