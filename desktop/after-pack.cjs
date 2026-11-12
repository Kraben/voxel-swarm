'use strict';
const path=require('node:path');const {verifyMacBundle}=require('./verify-macos-bundle.cjs');
module.exports=async context=>{
 if(context.electronPlatformName==='darwin')verifyMacBundle(path.join(context.appOutDir,context.packager.appInfo.productFilename+'.app'));
};
