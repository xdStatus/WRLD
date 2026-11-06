// Run: node cloud/test-worker.mjs
import assert from 'node:assert/strict';
import worker from './worker.js';
let row=null;
const db={
  prepare(sql){
    const args=[];
    return {
      bind(...values){args.push(...values);return this},
      async first(){return row&&{revision:row.revision,payload:row.payload}},
      async run(){
        if(sql.startsWith('UPDATE')){
          if(!row||row.revision!==args[1])return {meta:{changes:0}};
          row={revision:row.revision+1,payload:args[0]};
          return {meta:{changes:1}};
        }
        if(sql.startsWith('INSERT')){
          if(row)return {meta:{changes:0}};
          row={revision:1,payload:args[0]};
          return {meta:{changes:1}};
        }
        throw Error('Unexpected SQL');
      }
    };
  }
};
const env={WRLD_ACCESS_TOKEN:'test-secret',MUSIC_BUCKET:{async list(){return {objects:[],truncated:false}}},SYNC_DB:db};
const req=(method,path,body,token='test-secret')=>new Request('https://wrld.test'+path,{method,headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
const call=async(method,path,body,token)=>{const response=await worker.fetch(req(method,path,body,token),env);return {status:response.status,body:await response.json()}};
assert.equal((await call('GET','/api/sync',null,'wrong')).status,401);
assert.deepEqual((await call('GET','/api/sync')).body,{revision:0,data:{liked:[],playlists:[],history:[],listeningMs:0}});
const data={liked:['r2_a'],playlists:[{id:'p1',name:'Favorites',ids:['r2_a']}],history:['r2_a'],listeningMs:500};
assert.equal((await call('PUT','/api/sync',{revision:0,data})).status,200);
assert.deepEqual((await call('GET','/api/sync')).body,{revision:1,data});
assert.equal((await call('PUT','/api/sync',{revision:0,data})).status,409);
assert.equal((await call('PUT','/api/sync',{revision:1,data:{...data,liked:['r2_b']}})).status,200);
assert.equal((await call('PUT','/api/sync',{revision:2,data:{...data,history:['bad'],listeningMs:-1}})).status,400);
assert.equal((await call('GET','/api/tracks')).status,200);
console.log('WRLD Cloud sync API checks passed');
