const { startGame, askQuestion, checkAnswer, revealAnswer, nextStory, getHint, createStory, saveStory, optimizeStory, listStories } = require('./game');

// 命令映射
const COMMANDS = {
  '开始游戏': 'start',
  '开始': 'start',
  '下一题': 'next',
  '换一题': 'next',
  '公布答案': 'reveal',
  '揭晓答案': 'reveal',
  '答案': 'reveal',
  '提示': 'hint',
  '帮助': 'help',
  '规则': 'help',
  'help': 'help',
  '创建汤': 'create',
  '定制汤': 'create',
  '保存汤': 'save',
  '优化汤': 'optimize',
  '查看汤库': 'list',
  '汤库': 'list',
  '有什么汤': 'list'
};

/**
 * 解析消息
 * @param {string} text - 用户输入的文本
 * @returns {object} - { type, command, content }
 */
function parseMessage(text) {
  if (!text || typeof text !== 'string') {
    return { type: 'unknown', command: null, content: '' };
  }

  const trimmed = text.trim();

  // 检查是否是命令
  for (const [keyword, command] of Object.entries(COMMANDS)) {
    if (trimmed === keyword || trimmed.startsWith(keyword)) {
      return { type: 'command', command, content: trimmed };
    }
  }

  // 其他消息视为提问
  return { type: 'question', command: null, content: trimmed };
}

/**
 * 处理消息
 * @param {string} groupId - 群组ID
 * @param {string} userId - 用户ID
 * @param {string} text - 用户消息
 * @returns {string} - 回复消息
 */
function handleMessage(groupId, userId, text) {
  const parsed = parseMessage(text);

  switch (parsed.type) {
    case 'command':
      return handleCommand(groupId, parsed.command, parsed.content);

    case 'question':
      return handleQuestion(groupId, parsed.content);

    default:
      return '我不太明白你的意思，发送"帮助"查看游戏规则。';
  }
}

/**
 * 处理命令
 * @param {string} groupId - 群组ID
 * @param {string} command - 命令类型
 * @param {string} content - 命令内容
 * @returns {string} - 回复消息
 */
function handleCommand(groupId, command, content = '') {
  switch (command) {
    case 'start':
      const result = startGame(groupId);
      return result.message;

    case 'next':
      const nextResult = nextStory(groupId);
      return nextResult.message;

    case 'reveal':
      const revealResult = revealAnswer(groupId);
      return revealResult.message;

    case 'hint':
      const hintResult = getHint(groupId);
      return hintResult.message;

    case 'help':
      return getHelpMessage();

    case 'create':
      const createResult = createStory(groupId, content);
      return createResult.message;

    case 'save':
      const saveResult = saveStory(groupId, content);
      return saveResult.message;

    case 'optimize':
      const optimizeResult = optimizeStory(groupId, content);
      return optimizeResult.message;

    case 'list':
      const listResult = listStories();
      return listResult.message;

    default:
      return '未知命令，发送"帮助"查看游戏规则。';
  }
}

/**
 * 处理提问
 * @param {string} groupId - 群组ID
 * @param {string} question - 问题内容
 * @returns {string} - 回复消息
 */
function handleQuestion(groupId, question) {
  // 检查是否是猜答案（以"答案是"、"真相是"开头，或直接陈述）
  const guessPatterns = [
    /^答案是/,
    /^真相是/,
    /^因为/,
    /^我猜/,
    /^我答/
  ];
  const isGuess = guessPatterns.some(pattern => pattern.test(question));

  if (isGuess) {
    const result = checkAnswer(groupId, question);
    return result.message;
  }

  // 否则当作提问
  const result = askQuestion(groupId, question);
  return result.message;
}

/**
 * 获取帮助信息
 * @returns {string}
 */
function getHelpMessage() {
  return `🐢 海龟汤游戏 - 功能列表

━━━━━━━━━━━━━━━━
🎮 基本玩法
━━━━━━━━━━━━━━━━
• 开始游戏 - 出一道海龟汤题
• 提示 - 获取提示（每题限3次）
• 公布答案 - 揭晓真相
• 下一题 - 跳过当前题
• 帮助 - 显示此菜单

━━━━━━━━━━━━━━━━
❓ 提问方式
━━━━━━━━━━━━━━━━
直接提问，我会回答"是/不是/不重要"
例如：这个人死了吗？
例如：是意外吗？

━━━━━━━━━━━━━━━━
🎯 猜答案
━━━━━━━━━━━━━━━━
• 答案是xxx
• 我猜xxx
• 真相是xxx

━━━━━━━━━━━━━━━━
✨ 创建定制汤
━━━━━━━━━━━━━━━━
• 创建汤 [汤面] - 创建新故事
• 保存汤 [故事ID] [汤底] - 原样保存
• 优化汤 [故事ID] [汤底] - 保存并提取关键词

━━━━━━━━━━━━━━━━
📚 故事主题
━━━━━━━━━━━━━━━━
生活、科技、职场、悬疑等

发送"开始游戏"开始推理吧！🎉`;
}

module.exports = {
  parseMessage,
  handleMessage,
  handleCommand,
  handleQuestion,
  getHelpMessage
};
