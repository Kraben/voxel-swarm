'use strict';
function bubbleBounds(anchor,area,expanded=false,custom=null){
 const width=Math.min(expanded?Math.max(480,custom?.width||0):Math.max(320,custom?.width||410),area.width),height=Math.min(expanded?Math.max(660,custom?.height||0):Math.max(300,custom?.height||390),area.height);
 const gap=8,right=anchor.x+anchor.width+gap,left=anchor.x-width-gap;
 const side=right+width<=area.x+area.width?'right':'left';
 const x=Math.round(Math.max(area.x,Math.min(side==='right'?right:left,area.x+area.width-width)));
 const y=Math.round(Math.max(area.y,Math.min(anchor.y+anchor.height/2-110,area.y+area.height-height)));
 return {x,y,width,height,side};
}
module.exports={bubbleBounds};
