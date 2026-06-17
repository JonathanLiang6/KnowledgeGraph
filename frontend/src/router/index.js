import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../layouts/AdminLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表盘 - KnowledgeGraph' },
      },
      {
        path: 'knowledge-bases',
        name: 'KnowledgeBases',
        component: () => import('../views/KnowledgeBases.vue'),
        meta: { title: '知识库管理 - KnowledgeGraph' },
      },
      {
        path: 'chat',
        name: 'ChatStudio',
        component: () => import('../views/ChatStudio.vue'),
        meta: { title: 'Chat Studio - KnowledgeGraph' },
      },
      {
        path: 'graph',
        name: 'GraphWorkspace',
        component: () => import('../views/GraphWorkspace.vue'),
        meta: { title: '图谱工作台 - KnowledgeGraph' },
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('../views/Documents.vue'),
        meta: { title: '文档管理 - KnowledgeGraph' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/Settings.vue'),
        meta: { title: '系统设置 - KnowledgeGraph' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta?.title) {
    document.title = to.meta.title
  }
})

export default router
