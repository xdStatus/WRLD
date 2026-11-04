"""Fast local audio duration probing without external Python packages.

Only reads container headers, not entire music files. Returns seconds or None.
"""
from __future__ import annotations
import os
import struct
import wave
import mmap
from pathlib import Path


def _mp3_frame(data, pos: int, end: int):
    """Return (frame_length, samples, sample_rate, version, layer, kbps) if valid."""
    if pos < 0 or pos + 4 > end:
        return None
    v=int.from_bytes(data[pos:pos+4], 'big')
    if (v & 0xffe00000)!=0xffe00000:
        return None
    version=(v>>19)&3
    layer_code=(v>>17)&3
    bitrate_code=(v>>12)&15
    sample_code=(v>>10)&3
    if version==1 or layer_code==0 or bitrate_code in (0,15) or sample_code==3:
        return None
    layer=4-layer_code
    table={
      ('1',3): (0,32,40,48,56,64,80,96,112,128,160,192,224,256,320,0),
      ('1',2): (0,32,48,56,64,80,96,112,128,160,192,224,256,320,384,0),
      ('1',1): (0,32,64,96,128,160,192,224,256,288,320,352,384,416,448,0),
      ('2',3): (0,8,16,24,32,40,48,56,64,80,96,112,128,144,160,0),
      ('2',2): (0,8,16,24,32,40,48,56,64,80,96,112,128,144,160,0),
      ('2',1): (0,32,48,56,64,80,96,112,128,144,160,176,192,224,256,0),
    }
    kbps=table[('1' if version==3 else '2',layer)][bitrate_code]
    if not kbps:return None
    sample_rate=(44100,48000,32000)[sample_code] // (1 if version==3 else 2 if version==2 else 4)
    padding=(v>>9)&1
    if layer==1:
        frame_len=(12*kbps*1000//sample_rate+padding)*4
        samples=384
    else:
        multiplier=72 if version!=3 and layer==3 else 144
        frame_len=multiplier*kbps*1000//sample_rate + padding
        samples=1152 if layer==2 or version==3 else 576
    if frame_len<24 or pos+frame_len>end:return None
    return (frame_len,samples,sample_rate,version,layer,kbps)


def mp3_duration(path: Path, byte_size: int):
    """Count actual MPEG audio frames to handle VBR without Xing/VBRI headers.

    Old versions extrapolated file size from the bitrate of only the *first* frame,
    making certain low-bitrate-intro VBR tracks appear much longer than they are.
    This method counts samples for all valid consecutive MPEG audio frames, ignores
    ID3 metadata and appended tags, and returns None for ambiguous/corrupt files.
    Results are cached by player.py, so each unchanged song is parsed once.
    """
    if byte_size < 100:return None
    with path.open('rb') as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
            end=len(data)
            offset=0
            if data[:3]==b'ID3' and end>=10:
                offset=10+sum((v&127)<<shift for v,shift in zip(data[6:10],(21,14,7,0)))
                if data[5]&0x10:offset+=10
            if offset >= end-8:return None
            # Get a synchronized starting point using two consecutive consistent headers.
            pos=None
            probe_end=min(end-8,offset+65536)
            p=data.find(b'\xff',offset,probe_end)
            while p>=0:
                frame=_mp3_frame(data,p,end)
                if frame:
                    nxt=_mp3_frame(data,p+frame[0],end)
                    if nxt and nxt[2:5]==frame[2:5]:
                        pos=p;break
                p=data.find(b'\xff',p+1,probe_end)
            if pos is None:return None
            total_samples=0
            frame_count=0
            rate=None
            expected_version=None
            expected_layer=None
            bad_audio=0
            while pos+4<=end:
                frame=_mp3_frame(data,pos,end)
                if frame and (rate is None or (frame[2],frame[3],frame[4])==(rate,expected_version,expected_layer)):
                    frame_len,samples,rate,expected_version,expected_layer,kbps=frame
                    frame_count+=1
                    total_samples+=samples
                    pos+=frame_len
                    continue
                # Skip an occasional broken frame but do not count arbitrary junk as audio.
                next_pos=None
                end_seek=min(end-8,pos+4096)
                p=data.find(b'\xff',pos+1,end_seek)
                while p>=0:
                    current=_mp3_frame(data,p,end)
                    if current and (current[2],current[3],current[4])==(rate,expected_version,expected_layer):
                        following=_mp3_frame(data,p+current[0],end)
                        if following and following[2:5]==current[2:5]:
                            next_pos=p
                            break
                    p=data.find(b'\xff',p+1,end_seek)
                if next_pos is None:
                    break
                bad_audio+=next_pos-pos
                if bad_audio>16384:return None
                pos=next_pos
            if frame_count<2 or rate is None:return None
            return total_samples/rate


def mp4_duration(path: Path, byte_size: int):
    def atoms(f, start:int, limit:int):
        p=start
        while p+8<=limit:
            f.seek(p)
            header=f.read(16)
            if len(header)<8:break
            n=int.from_bytes(header[0:4], 'big')
            tag=header[4:8]
            head=8
            if n==1:
                if len(header)<16:break
                n=int.from_bytes(header[8:16], 'big');head=16
            elif n==0:n=limit-p
            if n<head or p+n>limit:break
            yield p+head,p+n,tag
            p+=n
    with path.open('rb') as f:
        for start,end,tag in atoms(f,0,byte_size):
            if tag != b'moov':continue
            for child_start,child_end,child_tag in atoms(f,start,end):
                if child_tag != b'mvhd':continue
                f.seek(child_start)
                b=f.read(40)
                if not b:continue
                if b[0]==0 and len(b)>=20:
                    timescale=int.from_bytes(b[12:16],'big')
                    duration=int.from_bytes(b[16:20],'big')
                elif b[0]==1 and len(b)>=32:
                    timescale=int.from_bytes(b[20:24],'big')
                    duration=int.from_bytes(b[24:32],'big')
                else:continue
                if timescale>0 and 0<duration<2**63:return duration/timescale
    return None


def flac_duration(path: Path):
    with path.open('rb') as f:
        if f.read(4)!=b'fLaC':return None
        for _ in range(32):
            h=f.read(4)
            if len(h)<4:break
            last=h[0]&128
            typ=h[0]&127
            n=int.from_bytes(h[1:4],'big')
            if typ==0 and n>=18:
                block=f.read(n)
                if len(block)<18:return None
                packed=int.from_bytes(block[10:18],'big')
                rate=(packed>>44)&0xfffff
                samples=packed & ((1<<36)-1)
                return samples/rate if rate and samples else None
            f.seek(n,1)
            if last:break
    return None


def ogg_duration(path: Path, byte_size:int):
    with path.open('rb') as f:
        start=f.read(65536)
        if not start.startswith(b'OggS'):return None
        if b'OpusHead' in start[:2048]:
            rate=48000
            pre_skip=0
            i=start.find(b'OpusHead')
            if i>=0 and i+12<=len(start):pre_skip=int.from_bytes(start[i+10:i+12],'little')
        else:
            i=start.find(b'\x01vorbis')
            if i<0 or i+16>len(start):return None
            rate=int.from_bytes(start[i+12:i+16],'little');pre_skip=0
        if not rate:return None
        tail_len=min(byte_size,131072)
        f.seek(byte_size-tail_len)
        tail=f.read(tail_len)
        p=tail.rfind(b'OggS')
        if p<0 or p+14>len(tail):return None
        granule=int.from_bytes(tail[p+6:p+14],'little')
        if granule==(1<<64)-1:return None
        return max(0,(granule-pre_skip)/rate)


def duration_seconds(path: Path, byte_size:int|None=None):
    try:
        size=byte_size if byte_size is not None else path.stat().st_size
        if size<=0:return None
        ext=path.suffix.lower()
        if ext=='.wav':
            with wave.open(str(path),'rb') as w:
                rate=w.getframerate();return w.getnframes()/rate if rate else None
        if ext=='.mp3':return mp3_duration(path,size)
        if ext in ('.m4a','.mp4','.aac'):
            return mp4_duration(path,size) if ext!='.aac' else None
        if ext=='.flac':return flac_duration(path)
        if ext in ('.ogg','.opus'):return ogg_duration(path,size)
    except (OSError,EOFError,ValueError,struct.error,wave.Error):
        pass
    return None
