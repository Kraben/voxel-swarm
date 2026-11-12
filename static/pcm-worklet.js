/* Captures mono PCM in memory; audio output remains silent. */
class VoxelPCMProcessor extends AudioWorkletProcessor{
 constructor(){super();this.buffer=new Float32Array(4096);this.count=0;this.port.onmessage=event=>{if(event.data==='flush'){this.flush();this.port.postMessage({flushed:true});}};}
 flush(){if(!this.count)return;const samples=this.buffer.slice(0,this.count);this.port.postMessage({samples},[samples.buffer]);this.count=0;}
 process(inputs){
  const channels=inputs[0];if(!channels?.length)return true;
  for(let i=0;i<channels[0].length;i++){
   let sum=0;for(const channel of channels)sum+=channel[i];
   this.buffer[this.count++]=sum/channels.length;
   if(this.count===this.buffer.length)this.flush();
  }
  return true;
 }
}
registerProcessor('voxel-pcm',VoxelPCMProcessor);
