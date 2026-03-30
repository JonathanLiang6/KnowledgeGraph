import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/Home.vue'),
      meta: { title: '知识图谱系统' }
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('../views/Chat.vue'),
      meta: { title: '智能问答' }
    },
    {
      path: '/graph',
      name: 'graph',
      component: () => import('../views/Graph.vue'),
      meta: { title: '图谱可视化' }
    },
    {
      path: '/documents',
      name: 'documents',
      component: () => import('../views/Documents.vue'),
      meta: { title: '文档管理' }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/Settings.vue'),
      meta: { title: '系统设置' }
    }
  ]
})

// 全局前置守卫，设置页面标题
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || '知识图谱系统'
  next()
})

export default router
