import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  user: { username: string } | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  user: null,
  
  login: async (username: string, password: string) => {
    try {
      // 简化版登录：直接验证
      // 在实际应用中，这里应该调用后端 API
      if (username === 'admin' && password === 'admin') {
        set({ 
          isAuthenticated: true, 
          user: { username } 
        });
        // 保存到 localStorage
        localStorage.setItem('auth', JSON.stringify({ isAuthenticated: true, user: { username } }));
        return true;
      }
      return false;
    } catch (error) {
      console.error('登录错误:', error);
      return false;
    }
  },
  
  logout: () => {
    set({ 
      isAuthenticated: false, 
      user: null 
    });
    localStorage.removeItem('auth');
  },
}));

// 初始化：从 localStorage 恢复登录状态
const savedAuth = localStorage.getItem('auth');
if (savedAuth) {
  try {
    const auth = JSON.parse(savedAuth);
    useAuthStore.setState({ 
      isAuthenticated: auth.isAuthenticated, 
      user: auth.user 
    });
  } catch (e) {
    console.error('恢复登录状态失败:', e);
  }
}
