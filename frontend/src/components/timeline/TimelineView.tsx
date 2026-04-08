export function TimelineView() {
  return (
    <div className="h-screen">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">工具输出时间线</h2>
        <p className="text-sm text-muted-foreground">查看工具调用历史</p>
      </div>
      <div className="p-6">
        <p className="text-muted-foreground">暂无工具输出记录</p>
      </div>
    </div>
  );
}
