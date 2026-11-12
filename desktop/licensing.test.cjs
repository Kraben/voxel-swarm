const {test}=require('node:test'),assert=require('node:assert/strict');
const {verifyLicense,freeProvider,assertProvider}=require('./licensing.cjs');
const fixture=require('../tests/license-vectors.json');
test('Free accepts only local Ollama and exact official Gemini API',()=>{
 for(const config of [{provider:'ollama',host:'http://localhost:11434'},{provider:'ollama',host:'http://127.0.0.1:11434'},{provider:'openai',host:'https://generativelanguage.googleapis.com/v1beta/openai'}])assert.ok(freeProvider(config));
 for(const host of ['https://api.openai.com/v1','https://generativelanguage.googleapis.com.evil.test/v1beta/openai','https://generativelanguage.googleapis.com:444/v1beta/openai','https://generativelanguage.googleapis.com/another','https://user@localhost/v1beta/openai'])assert.ok(!freeProvider({provider:'openai',host}));
 assert.ok(!freeProvider({provider:'ollama',host:'https://remote.example'}));
 assert.throws(()=>assertProvider({provider:'openai',host:'https://api.openai.com/v1'},{plan:'free'}),/Pro/);
});
test('Node validates the same signed grant as Python, expiry and tampering',()=>{
 assert.equal(verifyLicense(fixture.token,fixture.publicKey,fixture.now).plan,'pro');
 assert.equal(verifyLicense(fixture.token,fixture.publicKey,2000).plan,'free');
 assert.equal(verifyLicense(fixture.token,fixture.publicKey,500).plan,'free');
 assert.equal(verifyLicense('X'+fixture.token.slice(1),fixture.publicKey,fixture.now).plan,'free');
 assert.equal(verifyLicense(fixture.token).plan,'free');
 assert.equal(verifyLicense('pro=true').plan,'free');
});
