'use strict';
const assert=require('assert'), path=require('path');
const G=require(path.join(__dirname,'../src/annotation/prebox/geometry.js'));
for (const zoom of [.5,2]) {
  const rect={left:100,top:50,width:1000*zoom,height:1500*zoom};
  assert.deepStrictEqual(G.point(100+200*zoom,50+300*zoom,rect,1000,1500),[200,300]);
  const start=G.point(100+200*zoom,50+300*zoom,rect,1000,1500);
  const end=G.point(100+240*zoom,50+320*zoom,rect,1000,1500);
  assert.deepStrictEqual(G.move([200,300,400,500],end[0]-start[0],end[1]-start[1],1000,1500),[240,320,440,520]);
  assert.deepStrictEqual(G.resize([200,300,400,500],'se',G.point(100+450*zoom,50+550*zoom,rect,1000,1500),1000,1500),[200,300,450,550]);
}
assert.deepStrictEqual(G.normalize([400,500],[200,300],1000,1500),[200,300,400,500]);
assert.deepStrictEqual(G.normalize([-20,-10],[1100,1700],1000,1500),[0,0,1000,1500]);
assert.strictEqual(G.normalize([20,20],[21,30],1000,1500),null);
assert.deepStrictEqual(G.move([200,300,400,500],-999,-999,1000,1500),[0,0,200,200]);
assert.deepStrictEqual(G.move([200,300,400,500],9999,9999,1000,1500),[800,1300,1000,1500]);
assert.deepStrictEqual(G.resize([200,300,400,500],'nw',[450,550],1000,1500),[400,500,450,550]);
assert.deepStrictEqual(G.resize([200,300,400,500],'ne',[450,250],1000,1500),[200,250,450,500]);
assert.deepStrictEqual(G.resize([200,300,400,500],'sw',[150,550],1000,1500),[150,300,400,550]);
assert.throws(()=>G.point(0,0,{left:0,top:0,width:0,height:0},100,100));
console.log('Prebox coordinate regressions passed: 0.5x/2x mapping, move, resize, reverse, bounds, minimum size.');
