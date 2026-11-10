import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,writeFile,rm,realpath} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createServer} from 'vite';
import config from '../vite.config.js';
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
test('개발 서버는 소스 변경 시 전체 리로드를 보내며 수집 데이터 갱신은 제외한다',async()=>{
 const root=await realpath(await mkdtemp(join(tmpdir(),'drobot-hmr-')));let server;
 try{
 await mkdir(join(root,'src'));await mkdir(join(root,'public/data'),{recursive:true});
 await writeFile(join(root,'index.html'),'<script type="module" src="/src/main.js"></script>');
 await writeFile(join(root,'src/main.js'),'console.log("consultation");');await writeFile(join(root,'public/data/catalog.json'),'{}');
 server=await createServer({configFile:false,root,logLevel:'silent',server:{port:0,host:'127.0.0.1',watch:config.server.watch}});await server.listen();
 const messages=[];const send=server.ws.send.bind(server.ws);server.ws.send=(...args)=>{messages.push(args[0]);return send(...args);};
 await server.transformRequest('/src/main.js');await pause(150);
 await writeFile(join(root,'src/main.js'),'console.log("updated consultation");');
 for(let i=0;i<60&&!messages.some(m=>m.type==='full-reload');i++)await pause(25);
 assert.ok(messages.some(m=>m.type==='full-reload'&&m.triggeredBy===join(root,'src/main.js')));
 messages.length=0;await writeFile(join(root,'public/data/catalog.json'),'{"updated":true}');await pause(250);
 assert.equal(messages.filter(m=>m.type==='full-reload').length,0);
 }finally{await server?.close();await rm(root,{recursive:true,force:true});}
});
