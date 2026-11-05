import { defineConfig } from 'vite';
export default defineConfig({server:{watch:{ignored:['**/public/data/**']},port:5588,strictPort:true,proxy:{'/api':'http://127.0.0.1:8000'}}});
