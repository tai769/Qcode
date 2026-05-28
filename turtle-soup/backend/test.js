const { handleMessage } = require('./handler');

// 测试用例
const groupId = 'test_group_001';
const userId = 'test_user_001';

console.log('=== 海龟汤游戏测试 ===\n');

// 测试帮助命令
console.log('1. 测试帮助命令:');
console.log(handleMessage(groupId, userId, '帮助'));
console.log('\n---\n');

// 测试开始游戏
console.log('2. 测试开始游戏:');
console.log(handleMessage(groupId, userId, '开始游戏'));
console.log('\n---\n');

// 测试提问
console.log('3. 测试提问:');
console.log(handleMessage(groupId, userId, '这个人是死了吗？'));
console.log('\n---\n');

// 测试提示
console.log('4. 测试提示:');
console.log(handleMessage(groupId, userId, '提示'));
console.log('\n---\n');

// 测试猜答案
console.log('5. 测试猜答案:');
console.log(handleMessage(groupId, userId, '打嗝了'));
console.log('\n---\n');

// 测试下一题
console.log('6. 测试下一题:');
console.log(handleMessage(groupId, userId, '下一题'));
console.log('\n---\n');

// 测试公布答案
console.log('7. 测试公布答案:');
console.log(handleMessage(groupId, userId, '公布答案'));
console.log('\n---\n');

console.log('=== 测试完成 ===');
