import { createRouter, createWebHistory } from "vue-router";
import { routes } from "./routes.js";
import { tokenManager } from "../api.js";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// 路由守卫：检查是否已登录
router.beforeEach((to, from, next) => {
  // 公开路由
  const publicRoutes = ["/login", "/register"];
  if (publicRoutes.includes(to.path)) {
    // 已登录用户访问登录/注册页，跳转到首页
    if (tokenManager.getToken()) {
      next("/");
    } else {
      next();
    }
    return;
  }

  // 其他路由需要登录
  if (!tokenManager.getToken()) {
    next("/login");
    return;
  }

  next();
});

export default router;
