import React from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/button';
import { 
  MessageSquare, 
  CheckSquare, 
  Users, 
  FileText, 
  Settings, 
  Clock,
  Menu,
  X,
  LogOut
} from 'lucide-react';

interface MainLayoutProps {
  children: React.ReactNode;
}

const tabs = [
  { id: 'chat' as const, label: '对话', icon: MessageSquare },
  { id: 'tasks' as const, label: '任务', icon: CheckSquare },
  { id: 'team' as const, label: '团队', icon: Users },
  { id: 'protocol' as const, label: '协议', icon: FileText },
  { id: 'timeline' as const, label: '时间线', icon: Clock },
  { id: 'settings' as const, label: '设置', icon: Settings },
];

export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar } = useUIStore();
  const { user, logout } = useAuthStore();

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <aside 
        className={`
          fixed left-0 top-0 z-40 h-full w-64 border-r bg-card transition-transform duration-200
          lg:relative lg:translate-x-0
          ${sidebarOpen ? 'translate' : '-translate-x-full'}
        `}
      >
        <div className="flex h-16 items-center justify-between border-b px-4">
          <h1 className="text-xl font-bold">Qcode</h1>
          <Button 
            variant="ghost" 
            size="icon" 
            className="lg:hidden"
            onClick={toggleSidebar}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="p-4 space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            
            return (
              <Button
                key={tab.id}
                variant={isActive ? 'default' : 'ghost'}
                className="w-full justify-start"
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon className="mr-2 h-4 w-4" />
                {tab.label}
              {isActive && (
                  <span className="ml-auto h-2 w-2 rounded-full bg-white" />
                )}
              </Button>
            );
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 border-t p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
              {user?.username?.charAt(0).toUpperCase() || 'D'}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{user?.username || 'Developer'}</p>
              <p className="text-xs text-muted-foreground">在线</p>
            </div>
            <Button 
              variant="ghost" 
              size="icon"
              onClick={logout}
              title="退出登录"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Mobile Header */}
        <header className="flex h-16 items-center justify-between border-b bg-card px-4 lg:hidden">
          <Button variant="ghost" size="icon" onClick={toggleSidebar}>
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="text-lg font-semibold">Qcode</h1>
          <div className="w-8" />
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
