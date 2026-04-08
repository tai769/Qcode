import { Teammate } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Circle, 
  User, 
  Mail, 
  Briefcase, 
  MoreVertical 
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TeammateCardProps {
  teammate: Teammate;
  isCurrent?: boolean;
}

export function TeammateCard({ teammate, isCurrent }: TeammateCardProps) {
  const getStatusColor = () => {
    switch (teammate.status) {
      case 'online':
        return 'bg-green-500';
      case 'busy':
        return 'bg-yellow-500';
      case 'offline':
        return 'bg-gray-400';
    }
  };

  const getStatusText = () => {
    switch (teammate.status) {
      case 'online':
        return '在线';
      case 'busy':
        return '忙碌';
      case 'offline':
        return '离线';
    }
  };

  const getRoleText = () => {
    switch (teammate.role) {
      case 'lead':
        return '负责人';
      case 'developer':
        return '开发';
      case 'tester':
        return '测试';
      case 'planner':
        return '策划';
    }
  };

  return (
    <Card className={isCurrent ? 'border-primary' : ''}>
      <CardContent className="p-3">
        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div className="flex-shrink-0">
            <div className="h-10 w-10 bg-secondary rounded-full flex items-center justify-center relative">
              {teammate.avatar ? (
                <img 
                  src={teammate.avatar} 
                  alt={teammate.name}
                  className="h-full w-full rounded-full object-cover"
                />
              ) : (
                <User className="h-5 w-5 text-secondary-foreground" />
              )}
              <div className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background ${getStatusColor()}`} />
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-medium text-sm truncate">
                {teammate.name}
                {isCurrent && <Badge variant="secondary" className="ml-1">我</Badge>}
              </h4>
              <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto">
                <MoreVertical className="h-3 w-3" />
              </Button>
            </div>
            
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Briefcase className="h-3 w-3" />
              <span>{getRoleText()}</span>
              <Circle className={`h-1.5 w-1.5 ${getStatusColor()}`} />
              <span>{getStatusText()}</span>
            </div>

            {teammate.id && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                <Mail className="h-3 w-3" />
                <span className="truncate">{teammate.id}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
