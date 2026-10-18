import React, { useState } from 'react';
import { 
  Sparkles, ShieldCheck, Clock, Users, BookOpen, AlertTriangle, 
  CheckCircle2, ArrowRight, GitBranch, Cpu, ListChecks, HelpCircle, 
  Terminal, ExternalLink, ChevronDown, ChevronRight 
} from 'lucide-react';

export function MultiAgentView({ recommendation: r, ticket: t, teams, engineer, busy, act, comment, setComment, date, Badge }) {
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'agents' | 'traces'
  const ma = r.multi_agent || {};
  const triage = ma.triage || {};
  const knowledge = ma.knowledge || {};
  const resolver = ma.resolver || {};
  const resolution = ma.resolution || r.analysis || {};
  const sla = ma.sla || {};
  const collab = ma.collaboration || {};
  const traces = ma.traces || [];
  const routing = ma.routing_decisions || [];

  return (
    <div className="multi-agent-container">
      {/* 1. Multi-Agent Pipeline Status Bar */}
      <div className="agent-pipeline-card">
        <div className="pipeline-header">
          <div className="inline">
            <Sparkles size={17} className="pulse-icon" />
            <span className="eyebrow">LANGGRAPH MULTI-AGENT ORCHESTRATION</span>
          </div>
          <span className="tag">6 AGENTS COLLABORATING</span>
        </div>

        <div className="pipeline-steps">
          <div className="agent-step active">
            <span className="step-num">01</span>
            <div className="step-info">
              <strong>Triage</strong>
              <small>{triage.urgency || 'Normal'} urgency</small>
            </div>
          </div>
          <div className="pipeline-arrow"><ArrowRight size={14}/></div>

          <div className="agent-step active">
            <span className="step-num">02</span>
            <div className="step-info">
              <strong>Knowledge</strong>
              <small>{(knowledge.sources_found || []).length} sources</small>
            </div>
          </div>
          <div className="pipeline-arrow"><ArrowRight size={14}/></div>

          <div className="agent-step active">
            <span className="step-num">03</span>
            <div className="step-info">
              <strong>Resolver</strong>
              <small>{resolver.recommended_team?.name || r.resolver?.name || 'Matched'}</small>
            </div>
          </div>
          <div className="pipeline-arrow"><ArrowRight size={14}/></div>

          <div className="agent-step active">
            <span className="step-num">04</span>
            <div className="step-info">
              <strong>SLA Guard</strong>
              <small>{sla.state || 'Calculated'}</small>
            </div>
          </div>
          <div className="pipeline-arrow"><ArrowRight size={14}/></div>

          <div className="agent-step active">
            <span className="step-num">05</span>
            <div className="step-info">
              <strong>Resolution</strong>
              <small>{(resolution.steps || []).length} steps</small>
            </div>
          </div>
          <div className="pipeline-arrow"><ArrowRight size={14}/></div>

          <div className="agent-step active">
            <span className="step-num">06</span>
            <div className="step-info">
              <strong>Collaboration</strong>
              <small>Review packet</small>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Agent Tab Navigation */}
      <div className="agent-tabs">
        <button 
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <ListChecks size={15} /> Resolution Plan & Review
        </button>
        <button 
          className={`tab-btn ${activeTab === 'agents' ? 'active' : ''}`}
          onClick={() => setActiveTab('agents')}
        >
          <Users size={15} /> Specialized Agent Outputs (6)
        </button>
        <button 
          className={`tab-btn ${activeTab === 'traces' ? 'active' : ''}`}
          onClick={() => setActiveTab('traces')}
        >
          <Terminal size={15} /> Execution Traces & Tools ({traces.length})
        </button>
      </div>

      {/* 3. Tab Contents */}
      {activeTab === 'overview' && (
        <div className="tab-pane">
          {/* Executive Summary from Collaboration Agent */}
          {collab.executive_summary && (
            <div className="agent-card summary-card">
              <div className="agent-card-header">
                <strong>Collaboration Agent · Executive Summary</strong>
                <span className="badge approved">Grounded Synthesis</span>
              </div>
              <p>{collab.executive_summary}</p>
            </div>
          )}

          {/* SLA Escalation Warning Banner if needed */}
          {sla.escalation_needed && (
            <div className="sla-alert-banner">
              <AlertTriangle size={18} />
              <div>
                <strong>SLA Agent Escalation Alert</strong>
                <p>{sla.advisory}</p>
              </div>
            </div>
          )}

          {/* Tentative Assessment */}
          <h3>Tentative assessment</h3>
          <p>{resolution.summary || r.analysis?.summary}</p>
          <div className="inline">
            <Badge value={resolution.category || r.analysis?.category}/>
            <span className="muted">Suggested priority: {resolution.suggested_priority || r.analysis?.suggested_priority} (advisory)</span>
          </div>

          {/* Hypotheses */}
          <h3>Hypotheses to investigate</h3>
          <ul>
            {(resolution.hypotheses || r.analysis?.hypotheses || []).map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>

          {/* Recommended Steps with Evidence Grounding */}
          <h3>Recommended investigation steps</h3>
          <ol className="steps">
            {(resolution.steps || r.analysis?.steps || []).map((s, i) => (
              <li key={i}>
                <p>{s.instruction}</p>
                <small className="evidence">
                  {s.basis === 'hypothesis' 
                    ? 'UNVERIFIED HYPOTHESIS · No historical evidence' 
                    : `HISTORICAL CONTEXT · ${(s.source_ids || []).map(id => {
                        const src = (r.sources || []).find(x => x.id === id);
                        return src ? `INC-${src.number}` : id;
                      }).join(', ')}`}
                </small>
              </li>
            ))}
          </ol>

          {/* Uncertainties */}
          <div className="notice">
            <strong>What remains uncertain</strong>
            <ul>
              {(resolution.uncertainties || r.analysis?.uncertainties || []).map((u, i) => (
                <li key={i}>{u}</li>
              ))}
            </ul>
          </div>

          {/* Recommended Resolver */}
          <h3>Recommended resolver · {resolver.recommended_team?.name || r.resolver?.name}</h3>
          <p className="muted">{resolver.reasoning || r.resolver?.reason}</p>
          {resolver.capacity_constrained && (
            <div className="warning-box">
              <AlertTriangle size={15} />
              <span>Team is operating at maximum capacity. Consider dispatching to alternate: {resolver.alternate_teams?.[0]?.name || 'Secondary queue'}.</span>
            </div>
          )}

          {/* Grounding Source Records */}
          <h3>Source records used ({ (r.sources || []).length })</h3>
          {(r.sources || []).length ? (
            r.sources.map(s => (
              <details key={s.id} className="source-accordion">
                <summary>INC-{s.number} · {s.title}</summary>
                <p className="preserve">{s.solution}</p>
                <small>{s.is_sample ? 'Fictional sample · ' : ''}Keyword overlap coverage: {Math.round((s.retrieval_score || 0) * 100)}%</small>
              </details>
            ))
          ) : (
            <p className="muted">No sufficiently relevant history was found. All steps are hypotheses.</p>
          )}

          {/* Engineer Review Box */}
          {engineer && r.status === 'pending' && (
            <div className="review">
              <h3>Human-in-the-loop: Review & decide</h3>
              <p>Approval applies the proposed category and resolver team. It records your acceptance of the multi-agent plan; it does not execute commands or close the incident.</p>
              
              {collab.engineer_review_packet && (
                <details className="review-packet-details">
                  <summary>View Collaboration Agent Decision Packet</summary>
                  <pre className="packet-pre">{collab.engineer_review_packet}</pre>
                </details>
              )}

              <label>Review rationale (required)
                <textarea 
                  value={comment} 
                  onChange={e => setComment(e.target.value)} 
                  minLength={5} 
                  maxLength={2000} 
                  rows={2} 
                  placeholder="Why do you accept or reject this recommendation?"
                />
              </label>
              <div className="inline">
                <button 
                  disabled={!!busy || comment.trim().length < 5} 
                  onClick={() => act('approve', async () => {
                    await fetch(`/api/recommendations/${r.id}/decision`, {
                      method: 'POST',
                      headers: {'Content-Type': 'application/json'},
                      body: JSON.stringify({ decision: 'approved', comment })
                    });
                    setComment('');
                  })}
                >
                  <CheckCircle2 size={16}/>Approve routing & plan
                </button>
                <button 
                  className="secondary" 
                  disabled={!!busy || comment.trim().length < 5} 
                  onClick={() => act('reject', async () => {
                    await fetch(`/api/recommendations/${r.id}/decision`, {
                      method: 'POST',
                      headers: {'Content-Type': 'application/json'},
                      body: JSON.stringify({ decision: 'rejected', comment })
                    });
                    setComment('');
                  })}
                >
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 4. Specialized Agent Outputs Tab */}
      {activeTab === 'agents' && (
        <div className="tab-pane">
          <div className="agents-grid">
            {/* Triage Agent Card */}
            <div className="agent-card">
              <div className="agent-card-header">
                <strong>🎯 Triage Agent</strong>
                <span className="tool-pill">Gemini Classifier</span>
              </div>
              <div className="agent-card-body">
                <div><small>CATEGORY</small><strong>{triage.category || t.category}</strong></div>
                <div><small>URGENCY</small><Badge value={triage.urgency || 'medium'} /></div>
                <div><small>PRIORITY</small><Badge value={triage.suggested_priority || t.priority} /></div>
                <div><small>FAST TRACK</small><strong>{triage.fast_track_required ? 'Yes (Elevated)' : 'Standard'}</strong></div>
                <div className="full-width">
                  <small>REQUIRED EXPERTISE</small>
                  <div className="inline wrap">
                    {(triage.required_expertise || []).map(k => (
                      <span key={k} className="skill">{k}</span>
                    ))}
                  </div>
                </div>
                {triage.impact_assessment && (
                  <div className="full-width">
                    <small>IMPACT ASSESSMENT</small>
                    <p>{triage.impact_assessment}</p>
                  </div>
                )}
              </div>
            </div>

            {/* SLA Agent Card */}
            <div className="agent-card">
              <div className="agent-card-header">
                <strong>⏱️ SLA Agent</strong>
                <span className="tool-pill">calculate_sla_tool</span>
              </div>
              <div className="agent-card-body">
                <div><small>SLA STATE</small><Badge value={sla.state || 'on_track'} /></div>
                <div><small>MINUTES REMAINING</small><strong>{sla.minutes_remaining || 0}m</strong></div>
                <div><small>BUDGET CONSUMED</small><strong>{sla.elapsed_percent || 0}%</strong></div>
                <div><small>ESCALATION</small><strong>{sla.escalation_needed ? 'Required' : 'None'}</strong></div>
                <div className="full-width">
                  <small>DETERMINISTIC ADVISORY</small>
                  <p>{sla.advisory || sla.reason || 'SLA tracked deterministically.'}</p>
                </div>
              </div>
            </div>

            {/* Knowledge Agent Card */}
            <div className="agent-card">
              <div className="agent-card-header">
                <strong>📚 Knowledge Agent</strong>
                <span className="tool-pill">search_knowledge_tool</span>
              </div>
              <div className="agent-card-body">
                <div><small>SOURCES MATCHED</small><strong>{(knowledge.sources_found || []).length}</strong></div>
                <div><small>MAX COVERAGE</small><strong>{Math.round((knowledge.coverage_score || 0) * 100)}%</strong></div>
                <div><small>MODE</small><strong>{knowledge.hypothesis_only ? 'Hypothesis Only' : 'Grounded'}</strong></div>
                <div className="full-width">
                  <small>SYNTHESIS NOTES</small>
                  <p>{knowledge.synthesis_notes || 'Retrieved grounded incident solutions.'}</p>
                </div>
                {knowledge.query_terms_used?.length > 0 && (
                  <div className="full-width">
                    <small>QUERY TOKENS</small>
                    <div className="inline wrap">
                      {knowledge.query_terms_used.map(term => (
                        <span key={term} className="token-tag">{term}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Resolver Agent Card */}
            <div className="agent-card">
              <div className="agent-card-header">
                <strong>👥 Resolver Agent</strong>
                <span className="tool-pill">rank_resolver_teams_tool</span>
              </div>
              <div className="agent-card-body">
                <div><small>RECOMMENDED</small><strong>{resolver.recommended_team?.name || r.resolver?.name}</strong></div>
                <div><small>MATCH SCORE</small><strong>{resolver.recommended_team?.score || r.resolver?.score}/100</strong></div>
                <div><small>ACTIVE LOAD</small><strong>{resolver.recommended_team?.active_tickets ?? r.resolver?.active_tickets} / {resolver.recommended_team?.capacity ?? r.resolver?.capacity}</strong></div>
                <div><small>STATUS</small><strong>{resolver.capacity_constrained ? 'Capacity Warning' : 'Available'}</strong></div>
                <div className="full-width">
                  <small>ROUTING RATIONALE</small>
                  <p>{resolver.reasoning || r.resolver?.reason}</p>
                </div>
              </div>
            </div>

            {/* Resolution Agent Card */}
            <div className="agent-card">
              <div className="agent-card-header">
                <strong>🔬 Resolution Agent</strong>
                <span className="tool-pill">validate_citations_tool</span>
              </div>
              <div className="agent-card-body">
                <div><small>HYPOTHESES</small><strong>{(resolution.hypotheses || []).length}</strong></div>
                <div><small>STEPS</small><strong>{(resolution.steps || []).length}</strong></div>
                <div><small>GROUNDED STEPS</small><strong>{(resolution.steps || []).filter(s => s.basis === 'historical').length}</strong></div>
                <div><small>SAFETY</small><strong>Read-Only Diagnostics</strong></div>
                <div className="full-width">
                  <small>TENTATIVE SUMMARY</small>
                  <p>{resolution.summary}</p>
                </div>
              </div>
            </div>

            {/* Collaboration Agent Card */}
            <div className="agent-card">
              <div className="agent-card-header">
                <strong>🤝 Collaboration Agent</strong>
                <span className="tool-pill">Synthesis Engine</span>
              </div>
              <div className="agent-card-body">
                <div className="full-width">
                  <small>SUGGESTED HANDOFF NOTE</small>
                  <p>{collab.suggested_handoff_note || 'Ready for assignment.'}</p>
                </div>
                <div className="full-width">
                  <small>REQUESTER-SAFE UPDATE</small>
                  <p>{collab.requester_update || 'Under engineering review.'}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Execution Traces & Tools Tab */}
      {activeTab === 'traces' && (
        <div className="tab-pane">
          {/* Dynamic LangGraph Routing Decisions */}
          {routing.length > 0 && (
            <div className="routing-decisions-card">
              <div className="inline">
                <GitBranch size={16} />
                <strong>LangGraph Conditional Routing Traversal</strong>
              </div>
              <ol className="routing-list">
                {routing.map((dec, i) => (
                  <li key={i}>
                    <code>{dec}</code>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Granular Execution Traces */}
          <h3>Agent Execution Traces ({traces.length})</h3>
          <div className="traces-timeline">
            {traces.length > 0 ? (
              traces.map((tr, i) => (
                <div key={i} className="trace-row">
                  <span className="trace-index">{i + 1}</span>
                  <div className="trace-content">
                    <div className="trace-header">
                      <strong>{tr.agent}</strong>
                      {tr.tool && <span className="trace-tool"><Terminal size={12}/> {tr.tool}</span>}
                      <span className={`badge ${tr.status === 'completed' ? 'approved' : tr.status === 'validation_failed' ? 'rejected' : 'waiting'}`}>
                        {tr.status}
                      </span>
                      <small className="muted">{date(tr.timestamp)}</small>
                    </div>
                    <div className="trace-action">{tr.action}</div>
                    <p className="trace-detail">{tr.detail}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="muted">No execution traces recorded for this recommendation.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
