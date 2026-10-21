import {PGlite} from '@electric-sql/pglite';
import {PGLiteSocketServer} from '@electric-sql/pglite-socket';
const db=await PGlite.create();
console.log(JSON.stringify(await db.query('select version(),current_setting(\'server_version_num\') as server_version_num')));
const server=new PGLiteSocketServer({db,host:'127.0.0.1',port:55432});
await server.start();
console.log('ISOLATED_WASM_POSTGRES_READY 127.0.0.1:55432');
process.on('SIGTERM',async()=>{await server.stop();await db.close();process.exit(0)});
