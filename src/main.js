import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from "vue-router";
import App from './App.vue'
import scriptPage from './components/scriptPage.vue';
import setupView from './components/setupView.vue';

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: setupView, props: true },
    { path: "/scriptPage", component: scriptPage},
  ],
});

createApp(App).use(router).mount('#app')