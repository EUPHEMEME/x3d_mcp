const puppeteer=require('puppeteer'),path=require('path');
(async()=>{
 const arg=process.argv[2];
 const url=/^https?:/.test(arg)?arg:('file://'+path.resolve(arg));
 const b=await puppeteer.launch({headless:'new',args:['--use-gl=angle','--use-angle=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--no-sandbox','--enable-unsafe-swiftshader']});
 const p=await b.newPage(); await p.setViewport({width:1200,height:780});
 p.on('pageerror',e=>console.log('ERR',e.message));
 p.on('console',m=>{if(/error|fail|exception/i.test(m.text()))console.log('LOG',m.text());});
 await p.goto(url,{waitUntil:'networkidle2',timeout:60000});
 await new Promise(r=>setTimeout(r,parseInt(process.argv[4]||'5000')));
 await p.screenshot({path:path.resolve(process.argv[3])});
 console.log('wrote',process.argv[3]); await b.close();
})().catch(e=>{console.error('FATAL',e);process.exit(1);});
