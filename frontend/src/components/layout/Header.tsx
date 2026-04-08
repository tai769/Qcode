import { useStore } from '../../store/useStore';

export function Header() {
  const { isConnected } = useStore();
  
  return (
    <header className="border-b bg-background p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Qcode</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm">{isConnected ? '已连接' : '未连接'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
