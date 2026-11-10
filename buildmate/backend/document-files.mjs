// JSON persistence for pipeline state and configuration. Non-JSON assets stay on disk.
export * from 'node:fs/promises';
import * as fs from 'node:fs/promises';
import {DatabaseSync} from 'node:sqlite';
import {mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const handles=new Map();
const jsonPath=path=>typeof path==='string'&&/\.json(?:\.[\w.-]+)?$/.test(path);
function connection(path){const absolute=resolve(path);const directory=absolute.startsWith(root)?resolve(process.env.BUILDMATE_DATA_DIR||resolve(root,'backend/data')):dirname(absolute);mkdirSync(directory,{recursive:true});const location=resolve(directory,'documents.db');if(!handles.has(location)){const db=new DatabaseSync(location);db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=10000; CREATE TABLE IF NOT EXISTS documents(path TEXT PRIMARY KEY,payload TEXT NOT NULL,updated_at TEXT NOT NULL)');handles.set(location,db);}return handles.get(location);}
export async function readFile(path,options){if(!jsonPath(path))return fs.readFile(path,options);const db=connection(path),key=resolve(path);let row=db.prepare('SELECT payload FROM documents WHERE path=?').get(key);if(!row){const payload=await fs.readFile(path,'utf8');JSON.parse(payload);db.prepare('INSERT OR IGNORE INTO documents VALUES(?,?,?)').run(key,payload,new Date().toISOString());row=db.prepare('SELECT payload FROM documents WHERE path=?').get(key);}const encoding=typeof options==='string'?options:options?.encoding;return encoding?row.payload:Buffer.from(row.payload);}
export async function writeFile(path,data,options){if(!jsonPath(path))return fs.writeFile(path,data,options);const payload=String(data);JSON.parse(payload);connection(path).prepare('INSERT INTO documents VALUES(?,?,?) ON CONFLICT(path) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at').run(resolve(path),payload,new Date().toISOString());}
export async function rename(from,to){if(!jsonPath(from)||!jsonPath(to))return fs.rename(from,to);const data=await readFile(from,'utf8');await writeFile(to,data);connection(from).prepare('DELETE FROM documents WHERE path=?').run(resolve(from));}
export function storedDocument(path){const row=connection(path).prepare('SELECT payload FROM documents WHERE path=?').get(resolve(path));return row?JSON.parse(row.payload):null;}
export async function archiveAsset(path){const db=connection(path);db.exec('CREATE TABLE IF NOT EXISTS source_assets(name TEXT PRIMARY KEY,payload BLOB NOT NULL,updated_at TEXT NOT NULL)');db.prepare('INSERT INTO source_assets VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at').run(path,await fs.readFile(path),new Date().toISOString());}
