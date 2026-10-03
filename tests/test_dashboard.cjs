// Dependency-free DOM harness: exercises page logic, not browser layout/rendering.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'../samples/DemoReport/Report.html'),'utf8');
const elements=new Map(),nav=[];let downloads=0;
class Element{
 constructor(id,tag='div'){this.id=id;this.tag=tag;this.value='';this.textContent='';this.children=[];this.classList={toggle(){}};this._html=''}
 set innerHTML(text){this._html=text;for(const m of text.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g)){if(!elements.has(m[2]))elements.set(m[2],new Element(m[2],m[1]));}if(elements.has('severity'))elements.get('severity').value='all';if(elements.has('status'))elements.get('status').value='Investigating'}
 get innerHTML(){return this._html}
 appendChild(e){this.children.push(e);if(this.id==='nav')nav.push(e);if(this.tag==='select'&&!this.value)this.value=e.value}
 click(){if(this.tag==='a')downloads++;else if(this.onclick)this.onclick()}
}
for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"[^>]*>/g))elements.set(m[2],new Element(m[2],m[1]));
elements.get('payload').textContent=html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const context={document:{getElementById:id=>elements.get(id),createElement:tag=>new Element('',tag),querySelectorAll:s=>s==='nav button'?nav:['overview','findings','evidence','troubleshoot','ticket','repairs'].map(id=>elements.get(id))},window:{print(){}},URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}},Blob,JSON,setTimeout:fn=>fn(),console};
const script=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];vm.runInNewContext(script,context);
assert(elements.get('banner').textContent.includes('DEMO DATA'));
assert.equal(nav.length,6);nav[2].click();assert.equal(elements.get('title').textContent,'Evidence explorer');
elements.get('search').value='DNS';elements.get('search').oninput();assert(elements.get('findinglist').innerHTML.includes('DNS probe failed'));
elements.get('section').value='bitlocker';elements.get('section').onchange();assert(elements.get('sectionstatus').textContent.includes('unavailable'));
elements.get('workflow').value='USB / driver error';elements.get('workflow').onchange();assert(elements.get('steps').innerHTML.includes('code 43'));
elements.get('status').value='Resolved';elements.get('ticketexport').click();assert(elements.get('ticketerror').textContent.includes('verification'));assert.equal(downloads,0);
elements.get('verify').value='User confirmed access after a fresh test.';elements.get('ticketexport').click();assert.equal(downloads,1);
elements.get('json').click();assert.equal(downloads,2);
console.log('Dashboard DOM harness passed: initialization, navigation, filtering, unavailable evidence, workflow selection, resolved-ticket guard and downloads.');
