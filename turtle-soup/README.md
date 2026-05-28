# 海龟汤飞书群机器人

## 项目简介
海龟汤（情境猜谜）游戏逻辑模块，供飞书群机器人调用。

## 核心功能
- 开始游戏：随机出题，返回汤面
- 是非问答：玩家提问，返回"是/不是/不重要"
- 猜中判定：判断玩家是否猜中真相
- 公布答案：揭晓汤底
- 下一题：换一道新题

## 目录结构
```
turtle-soup/
├── backend/
│   ├── game.js       # 游戏核心逻辑
│   ├── handler.js    # 消息解析处理
│   └── index.js      # 入口文件
├── stories/          # 海龟汤故事数据
└── docs/
    └── PRD.md        # 产品需求文档
```

## 使用方式
```javascript
const { startGame, askQuestion, checkAnswer, revealAnswer } = require('./backend/game');

// 开始游戏
const result = startGame('group_123');
// => { storyId, 汤面 }

// 提问
const answer = askQuestion('group_123', '男人是渴了吗？');
// => { answer: '不是' }

// 猜答案
const correct = checkAnswer('group_123', '男人打嗝了');
// => { correct: true, 汤底 }
```