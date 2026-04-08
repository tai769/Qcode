import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Avatar, AvatarFallback } from '../ui/avatar';
import { Badge } from '../ui/badge';

const teammates = [
  { name: 'Alice', role: 'Frontend', status: 'online' },
  { name: 'Bob', role: 'Backend', status: 'busy' },
  { name: 'Charlie', role: 'Designer', status: 'offline' },
];

export function TeamPanel() {
  return (
    <div className="p-4 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>团队成员</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {teammates.map((member) => (
              <div key={member.name} className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback>{member.name[0]}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <p className="font-medium">{member.name}</p>
                  <p className="text-sm text-muted-foreground">{member.role}</p>
                </div>
                <Badge variant={member.status === 'online' ? 'default' : 'secondary'}>
                  {member.status}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
