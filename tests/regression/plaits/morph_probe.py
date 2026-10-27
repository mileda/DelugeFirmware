"""D1: Plaits Morph moved from carrier feedback (linear, multiplicative) to a hybrid param. The real
Deluge param maths shows an unmodulated preset value P gives the same Morph either way, and the new
param lets a modulation source open Morph from P = minimum, which the old one could not."""

import subprocess
import tempfile
from pathlib import Path

r = Path(__file__).resolve().parents[3]
f = (r / "src/deluge/util/functions.cpp").read_text()
pt = (r / "src/deluge/modulation/patch/patcher.cpp").read_text()
v = (r / "src/deluge/model/voice/voice.cpp").read_text()


def extract(text, key):
    a = text.index(key)
    i = text.index("{", a) + 1
    d = 1
    while d:
        d += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[a:i]


assert "LOCAL_PLAITS_A_MORPH + s] / 2147483648.f" in v, (
    "voice must read the hybrid Morph param"
)
code = (
    r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <algorithm>
#include <iostream>
static inline int32_t multiply_32x32_rshift32(int32_t a,int32_t b){return int32_t((int64_t(a)*b)>>32);}
template<int lshift>static inline int32_t lshiftAndSaturate(int32_t v){int64_t x=int64_t(v)<<lshift;return int32_t(std::clamp<int64_t>(x,INT32_MIN,INT32_MAX));}
template<int bits>static inline int32_t signed_saturate(int32_t v){const int32_t m=(1<<(bits-1))-1;return std::clamp(v,-m-1,m);}
static inline int32_t add_saturate(int32_t a,int32_t b){return int32_t(std::clamp<int64_t>(int64_t(a)+b,INT32_MIN,INT32_MAX));}
"""
    + extract(f, "int32_t getFinalParameterValueLinear(")
    + "\n"
    + extract(f, "int32_t getFinalParameterValueHybrid(")
    + r"""
constexpr int32_t kRange=1073741824;      // getParamRange() default for both params
constexpr int32_t kFeedbackNeutral=5931642;
// Patcher maths, linear param with one optional cable (combineCablesLinear without range adjust).
static int32_t linearCombo(int32_t preset,int32_t source,int32_t strength){
 int32_t total=536870912;
 auto cable=[&](int32_t src,int32_t str){int32_t scaled=multiply_32x32_rshift32(src,str);int32_t pos=scaled+536870912;int32_t pre=multiply_32x32_rshift32(total,pos);total=lshiftAndSaturate<3>(pre);};
 cable(preset,kRange);if(strength)cable(source,strength);return total-536870912;}
// Hybrid param: cables add, then the preset value (combineCablesExp).
// Since v1.3.0-rc3 (#5099) exp/hybrid cable sums saturate instead of wrapping.
static int32_t hybridCombo(int32_t preset,int32_t source,int32_t strength){
 int32_t total=strength?add_saturate(0,multiply_32x32_rshift32(source,strength)):0;return add_saturate(total,multiply_32x32_rshift32(preset,kRange));}
static float oldMorph(int32_t preset,int32_t source=0,int32_t strength=0){
 return std::clamp(getFinalParameterValueLinear(kFeedbackNeutral,linearCombo(preset,source,strength))/11863284.f,0.f,1.f);}
static float newMorph(int32_t preset,int32_t source=0,int32_t strength=0){
 return std::clamp(0.5f+getFinalParameterValueHybrid(0,hybridCombo(preset,source,strength))/2147483648.f,0.f,1.f);}
int main(){
 double worst=0;
 for(int64_t p=INT32_MIN;p<=INT32_MAX;p+=16777216){worst=std::max<double>(worst,std::abs(oldMorph(int32_t(p))-newMorph(int32_t(p))));}
 assert(worst<0.002);
 // Envelope (unipolar max) patched at full strength with the knob at minimum.
 const int32_t envMax=INT32_MAX,full=1073741824;
 assert(oldMorph(INT32_MIN,envMax,full)==0.f);          // multiplicative: 0 x anything = 0
 assert(newMorph(INT32_MIN,envMax,full)>0.45f);         // additive: the envelope opens Morph
 std::printf("PASS Plaits Morph: unmodulated presets identical (max diff %.5f), modulation now reaches Morph from the minimum (old %.2f, new %.2f)\n",worst,oldMorph(INT32_MIN,envMax,full),newMorph(INT32_MIN,envMax,full));
}
"""
)
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "probe.cpp"
    p.write_text(code)
    exe = Path(td) / "probe"
    subprocess.run(
        ["g++", "-std=c++23", "-O1", "-fsanitize=undefined", str(p), "-o", str(exe)],
        check=True,
    )
    subprocess.run([str(exe)], check=True)
