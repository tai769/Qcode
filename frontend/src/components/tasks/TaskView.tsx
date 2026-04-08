import { TaskBoard } from './TaskBoard';

export function TaskView() {
  return (
    <div className="h-screen">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">任务看板</h2>
        <p className="text-sm text-muted-foreground">管理任务进度</p>
      </div>
      <TaskBoard />
    </div>
  );
}
