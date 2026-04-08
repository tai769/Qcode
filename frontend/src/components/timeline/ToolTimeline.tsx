import { useChatStore } from '@/stores/chatStore';
import { ToolCallCard } from '../chat/ToolCallCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Clock } from 'lucide-react';

export function ToolTimeline() {
  const { messages } = useChatStore();

  // 收集所有工具调用
  const allToolCalls = messages.flatMap((message) => {
    const calls: { call: any; output?: any }[] = [];
    
    if (message.toolCalls) {
      message.toolCalls.forEach((call) => {
        calls.push({ call });
      });
    }
    
    if (message.toolOutputs) {
      message.toolOutputs.forEach((output) => {
        // 尝试匹配对应的调用
        const matchingCall = message.toolCalls?.find(c => c.id === output.id);
        if (matchingCall) {
          // 如果已经有匹配的调用，添加输出
          const existing = calls.find(c => c.call.id === output.id);
          if (existing) {
            existing.output = output;
          }
        } else {
          calls.push({ call: { id: output.id, name: output.name, args: {} }, output });
        }
      });
    }
    
    return calls;
  });

  const totalCount = allToolCalls.length;
  const completedCount = allToolCalls.filter(c => c.output).length;
  const runningCount = totalCount - completedCount;

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Clock className="h-5 w-5" />
          工具输出时间线
        </h2>
        <div className="flex gap-2 mt-2">
          <Badge variant="secondary">总计: {totalCount}</Badge>
          <Badge variant="default">完成: {completedCount}</Badge>
          <Badge variant="outline" className="text-yellow-600">运行中: {runningCount}</Badge>
        </div>
      </div>

      <ScrollArea className="flex-1 p-4">
        {allToolCalls.length === 0 ? (
          <div className="text-center text-sm text-muted-foreground py-8">
            暂无工具调用记录
          </div>
        ) : (
          <div className="space-y-2">
            {allToolCalls.map(({ call, output }) => (
              <ToolCallCard
                key={call.id}
                toolCall={call}
                output={output}
              />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
