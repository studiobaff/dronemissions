'use strict';
// Synthetic DJI v13 binary: invented coordinates, names and AES material only.
const crypto=require('node:crypto');
function crc(seed,bytes){let n=BigInt(seed);for(const b of bytes){n^=BigInt(b);for(let i=0;i<8;i++)n=(n&1n)?(n>>1n)^0x95ac9329ac4bc9b5n:n>>1n;}return n;}
function xor(type,bytes){const key=Buffer.alloc(8);key.writeBigUInt64LE(crc(type,Buffer.alloc(8)));return Buffer.concat([Buffer.from([0]),Buffer.from(bytes.map((b,i)=>b^key[i%8]))]);}
function fixture(){
 const key=Buffer.alloc(32,7),initial=Buffer.alloc(16,9);let iv=initial;
 const chains=[[{featurePoint:'FR_Standardization_Feature_Base_1',aesKey:key.toString('base64'),aesIv:iv.toString('base64')}]];
 const details=Buffer.alloc(400);details.writeBigInt64LE(1792155600000n,91);details.writeDoubleLE(16,99);details.writeDoubleLE(48,107);details.writeFloatLE(750,115);details.writeInt32LE(960000,119);details.writeFloatLE(60,123);details[271]=77;details.write('Synthetic drone',280);details.write('SYNTHETIC-SN',312);
 const payload=Buffer.concat([Buffer.from([1,144,1]),details,Buffer.alloc(2)]),info=xor(0,payload),header=Buffer.alloc(3);header[0]=0;header.writeUInt16LE(info.length,1);
 const aux=Buffer.concat([header,info,Buffer.from([1,3,0,13,0,3])]);
 const records=[];
 function record(type,plain){const cipher=crypto.createCipheriv('aes-256-cbc',key,iv),encrypted=Buffer.concat([cipher.update(plain),cipher.final()]);iv=encrypted.subarray(-16);const body=Buffer.concat([xor(type,encrypted),Buffer.from([0])]),h=Buffer.alloc(3);h[0]=type;h.writeUInt16LE(body.length,1);records.push(Buffer.concat([h,body,Buffer.from([255])]));}
 const points=[[16,48],[16.002,48.001],[16.004,48],[16.002,47.999],[16,48]];
 for(let sample=0;sample<6;sample++){
  const i=Math.min(sample,4);
  const osd=Buffer.alloc(50);osd.writeDoubleLE(points[i][0]*Math.PI/180,0);osd.writeDoubleLE(points[i][1]*Math.PI/180,8);osd.writeInt16LE(600,16);osd[33]=128;osd[36]=15;osd[40]=100-i*10;osd.writeUInt16LE(i*2400,42);record(1,osd);
  const battery=Buffer.alloc(44);battery[0]=100-i*10;battery.writeUInt16LE(15000,1);battery.writeUInt16LE(5000-i*500,3);battery.writeUInt16LE(5000,5);record(7,battery);
 }
 const prefix=Buffer.alloc(100);prefix.writeBigUInt64LE(BigInt(100+aux.length),0);prefix.writeUInt16LE(aux.length,8);prefix[10]=13;
 return {raw:Buffer.concat([prefix,aux,...records]),chains,points};
}
module.exports={fixture};
if(require.main===module){const fs=require('node:fs'),f=fixture();fs.writeFileSync(process.argv[2],f.raw);fs.writeFileSync(process.argv[3],JSON.stringify(f.chains));}

