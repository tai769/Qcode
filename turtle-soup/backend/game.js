const fs = require('fs');
const path = require('path');

// 加载所有故事
const storiesDir = path.join(__dirname, '..', 'stories');
let stories = [];

function loadStories() {
  const files = fs.readdirSync(storiesDir).filter(f => f.endsWith('.json'));
  stories = files.map(f => {
    const content = fs.readFileSync(path.join(storiesDir, f), 'utf-8');
    return JSON.parse(content);
  });
  console.log(`已加载 ${stories.length} 个海龟汤故事`);
}

// 游戏状态（内存存储）
const gameStates = new Map();

/**
 * 开始游戏
 * @param {string} groupId - 群组ID
 * @returns {object} - { storyId, 汤面, difficulty }
 */
function startGame(groupId) {
  if (stories.length === loadStories()) {
    loadStories();
  }

  // 随机选一个故事
  const story = stories[Math.floor(Math.random() * stories.length)];

  // 保存游戏状态
  gameStates.set(groupId, {
    storyId: story.id,
    status: 'playing',
    questionsAsked: 0,
    startedAt: new Date().toISOString()
  });

  return {
    storyId: story.id,
    汤面: story.汤面,
    difficulty: story.difficulty || '未知',
    message: `🐢 海龟汤来啦！\n\n汤面：${story.汤面}\n\n请用提问来推理真相，我会回答"是/不是/不重要"。`
  };
}

/**
 * 提问
 * @param {string} groupId - 群组ID
 * @param {string} question - 玩家的问题
 * @returns {object} - { answer, message }
 */
function askQuestion(groupId, question) {
  const state = gameStates.get(groupId);
  if (!state || state.status !== 'playing') {
    return { answer: null, message: '当前没有进行中的游戏，请发送"开始游戏"开始一局。' };
  }

  const story = stories.find(s => s.id === state.storyId);
  if (!story) {
    return { answer: null, message: '找不到当前题目，请重新开始游戏。' };
  }

  state.questionsAsked++;

  // 简单关键词匹配逻辑
  const answer = matchQuestion(question, story);

  return {
    answer,
    message: answer
  };
}

/**
 * 匹配问题
 * @param {string} question - 玩家的问题
 * @param {object} story - 故事数据
 * @returns {string} - "是" / "不是" / "不重要"
 */
function matchQuestion(question, story) {
  const questionLower = question.toLowerCase();
  const 汤底 = story.汤底;
  const keywords = story.关键词 || [];

  // 检查是否直接包含答案关键词
  for (const keyword of keywords) {
    if (questionLower.includes(keyword)) {
      return '是';
    }
  }

  // 检查问题是否与汤底相关
  // 这里是简化逻辑，实际可以更复杂
  const questionWords = questionLower.split(/[，。？！、\s]+/).filter(w => w.length > 0);
  for (const word of questionWords) {
    if (汤底.includes(word) && word.length > 1) {
      return '是';
    }
  }

  // 默认返回不重要
  return '不重要';
}

/**
 * 检查答案
 * @param {string} groupId - 群组ID
 * @param {string} answer - 玩家的答案
 * @returns {object} - { correct, message }
 */
function checkAnswer(groupId, answer) {
  const state = gameStates.get(groupId);
  if (!state || state.status !== 'playing') {
    return { correct: false, message: '当前没有进行中的游戏，请发送"开始游戏"开始一局。' };
  }

  const story = stories.find(s => s.id === state.storyId);
  if (!story) {
    return { correct: false, message: '找不到当前题目，请重新开始游戏。' };
  }

  // 检查答案是否与汤底匹配
  const answerLower = answer.toLowerCase();
  const 汤底 = story.汤底;
  const keywords = story.关键词 || [];

  // 计算匹配度
  let matchScore = 0;
  for (const keyword of keywords) {
    if (answerLower.includes(keyword)) {
      matchScore++;
    }
  }

  // 如果匹配超过一半关键词，认为猜中
  const threshold = Math.ceil(keywords.length / 2);
  if (matchScore >= threshold) {
    state.status = 'finished';
    return {
      correct: true,
      message: `🎉 恭喜你答对了！\n\n汤底：${story.汤底}\n\n共提问 ${state.questionsAsked} 次。`
    };
  }

  return {
    correct: false,
    message: '还没猜对哦，继续推理吧！'
  };
}

