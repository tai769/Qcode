import { MainLayout } from './components/layout/MainLayout';
import { ChatView } from './components/chat/ChatView';
import { TaskView } from './components/tasks/TaskView';
import { TeamView } from './components/team/TeamView';
import { ProtocolView } from './components/protocol/ProtocolView';
import { TimelineView } from './components/timeline/TimelineView';
import { SettingsView } from './components/settings/SettingsView';
import { LoginPage } from './pages/LoginPage';
import { useAuthStore } from './stores/authStore';
import { useUIStore } from './stores/uiStore';

function App() {
  const { activeTab } = useUIStore();
  const { isAuthenticated } = useAuthStore();

  // 如果未登录，显示登录页面
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const renderActiveView = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatView />;
      case 'tasks':
        return <TaskView />;
      case 'team':
        return <TeamView />;
      case 'protocol':
        return <ProtocolView />;
      case 'timeline':
        return <TimelineView />;
      case 'settings':
        return <SettingsView />;
      default:
        return <ChatView />;
    }
  };

  return (
    <MainLayout>
      {renderActiveView()}
    </MainLayout>
  );
}

export default App;
