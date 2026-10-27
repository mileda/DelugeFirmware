import subprocess
import tempfile
from pathlib import Path

r = Path(__file__).resolve().parents[3]
s = (r / "src/deluge/gui/views/instrument_clip_view.cpp").read_text()
a = s.index("bool InstrumentClipView::renderMainPads(")
b = s.index("\n\tif (isUIModeActive", a)
method = s[a:b] + "return false;\n}"
g = s.index("void InstrumentClipView::graphicsRoutine()")
h = s.index("\n\tif (!currentSong)", g)
graphics = s[g:h] + "\n}"
cells_a = s.index("std::array<int, 4> InstrumentClipView::mddPlayheadCells(")
cells_b = s.index("\nbool InstrumentClipView::mddControls()", cells_a)
cells = s[cells_a:cells_b]
code = (
    r"""
#include "sequencer/mdd/controller.hpp"
#include <array>
#include <cassert>
#include <cstring>
#include <cstdint>
#include <iostream>
constexpr int kDisplayWidth=16,kSideBarWidth=2,kDisplayHeight=8;namespace PadLEDs{void clearTickSquares(){}}int redraws=0;uint32_t lastRows=0;
template<class T>void uiNeedsRendering(T*,uint32_t rows=0xFFFFFFFF,uint32_t=0xFFFFFFFF){++redraws;lastRows=rows;}
struct RGB{uint8_t r=0,g=0,b=0;static RGB monochrome(int v){return {uint8_t(v),uint8_t(v),uint8_t(v)};}};
struct InstrumentClip{snake::Controller mdd;uint64_t mddTick=0;bool mddEnabled=true;}clip;
InstrumentClip*getCurrentInstrumentClip(){return &clip;}
struct Song{bool active=true;int getQuarterNoteLength(){return 24;}bool isClipActive(InstrumentClip*){return active;}}song,*currentSong=&song;
struct Playback{bool running=true;bool isEitherClockActive(){return running;}}playbackHandler;
struct InstrumentClipView{std::array<int,4> mddLastRenderedCells{-1,-1,-1,-1};bool enabled=true,mddGridWasRendered=false;bool mddControls(){return enabled;}
 std::array<int,4> mddPlayheadCells(InstrumentClip*)const;void graphicsRoutine();bool renderMainPads(uint32_t,RGB[][18],uint8_t[][18],bool);};
"""
    + cells
    + method
    + graphics
    + r"""
static bool white(RGB c){return c.r==c.g&&c.g==c.b&&c.r>0;}
int main(){InstrumentClipView view;RGB image[8][18]{};uint8_t mask[8][18]{};int frames=0;
for(int custom=0;custom<4;++custom)for(int shape=0;shape<5;++shape)for(int dir=0;dir<4;++dir)for(int length=1;length<=16;length+=3){
 clip.mdd.custom=custom;clip.mdd.choose(custom%3);
 for(int l=0;l<7;++l){auto&lane=clip.mdd.core.lanes[l];lane.shape=snake::Shape(shape);lane.direction=snake::Direction(dir);lane.length=length;lane.shift=3;lane.muted=l==1?0xFFFF:0;}
 for(int t=0;t<24;++t){clip.mddTick=t*7;view.renderMainPads(~0u,image,mask,false);
  for(int block=0;block<4;++block){const int laneIndex=block<3?block:3+custom;const auto&lane=clip.mdd.core.lanes[laneIndex];const int expected=lane.cell(clip.mddTick);const uint16_t used=lane.usedCells();int lit=0;
   for(int i=0;i<16;++i){auto c=image[7-i/4][block*4+i%4];assert(mask[7-i/4][block*4+i%4]==64);
    if(white(c)){++lit;assert(i==expected);assert(c.r==(lane.muted&(1u<<i)?32:laneIndex==clip.mdd.lane?220:120));}
    else if(!(used&(1u<<i)))assert(c.r<=13&&c.g<=13&&c.b<=13);}
   assert(lit==1);}
  for(int x=0;x<16;++x){assert(mask[3][x]==(x<10?64:0));}
  for(int y=0;y<3;++y)for(int x=0;x<16;++x)assert(mask[y][x]==0);++frames;}
}
// The selected lane is drawn brighter than the other blocks.
clip.mdd.choose(0);for(auto&l:clip.mdd.core.lanes){l.muted=0;l.length=16;l.shift=0;l.shape=snake::Shape::Rows;l.direction=snake::Direction::Forward;}
playbackHandler.running=false;view.renderMainPads(~0u,image,mask,false);assert(image[7][0].r>image[7][4].r||image[7][0].g>image[7][4].g||image[7][0].b>image[7][4].b);
for(int y=4;y<8;++y)for(int x=0;x<16;++x)assert(!white(image[y][x]));
playbackHandler.running=true;song.active=false;view.renderMainPads(~0u,image,mask,false);for(int y=4;y<8;++y)for(int x=0;x<16;++x)assert(!white(image[y][x]));
view.enabled=false;view.renderMainPads(~0u,image,mask,false);assert(!view.mddGridWasRendered);
 for(int y=0;y<8;++y)for(int x=0;x<16;++x){assert(image[y][x].r==0&&image[y][x].g==0&&image[y][x].b==0&&mask[y][x]==0);}
view.enabled=true;song.active=true;playbackHandler.running=true;clip.mddTick=0;
view.renderMainPads(~0u,image,mask,false);redraws=0;for(int i=0;i<100;++i)view.graphicsRoutine();assert(redraws==0);
clip.mddTick=clip.mdd.core.lanes[0].ticks;view.graphicsRoutine();assert(redraws==1&&lastRows==0xF0);view.renderMainPads(~0u,image,mask,false);view.graphicsRoutine();assert(redraws==1);
playbackHandler.running=false;view.graphicsRoutine();assert(redraws==2&&lastRows==0xF0);view.renderMainPads(~0u,image,mask,false);for(int i=0;i<100;++i)view.graphicsRoutine();assert(redraws==2);
// After switching back to Normal the stock grid is redrawn once.
view.enabled=false;view.graphicsRoutine();assert(redraws==3&&lastRows==0xFFFFFFFF);
std::cout<<"PASS change-driven grid redraw: idle, next cell (cell rows only), stop and return to Normal\n";
std::cout<<"PASS four-block grid render: "<<frames<<" frames, Notes/Gates/Velocity/Custom blocks, 5 shapes, 4 directions, lengths, reachable cells, muted/selected playheads and stopped/inactive states\n";
}
"""
)
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "probe.cpp"
    p.write_text(code)
    exe = Path(d) / "probe"
    subprocess.run(
        [
            "g++",
            "-std=c++23",
            "-O1",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wno-unused-parameter",
            "-Wno-misleading-indentation",
            "-fsanitize=undefined",
            "-I" + str(r / "src/deluge"),
            str(p),
            "-o",
            str(exe),
        ],
        check=True,
    )
    subprocess.run([str(exe)], check=True)
