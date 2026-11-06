// WRLD Cloud Worker: R2 music + D1 collections synchronization.
// Bind MUSIC_BUCKET (R2), SYNC_DB (D1), and WRLD_ACCESS_TOKEN (secret).
const AUDIO_TYPES = {mp3:"audio/mpeg",m4a:"audio/mp4",mp4:"audio/mp4",flac:"audio/flac",wav:"audio/wav",ogg:"audio/ogg",opus:"audio/ogg",aac:"audio/aac"};
const json = (data,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
const error=(message,status)=>json({message},status);
const EMPTY={liked:[],playlists:[],history:[],listeningMs:0};
function validate(value){
  if(!value||typeof value!=="object"||Array.isArray(value))return null;
  const ids=v=>Array.isArray(v)&&v.length<=20000&&v.every(x=>typeof x==="string"&&x.length>0&&x.length<=2048);
  if(!ids(value.liked)||!ids(value.history)||value.history.length>500)return null;
  if(!Array.isArray(value.playlists)||value.playlists.length>500)return null;
  for(const p of value.playlists){
    if(!p||typeof p.id!=="string"||p.id.length>128||!p.id||typeof p.name!=="string"||p.name.length>200||!ids(p.ids))return null;
  }
  if(!Number.isSafeInteger(value.listeningMs)||value.listeningMs<0)return null;
  return {liked:[...new Set(value.liked)],playlists:value.playlists.map(p=>({id:p.id,name:p.name,ids:[...new Set(p.ids)]})),history:value.history.slice(0,500),listeningMs:value.listeningMs};
}
export default {
  async fetch(request,env){
    if(!env.WRLD_ACCESS_TOKEN||!env.MUSIC_BUCKET)return error("Cloud is not configured",503);
    if(request.headers.get("Authorization")!==`Bearer ${env.WRLD_ACCESS_TOKEN}`)return error("Unauthorized",401);
    const url=new URL(request.url);
    const method=request.method;
    if(url.pathname==="/api/sync"){
      if(!env.SYNC_DB)return error("Sync database is not configured",503);
      if(method!=="GET"&&method!=="PUT")return error("Method not allowed",405);
      try{
        if(method==="GET"){
          const row=await env.SYNC_DB.prepare("SELECT revision, payload FROM sync_state WHERE id = 1").first();
          return json({revision:row?.revision??0,data:row?JSON.parse(row.payload):EMPTY});
        }
        if(Number(request.headers.get("Content-Length")||0)>2_000_000)return error("Sync payload too large",413);
        const raw=await request.text();
        if(raw.length>2_000_000)return error("Sync payload too large",413);
        let incoming;
        try{incoming=JSON.parse(raw)}catch{return error("Invalid JSON",400)}
        const data=validate(incoming?.data);
        if(!data||!Number.isSafeInteger(incoming.revision)||incoming.revision<0)return error("Invalid sync data or revision",400);
        // Optimistic concurrency: never overwrite a newer revision.
        const result=await env.SYNC_DB.prepare(
          "UPDATE sync_state SET revision = revision + 1, payload = ? WHERE id = 1 AND revision = ?"
        ).bind(JSON.stringify(data),incoming.revision).run();
        if(result.meta.changes===1)return json({revision:incoming.revision+1,data});
        if(incoming.revision===0){
          const inserted=await env.SYNC_DB.prepare(
            "INSERT OR IGNORE INTO sync_state (id,revision,payload) VALUES (1,1,?)"
          ).bind(JSON.stringify(data)).run();
          if(inserted.meta.changes===1)return json({revision:1,data});
        }
        const current=await env.SYNC_DB.prepare("SELECT revision,payload FROM sync_state WHERE id = 1").first();
        return json({message:"Sync conflict: refresh and merge before retrying",revision:current?.revision??0,data:current?JSON.parse(current.payload):EMPTY},409);
      }catch{return error("Sync database request failed",503)}
    }
    if(method!=="GET"&&method!=="HEAD")return error("Method not allowed",405);
    if(url.pathname==="/api/tracks"){
      const songs=[];let cursor;
      do{
        const page=await env.MUSIC_BUCKET.list({limit:1000,...(cursor?{cursor}:{})});
        for(const item of page.objects){
          const extension=item.key.split(".").pop().toLowerCase();
          if(!AUDIO_TYPES[extension])continue;
          songs.push({id:item.key,title:item.key.split("/").pop().replace(/\.[^.]+$/,""),artist:"Juice WRLD",size:item.size,modified:item.uploaded,streamPath:"/api/stream/"+encodeURIComponent(item.key)});
        }
        cursor=page.truncated?page.cursor:undefined;
      }while(cursor&&songs.length<10000);
      return json({count:songs.length,tracks:songs});
    }
    if(url.pathname.startsWith("/api/stream/")){
      let key;
      try{key=decodeURIComponent(url.pathname.slice("/api/stream/".length))}catch{return error("Invalid song",400)}
      const extension=key.split(".").pop().toLowerCase();
      if(!AUDIO_TYPES[extension])return error("Unsupported audio type",400);
      const info=await env.MUSIC_BUCKET.head(key);
      if(!info)return error("Song not found",404);
      const size=info.size,range=request.headers.get("Range");
      let start=0,end=size-1,partial=false;
      if(range){
        const match=/^bytes=(\d*)-(\d*)$/.exec(range);
        if(!match||(!match[1]&&!match[2]))return new Response(null,{status:416,headers:{"Content-Range":`bytes */${size}`}});
        partial=true;
        if(match[1]){start=Number(match[1]);end=match[2]?Math.min(Number(match[2]),size-1):size-1}
        else start=Math.max(0,size-Number(match[2]));
        if(start>end||start>=size)return new Response(null,{status:416,headers:{"Content-Range":`bytes */${size}`}});
      }
      const length=end-start+1;
      const song=method==="HEAD"?null:await env.MUSIC_BUCKET.get(key,{range:{offset:start,length}});
      if(method!=="HEAD"&&!song)return error("Song not found",404);
      const headers=new Headers({"Content-Type":AUDIO_TYPES[extension],"Accept-Ranges":"bytes","Content-Length":String(length),"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"});
      if(partial)headers.set("Content-Range",`bytes ${start}-${end}/${size}`);
      return new Response(song?.body??null,{status:partial?206:200,headers});
    }
    return error("Not found",404);
  }
};
