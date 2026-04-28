import Home from "../views/Home.vue";
import Dashboard from "../views/Dashboard.vue";
import Account from "../views/Account.vue";
import Product from "../views/Product.vue";
import Session from "../views/Session.vue";
import UserSettings from "../views/UserSettings.vue";
import Login from "../views/Login.vue";
import Register from "../views/Register.vue";

// 主布局路由（包含 header + sidebar）
const layoutRoutes = {
  path: "/",
  component: Home,
  children: [
    { path: "", name: "Dashboard", component: Dashboard },
    { path: "accounts", name: "账号管理", component: Account },
    { path: "sessions", name: "会话管理", component: Session },
    { path: "products", name: "商品管理", component: Product },
    { path: "settings", name: "用户中心", component: UserSettings },
  ],
};

// 独立页面（无布局）
const publicRoutes = [
  { path: "/login", name: "Login", component: Login },
  { path: "/register", name: "Register", component: Register },
];

export const routes = [layoutRoutes, ...publicRoutes];
