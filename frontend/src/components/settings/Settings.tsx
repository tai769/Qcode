import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';

export function Settings() {
  return (
    <div className="p-4 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>连接设置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">API URL</label>
              <input
                type="text"
                defaultValue="http://localhost:8000"
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </div>
            <Button>测试连接</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
