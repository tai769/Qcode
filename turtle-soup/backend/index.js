require('dotenv').config();
const { handleMessage } = require('./handler');

/**
 * 海龟汤游戏入口
 * 供飞书机器人调用
 */

// 飞书配置
const FEISHU_APP_ID = process.env.FEISHU_APP_ID;
const FEISHU_APP_SECRET = process.env.FEISHU_APP_SECRET;

// 默认群组
const DEFAULT_GROUP = 'default_group';

/**
 * 处理飞书消息
 * @param {object} event - 飞书消息事件
 * @returns {string} - 回复消息
 */
function handleFeishuMessage(event) {
  const { groupId, userId, text } = event;

  // 去掉可能的@机器人前缀
  const cleanText = text.replace(/@\w+\s*/g, '').trim();

  return handleMessage(groupId || DEFAULT_GROUP, userId, cleanText);
}

/**
 * HTTP API 入口（供其他服务调用）
 */
const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'turtle-soup' });
});

// 处理消息
app.post('/api/message', (req, res) => {
  const { groupId, userId, text } = req.body;

  if (!text) {
    return res.status(400).json({ error: '缺少消息内容' });
  }

  const reply = handleMessage(groupId || DEFAULT_GROUP, userId, text);
  res.json({ reply });
});

// 飞书 Webhook 回调
app.post('/api/feishu/webhook', async (req, res) => {
  // 处理飞书验证请求
  if (req.body.challenge) {
    return res.json({ challenge: req.body.challenge });
  }

  // 处理消息
  const event = req.body.event;
  if (event && event.message) {
    const groupId = event.message.chat_id;
    const userId = event.sender?.sender_id?.open_id || 'unknown';
    const text = event.message.content?.text || '';

    const reply = handleMessage(groupId, userId, text);

    // 回复消息
    await replyToFeishu(groupId, reply);
  }

  res.json({ code: 0 });
});

// 回复飞书消息
async function replyToFeishu(chatId, text) {
  if (!FEISHU_APP_ID || !FEISHU_APP_SECRET) {
    console.log('飞书未配置，跳过回复');
    return;
  }

  try {
    // 获取 access_token
    const tokenRes = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        app_id: FEISHU_APP_ID,
        app_secret: FEISHU_APP_SECRET
      })
    });
    const { tenant_access_token } = await tokenRes.json();

    // 发送消息
    await fetch(`https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${tenant_access_token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        receive_id: chatId,
        msg_type: 'text',
        content: JSON.stringify({ text })
      })
    });
  } catch (error) {
    console.error('回复飞书消息失败:', error);
  }
}

// 启动服务
app.listen(PORT, () => {
  console.log(`🐢 海龟汤服务运行在 http://localhost:${PORT}`);
});

module.exports = { handleFeishuMessage, handleMessage };
