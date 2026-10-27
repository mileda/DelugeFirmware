"""P1: MDD processed only at InstrumentClip::mddTicksUntilNextEvent() boundaries must produce exactly the
same note-on/off and Custom output as processing every native tick (the previous behaviour)."""

import subprocess
import tempfile
from pathlib import Path

r = Path(__file__).resolve().parents[3]
s = (r / "src/deluge/model/clip/instrument_clip.cpp").read_text()
a = s.index("int32_t InstrumentClip::mddTicksUntilNextEvent() const {")
i = s.index("{", a) + 1
d = 1
while d:
    d += (s[i] == "{") - (s[i] == "}")
    i += 1
body = s[a:i]
code = (
    r"""
#include "sequencer/mdd/controller.hpp"
#include "sequencer/mdd/held_notes.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
struct InstrumentClip{std::string lastCustom;snake::Controller mdd;snake::HeldNotes mddHeld;uint64_t mddTick=0,mddLastProcessed=UINT64_MAX;
 int32_t mddTicksUntilNextEvent() const;
 // Mirrors processMdd(): one frame per processed tick, duplicate-tick guard, note on/off via HeldNotes.
 void process(std::vector<std::string>& log){auto frame=mdd.core.advance(mddTick);if(mddLastProcessed==mddTick)frame.trigger=false;mddLastProcessed=mddTick;
  std::string c="C";for(int k=0;k<4;++k)c+=std::to_string(frame.custom[k])+",";if(c!=lastCustom){log.push_back(c+"@"+std::to_string(mddTick));lastCustom=c;}
  mddHeld.advance(frame,mddTick,[&](uint8_t n,uint8_t v){log.push_back("on"+std::to_string(n)+"/"+std::to_string(v)+"@"+std::to_string(mddTick));},[&](uint8_t n){log.push_back("off"+std::to_string(n)+"@"+std::to_string(mddTick));});}
};
"""
    + body
    + r"""
static uint32_t rng=12345;static uint32_t rnd(){rng=rng*1664525u+1013904223u;return rng>>8;}
int main(){int configs=0;
for(int quarter:{24,96}){for(int trial=0;trial<300;++trial){
 InstrumentClip every,sched;
 for(auto*c:{&every,&sched}){c->mdd.quarterTicks=quarter;}
 for(int l=0;l<7;++l){int speed=rnd()%15;int len=1+rnd()%16;int dir=rnd()%4;int shape=rnd()%5;uint16_t mute=rnd()&0xffff&(rnd()&1?0:0x5a5a);
  for(auto*c:{&every,&sched}){auto&lane=c->mdd.core.lanes[l];c->mdd.setSpeed(lane,speed);lane.length=len;lane.direction=snake::Direction(dir);lane.shape=snake::Shape(shape);lane.muted=mute;}
  for(int k=0;k<16;++k){uint16_t v=l==0?36+rnd()%48:l==2?rnd()%128:rnd()&0xffff;for(auto*c:{&every,&sched})c->mdd.core.lanes[l].values[k]=v;}}
 uint16_t ties=(trial%3==0)?rnd()&0xffff:0,overlap=(trial%4==1)?rnd()&0xffff:0;bool legato=trial%5==2;
 for(auto*c:{&every,&sched}){c->mdd.core.ties=ties;c->mdd.core.overlap=overlap;c->mdd.core.legato=legato;}
 const uint64_t end=uint64_t(quarter)*32;std::vector<std::string> a,b;
 for(uint64_t t=0;t<end;++t){every.mddTick=t;every.process(a);}
 uint64_t t=0;int events=0;while(t<end){sched.mddTick=t;sched.process(b);++events;int32_t n=sched.mddTicksUntilNextEvent();assert(n>=1);t+=n;}
 if(a!=b){std::cerr<<"mismatch quarter="<<quarter<<" trial="<<trial<<"\n";for(size_t k=0;k<std::max(a.size(),b.size());++k){std::cerr<<(k<a.size()?a[k]:"-")<<"  |  "<<(k<b.size()?b[k]:"-")<<"\n";if(k>40)break;}return 1;}
 assert(uint64_t(events)<=end);++configs;}}
// Default layout: all seven lanes at 1/16, 50% gates. Count transport events per bar.
for(int quarter:{24,96}){InstrumentClip c;c.mdd.quarterTicks=quarter;for(auto&l:c.mdd.core.lanes)c.mdd.setSpeed(l,2);
 std::vector<std::string> log;uint64_t t=0;int events=0;const uint64_t bar=uint64_t(quarter)*4;
 while(t<bar*8){c.mddTick=t;c.process(log);++events;t+=c.mddTicksUntilNextEvent();}
 std::cout<<"  1/16 default at "<<quarter<<" ticks/quarter: "<<events/8<<" events per bar instead of "<<bar<<"\n";
 assert(uint64_t(events/8)<=32);}
std::cout<<"PASS MDD event scheduling: "<<configs<<" random configs (speeds, lengths, directions, shapes, mutes, ties, overlap, legato) identical to per-tick processing\n";}
"""
)
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "probe.cpp"
    p.write_text(code)
    exe = Path(td) / "probe"
    subprocess.run(
        [
            "g++",
            "-std=c++23",
            "-O1",
            "-Wall",
            "-Wextra",
            "-fsanitize=undefined,address",
            "-I" + str(r / "src/deluge"),
            str(p),
            "-o",
            str(exe),
        ],
        check=True,
    )
    subprocess.run([str(exe)], check=True)
