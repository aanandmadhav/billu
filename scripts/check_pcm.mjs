import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync('catbot/ui/pcm-worklet.js','utf8');
for(const rate of [44100,48000]){
 let Processor;
 const messages=[];
 class Base{constructor(){this.port={postMessage:message=>messages.push(message),onmessage:null};}}
 vm.runInNewContext(source,{sampleRate:rate,AudioWorkletProcessor:Base,registerProcessor:(name,type)=>{Processor=type;},Int16Array,Math});
 const processor=new Processor();
 const total=rate/10;
 for(let offset=0;offset<total;offset+=128){const samples=new Float32Array(Math.min(128,total-offset)).fill(.5);processor.process([[samples]]);}
 if(messages.length!==1||messages[0].pcm.byteLength!==3200)throw new Error(`Wrong frame size at ${rate} Hz`);
 const samples=new Int16Array(messages[0].pcm);
 if(samples.some(value=>Math.abs(value-16383)>1))throw new Error(`Resampling changed a constant signal at ${rate} Hz`);
 processor.process([[new Float32Array(128).fill(.2)]]);processor.port.onmessage({data:{type:'flush'}});
 if(!messages.at(-1).final||messages.at(-1).pcm.byteLength!==3200)throw new Error('Final frame was not zero-padded to 100ms');
 console.log(`${rate} Hz -> 16 kHz: 100ms int16 frame, amplitude and final flush passed.`);
}
