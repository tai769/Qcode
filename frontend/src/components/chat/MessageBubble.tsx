import { Message } from '../../types';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  void isSystem;
  
  return (
    <div
      className={`flex gap-3 mb-4 ${
        isUser ? 'justify-end' : 'justify-start'
      }`}
    >
      {isUser && (
        <div className="flex flex-col items-end max-w-[80%]">
          <div className="bg-primary text-primary-foreground px-4 py-2 rounded-lg">
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          <span className="text-xs text-muted-foreground mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
      )}

      {isSystem && (
        <div className="flex flex-col max-w-[80%]">
          <div className="bg-muted px-4 py-2 rounded-lg border">
            <p className="text-sm text-muted-foreground">{message.content}</p>
          </div>
          <span className="text-xs text-muted-foreground mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
      )}

      {!isUser && !isSystem && (
        <div className="flex gap-3 max-w-[80%]">
          <div className="flex-shrink-0">
            <div className="h-8 w-8 bg-secondary rounded-full flex items-center justify-center">
              <span className="text-secondary-foreground">A</span>
            </div>
          </div>
          <div className="flex flex-col flex-1">
            <div className="bg-secondary/50 px-4 py-2 rounded-lg">
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div className="mt-2 border-t pt-2">
                  <p className="text-xs text-muted-foreground mb-1">
                    工具调用:
                  </p>
                  {message.toolCalls.map((tool: any) => (
                    <div key={tool.id} className="text-xs font-mono bg-muted px-2 py-1 rounded">
                      {tool.name}({JSON.stringify(tool.args)})
                    </div>
                  ))}
                </div>
              )}
            </div>
            <span className="text-xs text-muted-foreground mt-1">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
