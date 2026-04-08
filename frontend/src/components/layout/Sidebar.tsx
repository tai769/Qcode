interface SidebarProps {
  currentView: string;
  onViewChange: (view: string) => void;
}

export function Sidebar({ currentView, onViewChange }: SidebarProps) {
  const menuItems = [
    { id: 'chat', label: '对话', icon: '💬' },
    { id: 'tasks', label: '任务', icon: '📋' },
    { id: 'team', label: '团队', icon: '👥' },
    { id: 'protocol', label: '协议', icon: '📝' },
    { id: 'settings', label: '设置', icon: '⚙️' },
  ];

  return (
    <aside className="w-64 border-r bg-muted/30 h-screen p-4">
      <nav className="space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              currentView === item.id
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted'
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