/**
 * 公布答案
 * @param {string} groupId - 群组ID
 * @returns {object} - { message }
 */
function revealAnswer(groupId) {
  const state = gameStates.get(groupId);
  if (!state || state.status !== 'playing') {
    return { message: '当前没有进行中的游戏，请发送"开始游戏"开始一局。' };
  }

  const story = stories.find(s => s.id === state.storyId);
  if (!story) {
    return { message: '找不到当前题目，请重新开始游戏。' };
  }

  state.status = 'finished';

  return {
    message: `📖 答案揭晓！\n\n汤底：${story.汤底}\n\n本次共提问 ${state.questionsAsked} 次。`
  };
}

/**
 * 下一题
 * @param {string} groupId - 群组ID
 * @returns {object} - { storyId, 汤面, message }
 */
function nextStory(groupId) {
  // 清除当前状态
  gameStates.delete(groupId);

  // 开始新游戏
  return startGame(groupId);
}

/**
 * 获取提示
 * @param {string} groupId - 群组ID
 * @returns {object} - { message }
 */
function getHint(groupId) {
  const state = gameStates.get(groupId);
  if (!state || state.status !== 'playing') {
    return { message: '当前没有进行中的游戏，请发送"开始游戏"开始一局。' };
  }

  const story = stories.find(s => s.id === state.storyId);
  if (!story || !story.提示 || story.提示.length === 0) {
    return { message: '这道题没有提示哦，自己加油推理吧！' };
  }

  // 随机返回一个提示
  const hint = story.提示[Math.floor(Math.random() * story.提示.length)];

  return {
    message: `💡 提示：${hint}`
  };
}

// 初始化加载故事
loadStories();

/**
 * 创建新汤
 * @param {string} groupId - 群组ID
 * @param {string} content - 用户输入的内容
 * @returns {object} - { message, storyId }
 */
function createStory(groupId, content) {
  // 解析用户输入，期望格式：创建汤 [汤面]
  const 汤面 = content.replace(/^创建汤\s*/, '').trim();

  if (!汤面 || 汤面.length < 10) {
    return {
      message: '📝 请提供汤面内容（至少10个字）。\n\n格式：创建汤 [你的汤面]\n例如：创建汤 一个人走进酒吧，要了一杯水...'
    };
  }

  // 生成故事ID
  const storyId = `custom_${Date.now()}`;

  // 创建故事对象
  const story = {
    id: storyId,
    difficulty: 'custom',
    theme: '用户创作',
    汤面: 汤面,
    汤底: '待填写',
    关键词: [],
    提示: [],
    createdBy: groupId,
    createdAt: new Date().toISOString()
  };

  // 保存故事
  const storyPath = path.join(__dirname, '..', 'stories', `${storyId}.json`);
  fs.writeFileSync(storyPath, JSON.stringify(story, null, 2), 'utf-8');

  // 重新加载故事
  loadStories();

  return {
    message: `📝 新汤已创建！\n\n汤面：${汤面}\n\n请提供汤底（真相），格式：\n优化汤 ${storyId} [汤底内容]\n\n例如：优化汤 ${storyId} 男人打嗝了，酒保用枪吓他治好了`,
    storyId
  };
}

/**
 * 保存汤（原样保存，不优化）
 * @param {string} groupId - 群组ID
 * @param {string} content - 用户输入的内容
 * @returns {object} - { message }
 */
