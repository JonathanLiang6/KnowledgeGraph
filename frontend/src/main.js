import { createApp } from 'vue'
// v4.1 (#73): Element Plus 模板组件经 unplugin 按需引入（见 vite.config.js），
// 此处仅保留 JS 调用组件（ElMessage/ElMessageBox）的样式与 v-loading 指令注册
import { ElLoading } from 'element-plus'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/theme-chalk/el-loading.css'
import App from './App.vue'
import router from './router'
import './styles/variables.scss'
import './styles/global.scss'
import './styles/transitions.scss'

const app = createApp(App)

app.use(router)
app.use(ElLoading)  // v-loading 指令（Documents.vue 使用）

app.mount('#app')
