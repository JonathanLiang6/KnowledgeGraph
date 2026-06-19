import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/HomePage.vue'),
  },
  {
    path: '/kb/:id',
    component: () => import('../layouts/KBLayout.vue'),
    children: [
      {
        path: '',
        redirect: (to) => ({ name: 'KBGraph', params: { id: to.params.id } }),
      },
      {
        path: 'documents',
        name: 'KBDocuments',
        component: () => import('../views/Documents.vue'),
        meta: { title: '文档管理 - KnowledgeGraph' },
      },
      {
        path: 'graph',
        name: 'KBGraph',
        component: () => import('../views/GraphWorkspace.vue'),
        meta: { title: '知识图谱 - KnowledgeGraph' },
      },
      {
        path: 'chat',
        name: 'KBChat',
        component: () => import('../views/ChatStudio.vue'),
        meta: { title: '智能问答 - KnowledgeGraph' },
      },
    ],
  },
  // 旧路由重定向到首页
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
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
