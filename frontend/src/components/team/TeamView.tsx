import { TeamPanel } from './TeamPanel';

export function TeamView() {
  return (
    <div className="h-screen">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">团队协作</h2>
        <p className="text-sm text-muted-foreground">查看团队成员状态</p>
      </div>
      <TeamPanel />
    </div>
  );
}
