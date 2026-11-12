'use strict';
for(const target of document.querySelectorAll('img[data-preferred-src]')){const candidate=new Image();candidate.onload=()=>{target.src=candidate.src;};candidate.src=target.dataset.preferredSrc;}
