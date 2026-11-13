import {defineConfig} from 'vite';
// Match the course backend's default port; override when running a separate local instance.
export default defineConfig({server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:{'/api':process.env.RAG_API_TARGET||'http://127.0.0.1:8000'}}});
