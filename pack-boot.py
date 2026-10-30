#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Preserve the supported Cube's Android-v0 header and exact initramfs."""
from pathlib import Path
import hashlib,struct,json,sys
if len(sys.argv)!=4:sys.exit('Use: python3 pack-boot.py ORIGINAL.img Image.lzo NEW.img')
output=Path(sys.argv[3])
if output.exists():sys.exit('STOP: output already exists; choose a new filename.')
original=Path(sys.argv[1]).read_bytes()
if hashlib.sha256(original).hexdigest()!='cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16':raise RuntimeError('Wrong original boot image')
def unpack(data):
 if data[:8]!=b'ANDROID!':raise RuntimeError('Wrong boot magic')
 kernel,kaddr,ramdisk,raddr,second,saddr,tags,page,version,osversion=struct.unpack_from('<10I',data,8)
 if page!=2048 or version!=0 or second!=0:raise RuntimeError('Unexpected original layout')
 align=lambda n:(n+page-1)//page*page
 kp=page;rp=kp+align(kernel);sp=rp+align(ramdisk)
 if sp+align(second)!=len(data):raise RuntimeError('Unexpected trailer')
 k=data[kp:kp+kernel];r=data[rp:rp+ramdisk];s=data[sp:sp+second]
 h=hashlib.sha1()
 for part in [k,r,s]:h.update(part);h.update(struct.pack('<I',len(part)))
 if h.digest()!=data[576:596]:raise RuntimeError('Android boot ID invalid')
 return {'header':data[:page],'kernel':k,'ramdisk':r,'second':s,'page':page,'kernel_padding':data[kp+kernel:rp],'ramdisk_padding':data[rp+ramdisk:sp]}
def pack(parts,kernel,original_padding=False):
 header=bytearray(parts['header']);struct.pack_into('<I',header,8,len(kernel))
 h=hashlib.sha1()
 for part in [kernel,parts['ramdisk'],parts['second']]:h.update(part);h.update(struct.pack('<I',len(part)))
 header[576:596]=h.digest()
 padding=parts['kernel_padding'] if original_padding else bytes((-len(kernel))%parts['page'])
 return bytes(header)+kernel+padding+parts['ramdisk']+parts['ramdisk_padding']+parts['second']
parts=unpack(original)
if pack(parts,parts['kernel'],True)!=original:raise RuntimeError('Original roundtrip not exact')
payload=Path(sys.argv[2]).read_bytes()
if not payload.startswith(b'\x89LZO\x00\r\n\x1a\n'):raise RuntimeError('Kernel must be LZO/lzop')
new=pack(parts,payload);verify=unpack(new)
if verify['ramdisk']!=parts['ramdisk']:raise RuntimeError('Initramfs changed')
# Only kernel size and standard SHA1 ID may differ in the boot header.
expected_header=bytearray(parts['header']);expected_header[8:12]=verify['header'][8:12];expected_header[576:596]=verify['header'][576:596]
if bytes(expected_header)!=verify['header']:raise RuntimeError('Unexpected header change')
with output.open('xb') as handle:handle.write(new)
report={'format':'Android boot v0','roundtrip_original_exact':True,'original_sha256':hashlib.sha256(original).hexdigest(),'new_sha256':hashlib.sha256(new).hexdigest(),'kernel_lzo_bytes':len(payload),'image_bytes':len(new),'ramdisk_unchanged':True,'ramdisk_sha256':hashlib.sha256(verify['ramdisk']).hexdigest(),'header_only_changes':['kernel_size','standard_boot_id'],'bootloader_changes':False}
print(json.dumps(report,indent=2))
