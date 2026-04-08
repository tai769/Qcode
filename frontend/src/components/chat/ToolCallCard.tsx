import { ToolCall, ToolOutput } from '@/types';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ToolCallCardProps {
  toolCall: ToolCall;
  output?: ToolOutput;
}

export function ToolCallCard({ toolCall, output }: ToolCallCardProps) {
  const status = output ? 'success' : 'running';

  return (
    <Card className="my-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-mono">{toolCall.name}</CardTitle>
          <Badge variant={status === 'success' ? 'default' : 'secondary'}>
            {status === 'success' ? '完成' : '运行中'}
          </Badge>
        </div>
        {toolCall.args && Object.keys(toolCall.args).length > 0 && (
          <pre className="text-xs text-muted-foreground mt-1 overflow-x-auto">
            {JSON.stringify(toolCall.args, null, 2)}
          </pre>
        )}
      </CardHeader>
      {output && (
        <CardContent className="pt-2">
          <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
            {output.output}
          </pre>
          <span className="text-xs text-muted-foreground mt-1 block">
            {new Date(output.timestamp).toLocaleTimeString()}
          </span>
        </CardContent>
      )}
    </Card>
  );
}
