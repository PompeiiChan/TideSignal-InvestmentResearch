import { useEffect } from 'react'
import { useInvestmentStore } from '../stores/useInvestmentStore'

export function JsonModal() {
  const jsonModal = useInvestmentStore((state) => state.jsonModal)
  const closeJson = useInvestmentStore((state) => state.closeJson)

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeJson()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [closeJson])

  if (!jsonModal) return null

  return (
    <div className="modal-backdrop show" aria-hidden="false" onClick={closeJson}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="jsonTitle" onClick={(event) => event.stopPropagation()}>
        <div className="modal-head">
          <span id="jsonTitle">{jsonModal.title}</span>
          <button className="modal-close" type="button" aria-label="关闭" onClick={closeJson}>
            ×
          </button>
        </div>
        <pre className="json-pre">{JSON.stringify(jsonModal.data, null, 2)}</pre>
      </div>
    </div>
  )
}
