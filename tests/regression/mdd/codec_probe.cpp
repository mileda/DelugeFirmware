#include "sequencer/mdd/codec.hpp"
#include <cassert>
#include <iostream>
#include <string>
int main(){snake::Controller timing;timing.setSpeed(timing.core.lanes[0],5);timing.core.lanes[1].values.fill(65535);assert(timing.core.lanes[0].ticks==3&&timing.core.lanes[0].tickDenominator==2);assert(timing.core.advance(0).trigger&&timing.core.advance(0).duration==2);assert(!timing.core.advance(1).trigger);assert(timing.core.advance(2).trigger&&timing.core.advance(2).duration==1);assert(timing.core.advance(3).trigger);snake::Controller a,b;a.choose(5);a.custom=2;a.core.lanes[5].muted=123;a.core.lanes[5].ticks=3;a.core.lanes[5].tickDenominator=2;a.core.lanes[5].held=567;a.routes[2][0]={42,-123};auto text=snake::Codec::encode(a,true,123456);bool enabled=false;uint64_t tick=0;assert(snake::Codec::decode(text.data(),b,enabled,tick,64));assert(enabled&&tick==123456&&b.lane==5&&b.custom==2&&b.core.lanes[5].muted==123&&b.core.lanes[5].held==567&&b.core.lanes[5].tickDenominator==2&&b.routes[2][0].depth==-123);assert(b.gestures.lane==&b.core.lanes[5]);auto saved=b.core.lanes[5].values;assert(!snake::Codec::decode("z",b,enabled,tick,64));text[0]='2';text[1]='0';assert(!snake::Codec::decode(text.data(),b,enabled,tick,64));assert(saved==b.core.lanes[5].values);
// V3 adds a MIDI CC per Custom lane; V2-length text (no CC bytes) still decodes and leaves CCs off.
{snake::Controller c,d;c.midiCC={74,snake::Controller::kNoMidiCC,0,119};c.core.ties=0x0f0f;c.core.overlap=1234;c.core.legato=true;
 auto v3=snake::Codec::encode(c,false,9);assert(std::string(v3.data()).size()==snake::Codec::bytes*2);bool e=true;uint64_t t=0;
 assert(snake::Codec::decode(v3.data(),d,e,t,64)&&!e&&t==9&&d.midiCC==c.midiCC&&d.core.ties==0x0f0f&&d.core.overlap==1234&&d.core.legato);
 std::string v2(v3.data(),snake::Codec::v2Bytes*2);snake::Controller f;f.midiCC[0]=5;
 assert(snake::Codec::decode(v2,f,e,t,64)&&f.midiCC[0]==snake::Controller::kNoMidiCC&&f.core.ties==0x0f0f);
 std::string legacy(v3.data(),snake::Codec::legacyBytes*2);snake::Controller g;assert(snake::Codec::decode(legacy,g,e,t,64)&&g.core.ties==0);
 // Out-of-range CC is rejected atomically.
 std::string bad(v3.data());bad[bad.size()-2]='f';bad[bad.size()-1]='0';snake::Controller h;h.core.lanes[0].values[0]=99;assert(!snake::Codec::decode(bad,h,e,t,64)&&h.core.lanes[0].values[0]==99);
 // resetToDefault restores factory state.
 h.routes[1][1]={7,100};h.midiCC[2]=10;h.core.lanes[2].length=3;h.resetToDefault(96);assert(h.routes[1][1].target==-1&&h.midiCC[2]==snake::Controller::kNoMidiCC&&h.core.lanes[2].length==16&&h.quarterTicks==96&&h.needsInitialSpeed);}
std::cout<<"PASS clip codec: atomic validation, settings, routes, mute, held, play position, V3 MIDI CC, V2/V1 compatibility and reset\n";}
