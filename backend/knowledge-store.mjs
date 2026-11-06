import {measurementIssue} from '../src/workload-evidence.mjs';
import {createHash} from 'node:crypto';
import {normalizeProduct,typeParents,requiredFacts,ontologyVersion} from '../src/product-ontology.mjs';
export function createKnowledgeStore(db){
 db.exec(`CREATE TABLE IF NOT EXISTS knowledge_products(id TEXT PRIMARY KEY,type TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS knowledge_facts(product_id TEXT NOT NULL,predicate TEXT NOT NULL,value TEXT NOT NULL,evidence TEXT NOT NULL,PRIMARY KEY(product_id,predicate));
 CREATE TABLE IF NOT EXISTS knowledge_relations(subject TEXT NOT NULL,predicate TEXT NOT NULL,object TEXT NOT NULL,conditions TEXT NOT NULL,evidence TEXT NOT NULL,PRIMARY KEY(subject,predicate,object,conditions));
 CREATE INDEX IF NOT EXISTS knowledge_relation_target ON knowledge_relations(predicate,object);
 CREATE TABLE IF NOT EXISTS knowledge_measurements(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS knowledge_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);`);
 return {
 measurements(){return db.prepare('SELECT payload FROM knowledge_measurements ORDER BY id').all().map(row=>JSON.parse(row.payload))},
 putMeasurement(value){const issue=measurementIssue(value);if(issue)throw new Error(issue);if(value.reviewed!==true||!value.reviewedBy||!Number.isFinite(Date.parse(value.reviewedAt)))throw new Error('실측 원문의 담당자 검수 기록이 필요합니다.');const payload=JSON.stringify(value);const id=createHash('sha256').update(payload).digest('hex');db.prepare('INSERT OR IGNORE INTO knowledge_measurements VALUES(?,?)').run(id,payload);return id},
 sync(snapshot){const version=`v${ontologyVersion}:${snapshot.catalogVersion||snapshot.generatedAt}`;if(db.prepare("SELECT value FROM knowledge_meta WHERE key='version'").get()?.value===version)return;
 const product=db.prepare('INSERT INTO knowledge_products VALUES(?,?,?,?)');const fact=db.prepare('INSERT INTO knowledge_facts VALUES(?,?,?,?)');const edge=db.prepare('INSERT OR IGNORE INTO knowledge_relations VALUES(?,?,?,?,?)');
 db.exec('BEGIN IMMEDIATE');try{db.exec('DELETE FROM knowledge_products;DELETE FROM knowledge_facts;DELETE FROM knowledge_relations;');for(const part of snapshot.parts){const normalized=normalizeProduct(part);product.run(part.id,normalized.type,normalized.status,JSON.stringify(normalized));for(const f of normalized.facts)fact.run(part.id,f.predicate,JSON.stringify(f.value),JSON.stringify(f.evidence));for(const r of normalized.relations)edge.run(r.subject,r.predicate,String(r.object),JSON.stringify(r.conditions||{}),JSON.stringify(r.evidence));edge.run(part.id,'isA',normalized.type,'{}',JSON.stringify({status:'classified',method:'product-ontology-v1'}));}db.prepare("INSERT INTO knowledge_meta VALUES('version',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value").run(version);db.exec('COMMIT')}catch(error){db.exec('ROLLBACK');throw error}},
 product(id){const row=db.prepare('SELECT payload FROM knowledge_products WHERE id=?').get(id);return row?JSON.parse(row.payload):null},
 summary(){return {schema:{typeParents,requiredFacts},version:db.prepare("SELECT value FROM knowledge_meta WHERE key='version'").get()?.value,types:db.prepare('SELECT type,status,count(*) AS count FROM knowledge_products GROUP BY type,status').all(),relations:db.prepare('SELECT count(*) AS count FROM knowledge_relations').get().count}},
 };
}
