import type { ProgressStep, ProgressTimeline } from '../types/api'

export function createEmptyProgressTimeline(): ProgressTimeline {
  return {
    steps: [],
    collapsed: false,
    summary: undefined,
    expandedByUser: false,
  }
}

function findStepIndex(steps: ProgressStep[], stepId: string, parentId?: string): number {
  if (parentId) {
    const parentIndex = steps.findIndex((step) => step.step_id === parentId)
    if (parentIndex < 0) return -1
    const children = steps[parentIndex].children ?? []
    return children.findIndex((child) => child.step_id === stepId)
  }
  return steps.findIndex((step) => step.step_id === stepId)
}

export function applyStepStart(timeline: ProgressTimeline, step: ProgressStep): ProgressTimeline {
  if (step.parent_id) {
    return timeline
  }

  const next = { ...timeline, steps: [...timeline.steps] }
  const index = next.steps.findIndex((item) => item.step_id === step.step_id)
  const mainStep: ProgressStep = {
    step_id: step.step_id,
    status: 'running',
    label: step.label,
  }
  if (index >= 0) {
    next.steps[index] = { ...next.steps[index], ...mainStep }
  } else {
    next.steps.push(mainStep)
  }
  return next
}

export function applyStepComplete(timeline: ProgressTimeline, stepId: string): ProgressTimeline {
  const index = timeline.steps.findIndex((step) => step.step_id === stepId)
  if (index < 0) {
    return timeline
  }
  const next = { ...timeline, steps: [...timeline.steps] }
  next.steps[index] = { ...next.steps[index], status: 'completed' }
  return next
}

export function applyResponseStreamStart(
  timeline: ProgressTimeline,
  summary?: string,
): ProgressTimeline {
  return {
    ...timeline,
    collapsed: true,
    summary: summary || timeline.summary,
    expandedByUser: false,
  }
}

export function toggleProgressExpanded(timeline: ProgressTimeline): ProgressTimeline {
  return {
    ...timeline,
    expandedByUser: !timeline.expandedByUser,
  }
}

export function buildCollapseLabel(timeline: ProgressTimeline): string {
  if (timeline.summary?.trim()) {
    return timeline.summary.trim()
  }
  const expertStep = timeline.steps.find((step) => step.step_id === 'match_expert')
  const expertSuffix = expertStep?.label.includes('·')
    ? expertStep.label.split('·').slice(1).join('·').trim()
    : ''
  if (expertSuffix) return expertSuffix
  const completedCount = timeline.steps.filter((step) => step.status === 'completed').length
  if (completedCount > 0) return `${completedCount} 步`
  return ''
}

export function isTimelineVisible(timeline: ProgressTimeline | undefined): boolean {
  return Boolean(timeline && timeline.steps.length > 0)
}

export { findStepIndex }
