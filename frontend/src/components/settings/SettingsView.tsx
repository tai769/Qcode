import { Settings } from './Settings';

export function SettingsView() {
  return (
    <div className="h-screen">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">设置</h2>
        <p className="text-sm text-muted-foreground">配置应用连接和偏好设置</p>
      </div>
      <Settings />
    </div>
  );
}
