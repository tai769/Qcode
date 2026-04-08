export function ChatTimeline() {
  return (
    <div className="border-l ml-4 pl-4 space-y-2">
      <div className="relative">
        <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-primary" />
        <p className="text-sm">系统初始化完成</p>
      </div>
      <div className="relative">
        <div className="absolute -left-[21px] w-3 h-3 rounded-full bg-muted" />
        <p className="text-sm text-muted-foreground">等待用户输入...</p>
      </div>
    </div>
  );
}
