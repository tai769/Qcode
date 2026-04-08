import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';

export function ProtocolPanel() {
  return (
    <div className="p-4 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>协议请求</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">任务 #1024</span>
                <Badge variant="secondary">pending</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                等待批准重构方案
              </p>
              <div className="flex gap-2">
                <Button size="sm">批准</Button>
                <Button size="sm" variant="outline">拒绝</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
