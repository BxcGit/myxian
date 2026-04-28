import axios from "axios";

// 全局 Axios 实例，统一配置 baseURL
const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

// 请求拦截器：添加 JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理错误
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      // 401 未授权，跳转到登录页
      if (error.response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user_id");
        localStorage.removeItem("username");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// 认证 API
export const authApi = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
};

// 咸鱼账号 API
export const xianyuAccountApi = {
  list: () => api.get("/xianyu-accounts/"),
  get: (id) => api.get(`/xianyu-accounts/${id}`),
  create: (data) => api.post("/xianyu-accounts/", data),
  update: (id, data) => api.put(`/xianyu-accounts/${id}`, data),
  delete: (id) => api.delete(`/xianyu-accounts/${id}`),
  start: (id) => api.post(`/xianyu-accounts/${id}/start`),
  stop: (id) => api.post(`/xianyu-accounts/${id}/stop`),
};

// 商品 API
export const productApi = {
  list: (xianyu_account_id) => api.get("/products/", { params: { xianyu_account_id } }),
  get: (id) => api.get(`/products/${id}`),
  updatePrompt: (id, data) => api.put(`/products/${id}/prompt`, data),
  sync: (data) => api.post("/products/sync", data),
  delete: (id) => api.delete(`/products/${id}`),
};

// 会话 API
export const sessionApi = {
  list: (xianyu_account_id) => api.get("/sessions/", { params: { xianyu_account_id } }),
  get: (id) => api.get(`/sessions/${id}`),
  getMessages: (session_id, params) => api.get(`/sessions/${session_id}/messages`, { params }),
  getRecentMessages: (limit) => api.get("/sessions/messages/recent", { params: { limit } }),
  getLastMessage: (session_id) => api.get(`/sessions/${session_id}/last-message`),
  delete: (id) => api.delete(`/sessions/${id}`),
};

// 消息 API
export const messageApi = {
  create: (data) => api.post("/sessions/messages", data),
};

// 用户设置 API
export const userSettingsApi = {
  get: (username) => api.get(`/auth/settings/${username}`),
  update: (username, data) => api.put(`/auth/settings/${username}`, data),
};

// Token 管理
export const tokenManager = {
  getToken: () => localStorage.getItem("access_token"),
  setToken: (token) => localStorage.setItem("access_token", token),
  getUserId: () => localStorage.getItem("user_id"),
  setUserId: (id) => localStorage.setItem("user_id", id),
  getUsername: () => localStorage.getItem("username"),
  setUsername: (name) => localStorage.setItem("username", name),
  clear: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("username");
  },
};

export default api;
