import {recommend} from './engine.mjs';
self.onmessage=({data})=>{try{self.postMessage({result:recommend(data.req,data.settings,data.catalog)});}catch(error){self.postMessage({error:error.message});}};
