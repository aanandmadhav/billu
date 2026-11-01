// Logic-only check of the generated chai app, without opening or controlling a browser.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const root=path.resolve('sandbox');
const file=path.resolve(process.argv[2]||'');
if(!file.startsWith(root+path.sep))throw new Error('Only sandbox app files can be checked');
const html=fs.readFileSync(file,'utf8');
const nodes=new Map([...html.matchAll(/\bid=["']([^"']+)["']/g)].map(match=>[match[1],{textContent:'0',value:0,listeners:{},attributes:{},setAttribute(name,value){this.attributes[name]=value},addEventListener(name,fn){this.listeners[name]=fn;}}]));
function node(id){return nodes.get(id)||null;}
const document={querySelector:selector=>node(selector.replace(/^#/,'')),getElementById:node,addEventListener(){}};
const context=vm.createContext({document,console,localStorage:{getItem(){return '0'},setItem(){}}});
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi))vm.runInContext(match[1],context,{timeout:1000});
function click(id){const target=node(id);const fn=target.listeners.click||target.onclick;if(!fn)throw new Error(`${id} has no handler`);fn();}
const plus=['plus','increase','increment'].find(id=>nodes.has(id));
const minus=['minus','decrease','decrement'].find(id=>nodes.has(id));
if(!plus||!minus)throw new Error('Counter controls were not found in the actual HTML');
click(plus);click(plus);if(Number(node('count').textContent)!==2)throw new Error('Plus failed');
click(minus);if(Number(node('count').textContent)!==1)throw new Error('Minus failed');
click('reset');if(Number(node('count').textContent)!==0)throw new Error('Reset failed');
click(minus);if(Number(node('count').textContent)!==0)throw new Error('Counter went below zero');
console.log('Generated app logic: plus, minus, reset and lower bound passed.');
