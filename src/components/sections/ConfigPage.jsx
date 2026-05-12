import InfoRow from '../common/InfoRow'
import Panel from '../common/Panel'

function ConfigPage({ bootstrap }) {
  const config = bootstrap.config?.config
  const routing = config?.routing ?? {}
  const limits = config?.limits ?? {}

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Deployment profile">
        <dl className="grid gap-3 text-sm">
          <InfoRow label="Profile" value={config?.deployment_profile || 'local_dev'} />
          <InfoRow label="API prefix" value={routing.api_prefix || '/api/v1'} />
          <InfoRow label="Frontend base" value={routing.frontend_base_path || '/'} />
        </dl>
      </Panel>
      <Panel title="Limits">
        <dl className="grid gap-3 text-sm">
          <InfoRow label="Free chats" value={String(limits.free_chats_per_user ?? 2)} />
          <InfoRow label="Paid chats" value={String(limits.max_chats_per_user ?? 5)} />
          <InfoRow label="Max top-k" value={String(limits.max_top_k ?? 10)} />
        </dl>
      </Panel>
    </div>
  )
}

export default ConfigPage
