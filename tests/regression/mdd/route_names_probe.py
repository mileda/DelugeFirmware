"""D2: MDD route targets are saved by param file name; V1/V2 numeric targets are migrated across the
inserted Plaits Morph params. Uses the real param enum and the real InstrumentClip helpers."""

import subprocess
import tempfile
from pathlib import Path

r = Path(__file__).resolve().parents[3]
s = (r / "src/deluge/model/clip/instrument_clip.cpp").read_text()


def extract(key, s=s):
    a = s.index(key)
    i = s.index("{", a) + 1
    d = 1
    while d:
        d += (s[i] == "{") - (s[i] == "}")
        i += 1
    return s[a:i]


ns_a = s.index("namespace {\n// MDD V1/V2 files")
ns_b = s.index("} // namespace", ns_a) + len("} // namespace")
legacy = s[ns_a:ns_b]
apply = extract("void InstrumentClip::applyMddRouteTargetNames")
code = (
    r"""
#include "modulation/params/param.h"
#include "sequencer/mdd/controller.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
namespace params = deluge::modulation::params;
// Test doubles for the file-name table: unique names per patched param.
static std::string nameOf(int p){return "p"+std::to_string(p);}
namespace deluge::modulation::params {ParamType fileStringToParam(Kind,char const*name,bool){if(name[0]!='p')return GLOBAL_NONE;int v=atoi(name+1);return v<GLOBAL_NONE?v:GLOBAL_NONE;}}
struct InstrumentClip{snake::Controller mdd;void applyMddRouteTargetNames(char const*);};
"""
    + legacy
    + "\n"
    + apply
    + r"""
int main(){
 // Old firmware IDs: Engine A/B stayed, everything from old LOCAL_PAN moved up by two.
 snake::Controller c;c.routes[0][0].target=params::LOCAL_PLAITS_B_ENGINE;c.routes[0][1].target=params::LOCAL_PLAITS_A_MORPH; // old PAN id
 c.routes[1][0].target=params::LOCAL_LPF_FREQ-2; c.routes[3][3].target=-1;
 migrateLegacyMddTargets(c);
 assert(c.routes[0][0].target==params::LOCAL_PLAITS_B_ENGINE&&c.routes[0][1].target==params::LOCAL_PAN&&c.routes[1][0].target==params::LOCAL_LPF_FREQ&&c.routes[3][3].target==-1);
 static_assert(kLegacyMddTargetLimit==params::GLOBAL_NONE-2);
 // Names: 16 comma-separated slots, empty = none, unknown name = none, missing tail = none.
 InstrumentClip clip;for(auto&l:clip.mdd.routes)for(auto&rt:l)rt.target=5;
 std::string names=nameOf(params::LOCAL_LPF_FREQ)+",,"+"bogus,"+nameOf(params::LOCAL_PLAITS_A_MORPH);
 clip.applyMddRouteTargetNames(names.c_str());
 assert(clip.mdd.routes[0][0].target==params::LOCAL_LPF_FREQ&&clip.mdd.routes[0][1].target==-1&&clip.mdd.routes[0][2].target==-1&&clip.mdd.routes[0][3].target==params::LOCAL_PLAITS_A_MORPH);
 for(int i=4;i<16;++i)assert(clip.mdd.routes[i/4][i%4].target==5); // not mentioned: decoded value kept
 std::string all;for(int i=0;i<16;++i){all+=(i?",":"")+nameOf(i);}clip.applyMddRouteTargetNames(all.c_str());for(int i=0;i<16;++i)assert(clip.mdd.routes[i/4][i%4].target==i);
 std::string toolong(40,'p');clip.applyMddRouteTargetNames(toolong.c_str());assert(clip.mdd.routes[0][0].target==-1);
 clip.applyMddRouteTargetNames(nullptr);
 std::cout<<"PASS MDD route targets: name-based restore, empty/unknown/overlong names, legacy numeric migration across Plaits Morph\n";
}
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
            "-Wall",
            "-Wextra",
            "-fsanitize=undefined,address",
            "-I" + str(r / "src"),
            "-I" + str(r / "src/deluge"),
            "-I" + str(r / "lib"),
            str(p),
            "-o",
            str(exe),
        ],
        check=True,
    )
    subprocess.run([str(exe)], check=True)
