import { useStore } from '../../store/useStore';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

export function TaskBoard() {
  const { tasks, updateTask } = useStore();
  
  const columns = [
    { id: 'pending', title: '待处理', status: 'pending' as const },
    { id: 'in_progress', title: '进行中', status: 'in_progress' as const },
    { id: 'completed', title: '已完成', status: 'completed' as const },
  ];

  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      {columns.map((column) => (
        <Card key={column.id}>
          <CardHeader>
            <CardTitle className="text-sm">{column.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {tasks.filter(t => t.status === column.status).map((task) => (
                <div key={task.id} className="p-3 border rounded-lg">
                  <p className="font-medium text-sm">{task.title}</p>
                  <div className="flex items-center justify-between mt-2">
                    <Badge variant="secondary">{column.status}</Badge>
                    <div className="flex gap-1">
                      {column.status !== 'completed' && (
                        <Button
                          size="sm"
                          onClick={() => updateTask(task.id, 'completed')}
                        >
                          完成
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
