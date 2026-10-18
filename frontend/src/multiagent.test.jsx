import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MultiAgentView } from './MultiAgentView';

afterEach(cleanup);

describe('MultiAgentView component', () => {
  const mockRecommendation = {
    id: 'rec-1',
    status: 'pending',
    model: 'gemini-3.8-flash',
    created_at: '2026-10-17T12:00:00Z',
    analysis: {
      category: 'Network',
      suggested_priority: 'P2',
      summary: 'Intermittent VPN disruption detected across multiple remote users.',
      hypotheses: ['Gateway certificate expired', 'DNS resolution timeout'],
      required_expertise: ['vpn', 'radius'],
      steps: [
        { instruction: 'Inspect gateway certificate status.', source_ids: ['src-1'], basis: 'historical' },
        { instruction: 'Verify local routing tables on client.', source_ids: [], basis: 'hypothesis' }
      ],
      uncertainties: ['Internal RADIUS server telemetry not confirmed.']
    },
    sources: [
      { id: 'src-1', number: 101, title: 'VPN Certificate Renewal', solution: 'Renewed CA certificate and pushed profile.', retrieval_score: 0.35, is_sample: true }
    ],
    resolver: {
      id: 'team-1',
      name: 'Network Operations',
      score: 85,
      reason: 'Category match and skill overlap',
      active_tickets: 3,
      capacity: 10
    },
    multi_agent: {
      triage: {
        category: 'Network',
        urgency: 'high',
        suggested_priority: 'P2',
        required_expertise: ['vpn', 'radius'],
        impact_assessment: 'Affects multiple remote developers.',
        fast_track_required: false
      },
      knowledge: {
        sources_found: [{ id: 'src-1', number: 101 }],
        query_terms_used: ['vpn', 'disconnect', 'gateway'],
        coverage_score: 0.35,
        hypothesis_only: false,
        synthesis_notes: 'Retrieved 1 relevant incident.'
      },
      resolver: {
        recommended_team: { name: 'Network Operations', score: 85, active_tickets: 3, capacity: 10 },
        capacity_constrained: false,
        reasoning: 'Category match and skill overlap'
      },
      resolution: {
        summary: 'Intermittent VPN disruption detected across multiple remote users.',
        hypotheses: ['Gateway certificate expired'],
        steps: [
          { instruction: 'Inspect gateway certificate status.', source_ids: ['src-1'], basis: 'historical' }
        ],
        uncertainties: ['Internal RADIUS server telemetry not confirmed.']
      },
      sla: {
        state: 'on_track',
        reason: 'More than 60 mins remaining',
        minutes_remaining: 320,
        elapsed_percent: 25,
        escalation_needed: false,
        advisory: 'NORMAL: SLA on track with 320 minutes remaining.'
      },
      collaboration: {
        executive_summary: 'Incident categorized as Network. Diagnostic plan formulated.',
        engineer_review_packet: 'RECOMMENDED ACTION: Route to Network Operations.',
        suggested_handoff_note: 'Multi-agent analysis completed.',
        requester_update: 'Ticket prioritized as P2.'
      },
      traces: [
        {
          agent: 'Triage Agent',
          action: 'Incident Classification',
          tool: 'Gemini Classifier',
          status: 'completed',
          detail: 'Classified as Network with high urgency.',
          timestamp: '2026-10-17T12:00:01Z'
        },
        {
          agent: 'Knowledge Agent',
          action: 'Historical Search',
          tool: 'search_knowledge_tool',
          status: 'completed',
          detail: 'Retrieved 1 source.',
          timestamp: '2026-10-17T12:00:02Z'
        }
      ],
      routing_decisions: [
        'Triage routed incident: priority=P2',
        'Standard knowledge search route executed'
      ]
    }
  };

  const mockTicket = {
    id: 't-1',
    number: 1001,
    title: 'VPN disconnecting',
    category: 'Network',
    priority: 'P2',
    status: 'open',
    version: 1
  };

  function MockBadge({ value }) {
    return <span data-testid="badge">{value}</span>;
  }

  it('renders multi-agent orchestration pipeline and executive summary', () => {
    render(
      <MultiAgentView 
        recommendation={mockRecommendation}
        ticket={mockTicket}
        teams={[]}
        engineer={true}
        busy=""
        act={vi.fn()}
        comment=""
        setComment={vi.fn()}
        date={s => s}
        Badge={MockBadge}
      />
    );

    expect(screen.getByText('LANGGRAPH MULTI-AGENT ORCHESTRATION')).toBeDefined();
    expect(screen.getByText('6 AGENTS COLLABORATING')).toBeDefined();
    expect(screen.getByText('Collaboration Agent · Executive Summary')).toBeDefined();
    expect(screen.getByText(/Grounded Synthesis/)).toBeDefined();
  });

  it('allows navigating between overview, specialized agent outputs, and execution traces', async () => {
    const user = userEvent.setup();
    render(
      <MultiAgentView 
        recommendation={mockRecommendation}
        ticket={mockTicket}
        teams={[]}
        engineer={true}
        busy=""
        act={vi.fn()}
        comment=""
        setComment={vi.fn()}
        date={s => s}
        Badge={MockBadge}
      />
    );

    // Switch to Specialized Agent Outputs tab
    const agentTabBtn = screen.getByRole('button', { name: /Specialized Agent Outputs/i });
    await user.click(agentTabBtn);

    expect(screen.getByText('🎯 Triage Agent')).toBeDefined();
    expect(screen.getByText('⏱️ SLA Agent')).toBeDefined();
    expect(screen.getByText('📚 Knowledge Agent')).toBeDefined();
    expect(screen.getByText('👥 Resolver Agent')).toBeDefined();
    expect(screen.getByText('🔬 Resolution Agent')).toBeDefined();
    expect(screen.getByText('🤝 Collaboration Agent')).toBeDefined();

    // Switch to Execution Traces tab
    const tracesTabBtn = screen.getByRole('button', { name: /Execution Traces & Tools/i });
    await user.click(tracesTabBtn);

    expect(screen.getByText('LangGraph Conditional Routing Traversal')).toBeDefined();
    expect(screen.getByText('Triage routed incident: priority=P2')).toBeDefined();
    expect(screen.getByText('search_knowledge_tool')).toBeDefined();
  });
});
