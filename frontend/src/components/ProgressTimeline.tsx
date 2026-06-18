import type { ProgressStep, ProgressTimeline } from '../types/api'
import { buildCollapseLabel } from '../utils/progressTimeline'

interface ProgressTimelineViewProps {
  timeline: ProgressTimeline
  onToggle: () => void
}

function StepRow({ step }: { step: ProgressStep }) {
  const completed = step.status === 'completed'
  return (
    <li className={`progress-step${completed ? ' is-completed' : ' is-running'}`}>
      <span className="progress-step-marker" aria-hidden="true" />
      <span className="progress-step-label">{step.label}</span>
    </li>
  )
}

export function ProgressTimelineView({ timeline, onToggle }: ProgressTimelineViewProps) {
  const expanded = !timeline.collapsed || timeline.expandedByUser
  const collapseDetail = buildCollapseLabel(timeline)

  if (!timeline.steps.length) {
    return null
  }

  return (
    <div className={`progress-timeline${expanded ? ' is-expanded' : ' is-collapsed'}`}>
      <button
        type="button"
        className="progress-timeline-toggle"
        aria-expanded={expanded}
        onClick={onToggle}
      >
        <span className="progress-timeline-chevron" aria-hidden="true">
          {expanded ? '▾' : '▸'}
        </span>
        <span className="progress-timeline-title">执行过程</span>
        {!expanded && collapseDetail ? (
          <span className="progress-timeline-summary">· {collapseDetail}</span>
        ) : null}
      </button>
      <div className="progress-timeline-body" hidden={!expanded}>
        <ol className="progress-timeline-steps">
          {timeline.steps.map((step) => (
            <StepRow key={step.step_id} step={step} />
          ))}
        </ol>
      </div>
    </div>
  )
}
