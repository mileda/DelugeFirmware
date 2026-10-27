"""Real InstrumentClip::setScaleModeKeepingScroll body: the bottom visible note stays put across toggles."""

import subprocess
import tempfile
from pathlib import Path

r = Path(__file__).resolve().parents[3]
s = (r / "src/deluge/model/clip/instrument_clip.cpp").read_text()
a = s.index("void InstrumentClip::setScaleModeKeepingScroll")
i = s.index("{", a) + 1
d = 1
while d:
    d += (s[i] == "{") - (s[i] == "}")
    i += 1
body = s[a:i]
src = (
    r"""
#include <cassert>
#include <cstdint>
#include <iostream>
struct Song{};
// Major scale model: 7 visual rows per octave in scale mode, 12 in chromatic.
static const int major[7]={0,2,4,5,7,9,11};
struct InstrumentClip{
 bool inScaleMode=false;int32_t yScroll=0;
 int32_t getYNoteFromYVisual(int32_t v,Song*){if(!inScaleMode)return v;int o=v>=0?v/7:-((-v+6)/7);return o*12+major[v-o*7];}
 int32_t getYVisualFromYNote(int32_t n,Song*){if(!inScaleMode)return n;int o=n>=0?n/12:-((-n+11)/12);int k=n-o*12,best=0;for(int j=0;j<7;++j)if(major[j]<=k)best=j;return o*7+best;}
 void setScaleModeKeepingScroll(bool scaleMode, Song* song);
};
"""
    + body
    + r"""
int main(){Song song;InstrumentClip c;
for(int start=0;start<=120;start+=1){
 c.inScaleMode=false;c.yScroll=start;int bottom=c.getYNoteFromYVisual(c.yScroll,&song);
 c.setScaleModeKeepingScroll(true,&song);int after=c.getYNoteFromYVisual(c.yScroll,&song);
 assert(c.inScaleMode&&after<=bottom&&bottom-after<=2); // nearest scale note at or below
 c.setScaleModeKeepingScroll(true,&song);assert(c.getYNoteFromYVisual(c.yScroll,&song)==after); // idempotent
 c.setScaleModeKeepingScroll(false,&song);assert(!c.inScaleMode&&c.yScroll==after);
}
std::cout<<"PASS MDD scale toggle keeps the stock grid's bottom note (chromatic <-> scale, idempotent)\n";
}
"""
)
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "probe.cpp"
    p.write_text(src)
    exe = Path(td) / "probe"
    subprocess.run(
        ["g++", "-std=c++23", "-fsanitize=undefined", str(p), "-o", str(exe)],
        check=True,
    )
    subprocess.run([str(exe)], check=True)
