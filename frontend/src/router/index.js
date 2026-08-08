import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Topology',
    component: () => import('../views/TopologyView.vue'),
    meta: { title: '个人知识库 · 第二大脑' },
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
      {
        path: 'coverage',
        name: 'KBCoverage',
        component: () => import('../views/CoveragePage.vue'),
        meta: { title: '知识体检 - KnowledgeGraph' },
      },
    ],
  },
  // 旧路由 /kb 重定向到首页
  {
    path: '/kb',
    redirect: '/',
  },
  // 旧 HomePage 路由保留但重定向
  {
    path: '/home',
    redirect: '/',
  },
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
