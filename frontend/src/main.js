import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from "vue-router";
import App from './App.vue'
import scriptView from './components/scriptView.vue';
import setupView from './components/setupView.vue';
import Dashboard from './components/Dashboard.vue';

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: setupView, props: true },
    { path: "/scriptView", component: scriptView, props: true },
    { path: "/dashboard", component: Dashboard, props: true },
  ],
});

createApp(App).use(router).mount('#app')