function saveStory(groupId, content) {
  // 解析用户输入，期望格式：保存汤 [storyId] [汤底]
  const match = content.match(/^保存汤\s+(\w+)\s+(.+)$/s);

  if (!match) {
    return {
      message: '📝 请提供故事ID和汤底内容。\n\n格式：保存汤 [storyId] [汤底内容]\n例如：保存汤 custom_1234567890 男人打嗝了...'
    };
  }

  const [, storyId, 汤底] = match;

  // 读取故事文件
  const storyPath = path.join(__dirname, '..', 'stories', `${storyId}.json`);
  if (!fs.existsSync(storyPath)) {
    return { message: '找不到该故事，请检查故事ID。' };
  }

  const story = JSON.parse(fs.readFileSync(storyPath, 'utf-8'));

  // 只更新汤底，不提取关键词
  story.汤底 = 汤底;
  story.updatedAt = new Date().toISOString();

  // 保存
  fs.writeFileSync(storyPath, JSON.stringify(story, null, 2), 'utf-8');

  // 重新加载故事
  loadStories();

  return {
    message: `✅ 汤底已保存！\n\n汤面：${story.汤面}\n\n汤底：${汤底}\n\n⚠️ 注意：未提取关键词，猜答案需要完全匹配。\n如需系统优化，请发送：优化汤 ${storyId} ${汤底}`
  };
}

/**
 * 优化汤（提取关键词）
 * @param {string} groupId - 群组ID
 * @param {string} content - 用户输入的内容
 * @returns {object} - { message }
 */
function optimizeStory(groupId, content) {
  // 解析用户输入，期望格式：优化汤 [storyId] [汤底]
  const match = content.match(/^优化汤\s+(\w+)\s+(.+)$/s);

  if (!match) {
    return {
      message: '📝 请提供故事ID和汤底内容。\n\n格式：优化汤 [storyId] [汤底内容]\n例如：优化汤 custom_1234567890 男人打嗝了...'
    };
  }

  const [, storyId, 汤底] = match;

  // 读取故事文件
  const storyPath = path.join(__dirname, '..', 'stories', `${storyId}.json`);
  if (!fs.existsSync(storyPath)) {
    return { message: '找不到该故事，请检查故事ID。' };
  }

  const story = JSON.parse(fs.readFileSync(storyPath, 'utf-8'));

  // 更新故事
  story.汤底 = 汤底;
  story.关键词 = extractKeywords(汤底);
  story.updatedAt = new Date().toISOString();

  // 保存
  fs.writeFileSync(storyPath, JSON.stringify(story, null, 2), 'utf-8');

  // 重新加载故事
  loadStories();

  return {
    message: `✅ 汤已优化完成！\n\n汤面：${story.汤面}\n\n汤底：${汤底}\n\n关键词：${story.关键词.join('、')}\n\n现在可以发送"开始游戏"来玩这道题了！`
  };
}

/**
 * 提取关键词
 * @param {string} text - 文本
 * @returns {string[]} - 关键词数组
 */
function extractKeywords(text) {
  // 简单的关键词提取：按标点分割，取长度>1的词
  const words = text.split(/[，。？！、\s]+/).filter(w => w.length > 1);
  return [...new Set(words)].slice(0, 5);
}

/**
 * 查看汤库
 * @returns {object} - { message }
 */
function listStories() {
  if (stories.length === 0) {
    return { message: '📚 汤库为空，发送"创建汤"添加新故事。' };
  }

  // 按主题分组
  const grouped = {};
  stories.forEach(story => {
    const theme = story.theme || '其他';
    if (!grouped[theme]) grouped[theme] = [];
    grouped[theme].push(story);
  });

  let message = `📚 汤库（共 ${stories.length} 道）\n\n`;

  for (const [theme, storyList] of Object.entries(grouped)) {
    message += `【${theme}】\n`;
    storyList.forEach((story, i) => {
      const preview = story.汤面.substring(0, 20) + '...';
      const hasAnswer = story.汤底 !== '待填写' ? '✅' : '⏳';
      message += `${hasAnswer} ${story.id}: ${preview}\n`;
    });
    message += '\n';
  }

  message += '✅ 已有汤底 ⏳ 待填写\n\n发送"开始游戏"随机出题';

  return { message };
}

module.exports = {
  startGame,
  askQuestion,
  checkAnswer,
  revealAnswer,
  nextStory,
  getHint,
  createStory,
  saveStory,
  optimizeStory,
  listStories,
  loadStories
};
