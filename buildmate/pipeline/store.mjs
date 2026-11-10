import {DatabaseSync} from 'node:sqlite';
import {mkdirSync} from 'node:fs';
import {dirname} from 'node:path';
import {randomUUID} from 'node:crypto';
export class PipelineStore {
 constructor(path){mkdirSync(dirname(path),{recursive:true});this.db=new DatabaseSync(path);this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
 CREATE TABLE IF NOT EXISTS pipeline_jobs(id TEXT PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,summary TEXT);
 CREATE TABLE IF NOT EXISTS product_facts(id TEXT PRIMARY KEY,payload TEXT NOT NULL,updated_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS price_observations(id INTEGER PRIMARY KEY,part_id TEXT NOT NULL,amount INTEGER NOT NULL,source_url TEXT NOT NULL,observed_at TEXT NOT NULL,evidence_hash TEXT NOT NULL,payload TEXT NOT NULL,UNIQUE(part_id,source_url,observed_at));
 CREATE INDEX IF NOT EXISTS price_by_part_time ON price_observations(part_id,observed_at DESC);
 CREATE TABLE IF NOT EXISTS benchmark_observations(part_id TEXT PRIMARY KEY,payload TEXT NOT NULL,observed_at TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS review_queue(id TEXT PRIMARY KEY,kind TEXT NOT NULL,part_id TEXT,reason TEXT NOT NULL,evidence_hash TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT DEFAULT 'pending',UNIQUE(kind,part_id,evidence_hash));
 `);}
 start(){const id=randomUUID();this.db.prepare('INSERT INTO pipeline_jobs(id,started_at,status) VALUES(?,?,?)').run(id,new Date().toISOString(),'running');return id;}
 finish(id,status,summary){this.db.prepare('UPDATE pipeline_jobs SET finished_at=?,status=?,summary=? WHERE id=?').run(new Date().toISOString(),status,JSON.stringify(summary),id);}
 queue(kind,partId,reason,evidence,payload={}){this.db.prepare('INSERT OR IGNORE INTO review_queue(id,kind,part_id,reason,evidence_hash,payload,created_at) VALUES(?,?,?,?,?,?,?)').run(randomUUID(),kind,partId,reason,evidence,JSON.stringify(payload),new Date().toISOString());}
 latestPrice(id){const row=this.db.prepare('SELECT payload FROM price_observations WHERE part_id=? ORDER BY observed_at DESC,id DESC LIMIT 1').get(id);return row?JSON.parse(row.payload):null;}
 acceptProduct({part,price},{approvedPriceHashes=[]}={}){
  const prior=this.latestPrice(part.id);
  if(prior?.amount>0&&Math.abs(price.amount/prior.amount-1)>.3&&!approvedPriceHashes.includes(price.hash)){this.queue('price',part.id,'직전 가격 대비 30% 이상 변동: 담당자 확인 필요',price.hash,{prior,price});return false;}
  this.db.exec('BEGIN IMMEDIATE');try{
   this.db.prepare('INSERT INTO product_facts VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at').run(part.id,JSON.stringify(part),price.observedAt);
   this.db.prepare('INSERT OR IGNORE INTO price_observations(part_id,amount,source_url,observed_at,evidence_hash,payload) VALUES(?,?,?,?,?,?)').run(part.id,price.amount,price.sourceUrl,price.observedAt,price.hash,JSON.stringify(price));this.db.exec('COMMIT');
  }catch(e){this.db.exec('ROLLBACK');throw e;}return true;
 }
 putBenchmark(partId,value){this.db.prepare('INSERT INTO benchmark_observations VALUES(?,?,?) ON CONFLICT(part_id) DO UPDATE SET payload=excluded.payload,observed_at=excluded.observed_at').run(partId,JSON.stringify(value),value.observedAt);}
 products(){return this.db.prepare('SELECT id,payload FROM product_facts').all().map(r=>{const part=JSON.parse(r.payload);const b=this.db.prepare('SELECT payload FROM benchmark_observations WHERE part_id=?').get(r.id);return {...part,priceEvidence:this.latestPrice(r.id),benchmark:b?JSON.parse(b.payload):null};});}
 recordProduct(part){this.db.prepare('INSERT INTO product_facts VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated_at=excluded.updated_at').run(part.id,JSON.stringify(part),new Date().toISOString());}
 updatePopularity(id,popularity){const row=this.db.prepare('SELECT payload FROM product_facts WHERE id=?').get(id);if(row)this.db.prepare('UPDATE product_facts SET payload=? WHERE id=?').run(JSON.stringify({...JSON.parse(row.payload),popularity}),id);}
 updateListingDate(id,listingMonth,listingDateEvidence){const row=this.db.prepare('SELECT payload FROM product_facts WHERE id=?').get(id);if(!row)return;const part=JSON.parse(row.payload);this.db.prepare('UPDATE product_facts SET payload=? WHERE id=?').run(JSON.stringify({...part,listingMonth,listingDateEvidence}),id);}
 history(partId,days=90){return this.db.prepare('SELECT amount,observed_at,source_url FROM price_observations WHERE part_id=? AND observed_at>=? ORDER BY observed_at').all(partId,new Date(Date.now()-days*86400000).toISOString());}
 reviews(){return this.db.prepare("SELECT id,kind,part_id,reason,created_at FROM review_queue WHERE status='pending' ORDER BY created_at DESC LIMIT 200").all();}
 jobs(){return this.db.prepare('SELECT * FROM pipeline_jobs ORDER BY started_at DESC LIMIT 20').all().map(r=>({...r,summary:r.summary?JSON.parse(r.summary):null}));}
 close(){this.db.close();}
}
