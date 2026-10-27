import subprocess
import tempfile
from pathlib import Path

r = Path(__file__).resolve().parents[3]
s = (r / "src/deluge/model/clip/instrument_clip.cpp").read_text()


def prefix(name, end):
    a = s.index(name)
    b = s.index(end, a)
    return s[a:b] + "}\n"


seek = prefix(
    "void InstrumentClip::setPos(",
    "\tClip::setPos(modelStack, newPos, useActualPosForParamManagers)",
)
seek = seek[:-2] + "Clip::setPos(modelStack,newPos,useActualPosForParamManagers);}\n"
move = prefix("void InstrumentClip::incrementPos(", "\n\tticksTilNextNoteRowEvent -=")
switch = prefix("void InstrumentClip::processCurrentPos(", "\n\tif (mddEnabled) {")
until_switch = prefix("int32_t InstrumentClip::mddTicksUntilSwitch(", "\n}\n")
code = (
    r"""
#include "sequencer/mdd/controller.hpp"
#include <cassert>
#include <iostream>
enum class OutputType{KIT,SYNTH};struct Output{OutputType type=OutputType::SYNTH;};
struct Song{int quarter=24;int getQuarterNoteLength(){return quarter;}}song;
struct ModelStackWithTimelineCounter{Song*song=&::song;};
struct Clock{int64_t lastSwungTickActioned=0;int swungTicksTilNextEvent=1000;}playbackHandler;
struct Clip{int lastProcessedPos=0,loopLength=96,repeatCount=0;bool currentlyPlayingReversed=false;
 void incrementPos(ModelStackWithTimelineCounter*,int n){lastProcessedPos+=n;if(lastProcessedPos>=loopLength){repeatCount+=lastProcessedPos/loopLength;lastProcessedPos%=loopLength;}}
 void setPos(ModelStackWithTimelineCounter*,int n,bool){repeatCount=n/loopLength;lastProcessedPos=n%loopLength;}
};
struct NoteRow{int32_t loopLengthIfIndependent=0,lastProcessedPosIfIndependent=0;bool hasIndependentPlayPos(){return loopLengthIfIndependent!=0;}};
struct NoteRows{NoteRow rows[2];int getNumElements(){return 2;}NoteRow*getElement(int i){return &rows[i];}};
struct InstrumentClip:Clip{Output*output;NoteRows noteRows;int32_t noteRowsNumTicksBehindClip=0,ticksTilNextNoteRowEvent=0;int32_t mddTicksUntilSwitch(Song*)const;snake::Controller mdd;bool mddEnabled=false,mddRequested=false,mddPending=false,mddNormalReversed=false;int mddNormalPos=0,mddNormalRepeat=0,closed=0,stopped=0;uint64_t mddTick=0,mddLastProcessed=UINT64_MAX;
 void closeMdd(ModelStackWithTimelineCounter*){++closed;}void stopAllNotesPlaying(ModelStackWithTimelineCounter*){++stopped;}
 void setPos(ModelStackWithTimelineCounter*,int,bool);void incrementPos(ModelStackWithTimelineCounter*,int);void processCurrentPos(ModelStackWithTimelineCounter*,uint32_t);
};
"""
    + seek
    + move
    + switch
    + until_switch
    + r"""
int main(){ModelStackWithTimelineCounter stack;Output out;
for(int quarter:{24,72}){song.quarter=quarter;InstrumentClip c;c.output=&out;c.loopLength=quarter*4;c.mdd.quarterTicks=quarter;for(auto&l:c.mdd.core.lanes)c.mdd.setSpeed(l,2);
 c.setPos(&stack,0,true);assert(c.mddTick==0&&c.mddLastProcessed==UINT64_MAX);
 // Native tick deltas can be one tick or batched, for internal or external clock.
 for(int n:{1,2,3,quarter-6,quarter,quarter*2})c.incrementPos(&stack,n);
 assert(c.mddTick==uint64_t(quarter*4));assert(c.lastProcessedPos==0);
 c.mddRequested=c.mddPending=true;playbackHandler.lastSwungTickActioned=quarter*4-1;
 playbackHandler.swungTicksTilNextEvent=1000;c.processCurrentPos(&stack,0);assert(c.mddPending&&!c.mddEnabled&&playbackHandler.swungTicksTilNextEvent==1);
 playbackHandler.lastSwungTickActioned=quarter*4;c.processCurrentPos(&stack,0);assert(c.mddEnabled&&!c.mddPending);
 assert(c.mdd.core.lanes[0].cell(c.mddTick)==0);
 c.incrementPos(&stack,quarter*2);int live=c.lastProcessedPos,repeat=c.repeatCount;
 c.noteRows.rows[0].loopLengthIfIndependent=40;c.noteRows.rows[0].lastProcessedPosIfIndependent=3;c.noteRowsNumTicksBehindClip=77;
 c.mddRequested=false;c.mddPending=true;playbackHandler.lastSwungTickActioned=quarter*6;c.processCurrentPos(&stack,0);
 assert(!c.mddEnabled&&c.lastProcessedPos==live&&c.repeatCount==repeat); // no rewind
 assert(c.noteRows.rows[1].lastProcessedPosIfIndependent==0); // clip-length row untouched
 assert(c.noteRows.rows[0].lastProcessedPosIfIndependent==live%40&&c.noteRowsNumTicksBehindClip==0&&c.ticksTilNextNoteRowEvent==0);
 c.noteRows.rows[0].loopLengthIfIndependent=0;
 c.incrementPos(&stack,quarter);assert(c.mddTick==uint64_t(quarter*7));
 c.mddRequested=c.mddPending=true;playbackHandler.lastSwungTickActioned=quarter*7;c.processCurrentPos(&stack,0);assert(c.mddEnabled);
 assert(c.mdd.core.lanes[0].cell(c.mddTick)==12); // phase follows song, not frozen MDD
 c.mddLastProcessed=0;c.setPos(&stack,0,true);assert(c.mddTick==0&&c.mddLastProcessed==UINT64_MAX);
 c.setPos(&stack,quarter,true);assert(c.mddTick==uint64_t(quarter)&&c.mdd.core.lanes[0].cell(c.mddTick)==4);
 c.setPos(&stack,quarter*5,true);assert(c.mddTick==uint64_t(quarter*5)&&c.lastProcessedPos==quarter);
}
std::cout<<"PASS native sync: shared tick deltas in both modes, live mode switch without rewind, independent rows re-aligned on return, switch scheduled on the 1/16 boundary, start/restart/seek, batched clock ticks and two song tick resolutions\n";}
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
