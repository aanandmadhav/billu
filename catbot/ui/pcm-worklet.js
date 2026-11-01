// Area-average resampling from the device sample rate to 16 kHz mono int16.
class BilluPCM extends AudioWorkletProcessor{
 constructor(){super();this.ratio=sampleRate/16000;this.area=0;this.filled=0;this.buffer=new Int16Array(1600);this.index=0;this.energy=0;this.port.onmessage=e=>{if(e.data.type==='flush'){this.flush(true);}};}
 flush(final=false){if(this.index){const pcm=this.buffer;const level=Math.min(1,Math.sqrt(this.energy/this.index)*3);this.port.postMessage({pcm:pcm.buffer,level,final},[pcm.buffer]);this.buffer=new Int16Array(1600);this.index=0;this.energy=0;}else if(final)this.port.postMessage({final:true});}
 process(inputs){const channels=inputs[0];if(!channels?.length)return true;const count=channels[0].length;for(let i=0;i<count;i++){let sample=0;for(const channel of channels)sample+=channel[i]||0;sample/=channels.length;let remaining=1;while(remaining>1e-9){const take=Math.min(remaining,this.ratio-this.filled);this.area+=sample*take;this.filled+=take;remaining-=take;if(this.filled>=this.ratio-1e-9){const value=Math.max(-1,Math.min(1,this.area/this.ratio));this.buffer[this.index++]=value<0?value*32768:value*32767;this.energy+=value*value;this.area=0;this.filled=0;if(this.index===1600)this.flush();}}}return true;}
}
registerProcessor('billu-pcm',BilluPCM);
