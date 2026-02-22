import './tailwind.css'
import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from "vue-router";

import { library } from '@fortawesome/fontawesome-svg-core'
import { faPlay, faPause, faCircleInfo, faFeather } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

import App from './App.vue'
import scriptView from './components/scriptView.vue';
import setupView from './components/setupView.vue';
import Dashboard from './components/Dashboard.vue';

library.add(faPlay, faPause, faCircleInfo, faFeather)

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: setupView, props: true },
    { path: "/scriptView", component: scriptView, props: true },
    { path: "/dashboard", component: Dashboard, props: true },
  ],
});

createApp(App)
  .use(router)
  .component('font-awesome-icon', FontAwesomeIcon)
  .mount('#app')
