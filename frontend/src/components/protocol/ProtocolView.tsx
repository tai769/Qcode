import { ProtocolPanel } from './ProtocolPanel';

export function ProtocolView() {
  return (
    <div className="h-screen">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">协议/审批</h2>
        <p className="text-sm text-muted-foreground">管理协议请求和审批</p>
      </div>
      <ProtocolPanel />
    </div>
  );
}
