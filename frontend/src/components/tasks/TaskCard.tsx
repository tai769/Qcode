import { Task } from '../../types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

interface TaskCardProps {
  task: Task;
  onClaim?: (taskId: number) => void;
  onRelease?: (taskId: number) => void;
  currentUserId?: string;
}

export function TaskCard({ task, onClaim, onRelease, currentUserId }: TaskCardProps) {
  const isClaimable = !task.owner && onClaim;
  const isReleasable = task.owner === currentUserId && onRelease;
  void isReleasable;
  void currentUserId;

  const getStatusBadge = () => {
    switch (task.status) {
      case 'pending':
        return <Badge variant="secondary">待认领</Badge>;
      case 'in_progress':
        return <Badge variant="default">进行中</Badge>;
      case 'completed':
        return <Badge variant="outline">已完成</Badge>;
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-medium line-clamp-2 flex-1">
            {task.subject}
          </CardTitle>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent>
        {task.description && (
          <p className="text-xs text-muted-foreground mb-2 line-clamp-3">
            {task.description}
          </p>
        )}
        
        {task.requiredRole && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
            <span>🔒</span>
            <span>需要: {task.requiredRole}</span>
          </div>
        )}
        
        {task.owner && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
            <span>👤</span>
            <span>负责人: {task.owner}</span>
          </div>
        )}
        
        {task.blockedBy && task.blockedBy.length > 0 && (
          <div className="text-xs text-muted-foreground">
            依赖: {task.blockedBy.join(', ')}
          </div>
        )}

        {isClaimable && (
          <div className="mt-3 pt-2 border-t">
            <Button 
              size="sm" 
              className="w-full"
              onClick={() => onClaim?.(task.id)}
            >
              认领任务
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
