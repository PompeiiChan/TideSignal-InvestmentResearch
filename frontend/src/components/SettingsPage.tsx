import { useInvestmentStore } from '../stores/useInvestmentStore'

export function SettingsPage() {
  const configStatus = useInvestmentStore((state) => state.configStatus)

  return (
    <section className="settings-view">
      <div className="view-grid">
        {!configStatus ? <div className="info-card full-row">状态读取中</div> : null}
        {configStatus?.models.map((model) => (
          <div key={model.name} className="info-card">
            <h3>{model.name}</h3>
            <p>Key、base_url、model 在后端配置中维护，前端只展示配置状态。</p>
            <ul>
              <li>状态：{model.status}</li>
              <li>字段：{model.fields.join(' / ')}</li>
              <li>缺失字段：{model.missing_fields.join(' / ')}</li>
            </ul>
          </div>
        ))}
        <div className="info-card full-row">
          <h3>Prompt 模块</h3>
          <p>总控 Agent、热点助手、问数助手、问股助手和质检模块先使用默认 System Prompt，后续可替换。</p>
          <ul>
            {configStatus?.prompts.map((prompt) => (
              <li key={prompt.agent}>{prompt.name}：{prompt.status}</li>
            ))}
          </ul>
        </div>
        <div className="info-card full-row">
          <h3>合规规则</h3>
          <p>默认扫描黑名单表达，并检查风险提示和引用来源。</p>
          <ul>
            <li>黑名单表达：{configStatus?.compliance_rules.blacklist_expressions.join(' / ')}</li>
            <li>风险提示必需：{configStatus?.compliance_rules.risk_tip_required ? 'true' : 'false'}</li>
            <li>引用来源必需：{configStatus?.compliance_rules.citation_required ? 'true' : 'false'}</li>
          </ul>
        </div>
      </div>
    </section>
  )
}
