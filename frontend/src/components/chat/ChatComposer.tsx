import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send } from 'lucide-react';

interface ChatComposerProps {
  onSendMessage: (content: string) => void;
  disabled?: boolean;
}

export function ChatComposer({ onSendMessage, disabled }: ChatComposerProps) {
  const [content, setContent] = useState('');

  const handleSend = () => {
    if (content.trim()) {
      onSendMessage(content.trim());
      setContent('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-background p-4">
      <div className="flex gap-2">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
          className="min-h-[60px] max-h-[200px] resize-none"
          disabled={disabled}
        />
        <Button 
          onClick={handleSend} 
          disabled={!content.trim() || disabled}
          className="h-[60px] px-4"
        >
          <Send className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}
