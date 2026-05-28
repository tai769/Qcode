require('dotenv').config();
const lark = require('@larksuiteoapi/node-sdk');
const { handleMessage } = require('./handler');

// 飞书配置
const FEISHU_APP_ID = process.env.FEISHU_APP_ID;
const FEISHU_APP_SECRET = process.env.FEISHU_APP_SECRET;

if (!FEISHU_APP_ID || !FEISHU_APP_SECRET) {
  console.error('请在 .env 文件中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET');
  process.exit(1);
}

// 创建飞书客户端（用于发送消息）
const client = new lark.Client({
  appId: FEISHU_APP_ID,
  appSecret: FEISHU_APP_SECRET,
  appType: lark.AppType.SelfBuild,
});

// 事件处理器
const eventDispatcher = new lark.EventDispatcher({}).register({
  'im.message.receive_v1': async (data) => {
    try {
      const { message, sender } = data;

      // 只处理文本消息
      if (message.message_type !== 'text') {
        return;
      }

      const groupId = message.chat_id;
      const userId = sender.sender_id.open_id;
      const content = JSON.parse(message.content);
      const text = content.text || '';

      // 去掉@机器人前缀
      const cleanText = text.replace(/@\w+\s*/g, '').trim();

      console.log(`[${new Date().toISOString()}] 收到消息: ${cleanText}`);

      // 处理消息
      const reply = handleMessage(groupId, userId, cleanText);

      // 回复消息
      await client.im.message.reply({
        path: { message_id: message.message_id },
        data: {
          msg_type: 'text',
          content: JSON.stringify({ text: reply }),
        },
      });

      console.log(`[${new Date().toISOString()}] 回复成功: ${reply.substring(0, 50)}...`);
    } catch (error) {
      console.error(`[${new Date().toISOString()}] 处理消息失败:`, error.message || error);
    }
  }
});

// 启动 WebSocket 长连接
const wsClient = new lark.WSClient({
  appId: FEISHU_APP_ID,
  appSecret: FEISHU_APP_SECRET,
  loggerLevel: lark.LoggerLevel.info,
});

wsClient.start({
  eventDispatcher,
});

console.log('🐢 海龟汤飞书机器人已启动（长连接模式）');
console.log('在飞书群里发送"开始游戏"试试吧！');
