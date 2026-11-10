// 교육·시연용 가상 가격과 성능 지수. 실구매 및 실측 벤치마크가 아님.
const item=(id,category,name,price,spec)=>({id,category,name,price,inStock:true,verified:true,source:'시연용 데이터',observedAt:'2026-11-04T00:00:00+09:00',...spec});
export const categories=['cpu','board','ram','gpu','ssd','psu','case','cooler','os'];
export const labels={cpu:'프로세서',board:'메인보드',ram:'메모리',gpu:'그래픽카드',ssd:'스토리지',psu:'파워서플라이',case:'케이스',cooler:'CPU 쿨러',os:'운영체제'};
export const catalog=[
item('c1','cpu','AMD Ryzen 5 7500F',170000,{socket:'AM5',watts:65,score:66,igpu:false}),
item('c2','cpu','AMD Ryzen 5 9600X',280000,{socket:'AM5',watts:65,score:83,igpu:true}),
item('c3','cpu','AMD Ryzen 7 9700X',420000,{socket:'AM5',watts:65,score:98,igpu:true}),
item('c4','cpu','AMD Ryzen 5 8600G',210000,{socket:'AM5',watts:65,score:65,igpu:true}),
item('b1','board','MSI PRO B650M-A WIFI',180000,{socket:'AM5',ddr:5,form:'mATX',bios:['c1','c2','c3','c4'],slots:4,maxRam:128,m2:2,wifi:true}),
item('b2','board','ASRock B650M Pro RS WiFi',220000,{socket:'AM5',ddr:5,form:'mATX',bios:['c1','c2','c3','c4'],slots:4,maxRam:128,m2:3,wifi:true,color:'white'}),
item('r1','ram','DDR5-5600 16GB · 8GB × 2',180000,{ddr:5,capacity:16,sticks:2}),
item('r2','ram','DDR5-5600 32GB · 16GB × 2',360000,{ddr:5,capacity:32,sticks:2}),
item('r3','ram','DDR5-5600 64GB · 32GB × 2',680000,{ddr:5,capacity:64,sticks:2}),
item('g0','gpu','CPU 내장 그래픽 사용',0,{virtual:true,watts:0,score:12,vram:0,length:0,thickness:0,connector:'none',minPsu:0}),
item('g1','gpu','GeForce RTX 5060 8GB',420000,{watts:145,score:61,vram:8,length:240,thickness:2,connector:'8pin',minPsu:550}),
item('g2','gpu','GeForce RTX 5060 Ti 16GB',550000,{watts:180,score:76,vram:16,length:280,thickness:2.5,connector:'8pin',minPsu:600}),
item('g3','gpu','GeForce RTX 5070 12GB',750000,{watts:250,score:95,vram:12,length:304,thickness:3,connector:'12v2x6',minPsu:650}),
item('g4','gpu','GeForce RTX 5070 Ti 16GB',1050000,{watts:300,score:115,vram:16,length:330,thickness:3,connector:'12v2x6',minPsu:750}),
item('s1','ssd','NVMe PCIe 4.0 · 1TB',120000,{m2:1,capacity:1000}),
item('s2','ssd','NVMe PCIe 4.0 · 2TB',210000,{m2:1,capacity:2000}),
item('p1','psu','650W · 80 PLUS Bronze',70000,{capacity:650,connectors:['8pin'],score:65}),
item('p2','psu','750W · 80 PLUS Gold · ATX 3.1',110000,{capacity:750,connectors:['8pin','12v2x6'],score:90}),
item('p3','psu','850W · 80 PLUS Gold · ATX 3.1',140000,{capacity:850,connectors:['8pin','12v2x6'],score:95}),
item('k1','case','에어플로우 미니타워 · 블랙',50000,{forms:['mATX'],gpuLength:320,gpuThickness:3,coolerHeight:160,color:'black'}),
item('k2','case','에어플로우 미들타워 · 화이트',60000,{forms:['ATX','mATX'],gpuLength:360,gpuThickness:4,coolerHeight:170,color:'white'}),
item('f1','cooler','싱글타워 공랭 쿨러',25000,{sockets:['AM5'],height:150,coolingWatts:120}),
item('f2','cooler','듀얼타워 공랭 · 화이트',50000,{sockets:['AM5'],height:158,coolingWatts:200,color:'white'}),
item('o0','os','OS 미포함',0,{virtual:true}),item('o1','os','Windows 11 Home · 정품',170000,{})];
